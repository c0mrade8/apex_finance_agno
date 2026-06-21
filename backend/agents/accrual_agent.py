import uuid
import time
import datetime
from core.state_manager import set_agent_status
from models.accrual import Accrual
from models.trial_balance import TrialBalance
from models.agent_log import AgentLog
from models.alert import Alert
from pydantic import BaseModel, Field
from typing import List, Literal
import json

class AccrualAuditInsight(BaseModel):
    accrual_type: str = Field(description="The type or category classification of the analyzed accrual schedule item")
    gl_account_code: str = Field(description="The general ledger account code targeted for review")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Calculated financial risk exposure metric")
    is_missing: bool = Field(description="True if the accrual adjustment entry is completely omitted from the ledger")
    suggested_journal_entry: str = Field(description="The precise proposed double-entry bookkeeping transaction (Debit/Credit map with targets)")

class AccrualAnalysisPackage(BaseModel):
    executive_summary: str = Field(description="Fund controller level operational summary paragraph detailing company accrual status")
    flagged_anomalies: List[AccrualAuditInsight] = Field(description="Array of targeted forensic corrections for omitted or inaccurate accruals")


class AccrualAgent:

    def __init__(self, db, agent_instance):
        self.db = db
        self.agent = agent_instance 

    def run(self, company_id, current_period):
        try:
            set_agent_status("AccrualAgent", company_id, "STARTED")

            accruals = self.db.query(Accrual).filter_by(company_id=company_id).all()
            tb_entries = self.db.query(TrialBalance).filter_by(
                company_id=company_id,
                period=current_period
            ).all()

            if not accruals:
                self.save_log(company_id, "AccrualAgent", f"No accrual setup schedules found for period {current_period}")
                set_agent_status("AccrualAgent", company_id, "COMPLETED")
                return

            # Safe string key wrapping to preserve dictionary hashability across all types
            tb_map = {
                str(e.account_code).strip(): (float(e.debit or 0.0) - float(e.credit or 0.0))
                for e in tb_entries
            }

            try:
                current_month = int(current_period.split("-")[1])
            except (ValueError, IndexError):
                current_month = datetime.datetime.now().month

            flagged_accruals_batch = []

            for a in accruals:
                # 1. Frequency logic
                is_due = False
                if a.frequency == "monthly":
                    is_due = True
                elif a.frequency == "quarterly":
                    is_due = current_month % 3 == 0
                elif a.frequency == "annual":
                    is_due = current_month == 12

                if not is_due:
                    continue

                is_booked = a.last_booked_date == current_period
                target_code = str(getattr(a, "gl_account_code", "")).strip()
                tb_balance = tb_map.get(target_code, 0)

                # 2. Variance logic
                variance_pct = abs(tb_balance - float(a.amount or 0.0)) / (float(a.amount or 0.0) + 1e-6)

                if not is_booked or variance_pct > 0.2:
                    flagged_accruals_batch.append({
                        "accrual_id": getattr(a, "id", "Unknown"),
                        "accrual_type": a.accrual_type,
                        "gl_account_code": target_code,
                        "expected_amount": float(a.amount or 0.0),
                        "actual_tb_balance": float(tb_balance),
                        "variance_percentage": round(float(variance_pct * 100), 2),
                        "last_booked_period": a.last_booked_date,
                        "is_booked_in_current_period": is_booked
                    })

            if not flagged_accruals_batch:
                self.save_log(company_id, "AccrualAgent", f"All scheduled accruals successfully reconciled and matched for period {current_period}.")
                set_agent_status("AccrualAgent", company_id, "COMPLETED")
                return
            
            shortened_context = [
                {"code": e.account_code, "name": e.account_name, "balance": float((e.debit or 0.0) - (e.credit or 0.0))} 
                for e in tb_entries[:15]
            ]

            prompt = f"""
            You are a senior Private Equity Fund Controller auditing the monthly adjusting journal entries for portfolio entity '{company_id}' during period '{current_period}'.
            
            Review the attached batch of flagged accrual scheduling discrepancies. Your task is to perform an analysis of omissions, errors, or material misstatements.

            For each flagged accrual record item:
            1. Determine whether the adjustment entry is completely missing or just improperly valued.
            2. Classify the compliance risk severity exposure level (LOW, MEDIUM, HIGH).
            3. Formulate the precise proposed balancing double-entry journal correction needed to true-up the ledger balance.

            Flagged Accrual Context Dataset:
            {flagged_accruals_batch}
            
            Holistic Company Trial Balance Profile (for context reference):
            {shortened_context}
            """
            time.sleep(2.5)

            response = self.agent.run(prompt, response_model=AccrualAnalysisPackage)
            raw_content = response.content

            # 🚀 TYPE GUARD: Extract and clean structural outputs safely
            if isinstance(raw_content, AccrualAnalysisPackage):
                structured_output = raw_content
            elif isinstance(raw_content, str):
                cleaned_text = raw_content.strip()
                
                if "rate_limit_exceeded" in cleaned_text or "Rate limit reached" in cleaned_text or "Request too large" in cleaned_text:
                    self.save_log(company_id, "AccrualAgent", "Groq Rate limit hit during accrual package analysis. Skipping run window.")
                    set_agent_status("AccrualAgent", company_id, "COMPLETED")
                    return

                start_idx = cleaned_text.find('{')
                end_idx = cleaned_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    cleaned_text = cleaned_text[start_idx:end_idx + 1]
                
                try:
                    parsed_dict = json.loads(cleaned_text)
                    structured_output = AccrualAnalysisPackage(**parsed_dict)
                except Exception as parse_err:
                    self.save_log(company_id, "AccrualAgent", f"JSON accrual compilation failed: {str(parse_err)}")
                    set_agent_status("AccrualAgent", company_id, "FAILED")
                    return
            else:
                self.save_log(company_id, "AccrualAgent", f"Unexpected structural response data type payload received: {type(raw_content)}")
                set_agent_status("AccrualAgent", company_id, "FAILED")
                return

            self.save_log(company_id, "AccrualAgent", structured_output.executive_summary)

            for anomaly in structured_output.flagged_anomalies:
                alert_payload = (
                    f"$! Accrual Adjustment Discrepancy Flagged [{anomaly.accrual_type}]:\n"
                    f"• Missing Status: {'Omitted from Ledger' if anomaly.is_missing else 'Improper Valuation'}\n"
                    f"• Risk Threshold: {anomaly.risk_level}\n"
                    f"• Proposed Journal Entry: {anomaly.suggested_journal_entry}"
                )
                
                alert_severity = "HIGH" if anomaly.risk_level == "HIGH" else ("MEDIUM" if anomaly.risk_level == "MEDIUM" else "LOW")
                self.create_alert(company_id, alert_payload, alert_severity)

            set_agent_status("AccrualAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("AccrualAgent", company_id, "FAILED")
            print(f"XXX Error in AccrualAgent for {company_id}: {e}")

    def create_alert(self, company_id, message, severity):
        self.db.add(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            message=message,
            severity=severity
        ))

    def save_log(self, company_id, agent, message):
        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent,
            message=message,
            timestamp=str(datetime.datetime.now())
        ))