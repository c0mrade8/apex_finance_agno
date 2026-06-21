import uuid
import datetime
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert
from models.bank_statements import BankStatements
from models.agent_log import AgentLog
from sqlalchemy import cast, Integer
from pydantic import BaseModel, Field
from typing import List
import json

class ReconciliationInsight(BaseModel):
    mismatch_reason_hypothesis: str = Field(description="Forensic hypothesis identifying whether this is a timing variance or a missing log record")
    suggested_adjusting_journal_entry: str = Field(description="The precise double-entry bookkeeping adjustment needed to align the ledger (Debit/Credit map)")
    operational_action_item: str = Field(description="Strategic recommendation for the corporate accounting team to resolve or clear this delta")

class CashReconciliationPackage(BaseModel):
    executive_summary: str = Field(description="High-level controller overview describing the cash reconciliation position and delta significance")
    reconciliation_insights: List[ReconciliationInsight] = Field(description="Array of broken structural anomalies analyzed per cash flow cluster")

class CashFlowAgent:

    def __init__(self, db, agent_instance):
        """
        db = Thread-isolated database session instance passed by Orchestrator
        agent_instance = Agno Agent model instance bound to Groq
        """
        self.db = db
        self.agent = agent_instance

    def run(self, company_id, period):
        try:
            set_agent_status("CashFlowAgent", company_id, "STARTED")

            # GL Cash (use account codes)
            cash_entries = self.db.query(TrialBalance).filter(
                TrialBalance.company_id == company_id,
                TrialBalance.period == period,
                cast(TrialBalance.account_code, Integer).between(1000, 1100)
            ).all()

            gl_balance = sum(float(e.debit or 0.0) - float(e.credit or 0.0) for e in cash_entries)

            # Bank statement (compute ending balance)
            bank_entries = self.db.query(BankStatements).filter_by(
                company_id=company_id,
                period=period
            ).all()

            if not bank_entries:
                self.save_log(company_id, "CashFlowAgent", f"No bank statement data records recovered for period {period}")
                set_agent_status("CashFlowAgent", company_id, "COMPLETED")
                return
            
            sorted_bank_entries = sorted(bank_entries, key=lambda x: getattr(x, 'date', getattr(x, 'id', 0)))
            bank_balance = float(sorted_bank_entries[-1].balance or 0.0)

            diff = gl_balance - bank_balance

            if abs(diff) > 1.0:
                hint = (
                    "Possible missing expense or bank fee"
                    if diff > 0 else
                    "Possible deposit in transit or unrecorded receipt"
                )
                
                recent_transactions = [
                    {
                        "date": str(getattr(tx, 'date', 'Unknown')),
                        "description": getattr(tx, 'description', 'No Description'),
                        "amount": float(getattr(tx, 'amount', 0.0)),
                        "type": getattr(tx, 'transaction_type', 'Unknown')
                    }
                    for tx in sorted_bank_entries[-15:]
                ]

                prompt = f"""
                You are a senior forensic auditor reconciling corporate cash positions for entity '{company_id}' during period '{period}'.
                
                The ledger balance does not match the statement provided by the banking institution.
                
                Reconciliation Parameters:
                • General Ledger Cash Position: ${gl_balance:,.2f}
                • Verified Ending Bank Balance: ${bank_balance:,.2f}
                • Out-of-Balance Variance: ${diff:,.2f}
                • Algorithmic Indicator: {hint}

                Review the recent bank transaction ledger history below for matching offsets, unrecorded fees, or timing anomalies. 
                Generate structured adjustments utilizing the response model constraints.

                CRITICAL INSTRUCTION: You must return a single valid JSON object following the requested schema.
                Ensure all property names and string values are enclosed strictly in standard double quotes ("). Never use single quotes (').
                Do not include any conversational introductions, headers, markdown code block backticks (```json), or text outside the raw JSON properties.

                Recent Transaction Activity Log:
                {recent_transactions}
                """

                response = self.agent.run(prompt, response_model=CashReconciliationPackage)
                raw_content = response.content

                # TYPE GUARD: Safely catch string modifications or error strings
                if isinstance(raw_content, CashReconciliationPackage):
                    structured_output = raw_content
                elif isinstance(raw_content, str):
                    cleaned_text = raw_content.strip()
                    
                    if "rate_limit_exceeded" in cleaned_text or "Rate limit reached" in cleaned_text or "Request too large" in cleaned_text:
                        self.save_log(company_id, "CashFlowAgent", "Groq Rate limit hit during cash reconciliation analysis. Skipping step.")
                        set_agent_status("CashFlowAgent", company_id, "COMPLETED")
                        return

                    start_idx = cleaned_text.find('{')
                    end_idx = cleaned_text.rfind('}')
                    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                        self.save_log(company_id, "CashFlowAgent", f"API provider returned a non-JSON error or empty text stream. Context: {cleaned_text[:150]}")
                        set_agent_status("CashFlowAgent", company_id, "COMPLETED")
                        return
                    cleaned_text = cleaned_text[start_idx:end_idx + 1]
                    
                    try:
                        parsed_dict = json.loads(cleaned_text)

                        for wrapper_key in ["reconciliation_metrics", "cash_reconciliation", "cash_flow_analysis", "reconciliation_insights"]:
                            if wrapper_key in parsed_dict and isinstance(parsed_dict[wrapper_key], dict):
                                parsed_dict = parsed_dict[wrapper_key]
                                break
                                
                        if "reconciliation_insights" not in parsed_dict and "insights" in parsed_dict:
                            parsed_dict["reconciliation_insights"] = parsed_dict.pop("insights")
                            
                        # Provide clean default values for mandatory fields
                        if "executive_summary" not in parsed_dict:
                            parsed_dict["executive_summary"] = f"Automated cash reconciliation positioning audit completed for {company_id}."
                        if "reconciliation_insights" not in parsed_dict:
                            parsed_dict["reconciliation_insights"] = []
                            
                        # 2. KEY NORMALIZATION: Standardize child fields to catch unexpected LLM aliases on the fly
                        if isinstance(parsed_dict.get("reconciliation_insights"), list):
                            normalized = []
                            for item in parsed_dict["reconciliation_insights"]:
                                normalized.append({
                                    "mismatch_reason_hypothesis": item.get("mismatch_reason_hypothesis") or item.get("mismatch_reason") or item.get("reason") or item.get("hypothesis") or "Timing variance flagged.",
                                    "suggested_adjusting_journal_entry": item.get("suggested_adjusting_journal_entry") or item.get("suggested_journal_entry") or item.get("journal_entry") or item.get("adjustment") or "No adjustment generated.",
                                    "operational_action_item": item.get("operational_action_item") or item.get("action_item") or item.get("recommendation") or item.get("action") or "Reconcile item manually."
                                })
                            parsed_dict["reconciliation_insights"] = normalized

                        structured_output = CashReconciliationPackage(**parsed_dict)
                    except Exception as parse_err:
                        self.save_log(company_id, "CashFlowAgent", f"JSON package extraction failed: {str(parse_err)}")
                        set_agent_status("CashFlowAgent", company_id, "FAILED")
                        return
                else:
                    self.save_log(company_id, "CashFlowAgent", f"Unexpected response object data layout type: {type(raw_content)}")
                    set_agent_status("CashFlowAgent", company_id, "FAILED")
                    return

                self.save_log(company_id, "CashFlowAgent", structured_output.executive_summary)

                abs_diff = abs(diff)
                if abs_diff > 100000: severity = "CRITICAL"
                elif abs_diff > 10000: severity = "HIGH"
                else: severity = "MEDIUM"

                for insight in structured_output.reconciliation_insights:
                    alert_payload = (
                        f"$!! Cash Recon Balance Discrepancy Flagged [Variance: ${diff:,.2f}]:\n"
                        f"• Forensic Audit Findings: {insight.mismatch_reason_hypothesis}\n"
                        f"• Proposed Journal Correction: {insight.suggested_adjusting_journal_entry}\n"
                        f"• System Actions Required: {insight.operational_action_item}"
                    )
                    self.create_alert(company_id, alert_payload, severity)

            else: 
                self.save_log(company_id, "CashFlowAgent", f"Cash positions successfully matched and reconciled for period {period}. Balance matches perfectly.")

            set_agent_status("CashFlowAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("CashFlowAgent", company_id, "FAILED")
            print(f"XXX Error in CashFlowAgent for {company_id}: {e}")

    def create_alert(self, company_id, message, severity):
        self.db.add(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            message=message,
            severity=severity
        ))

    def save_log(self, company_id, agent_name, message):
        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent_name,
            company_id=company_id,
            message=message,
            timestamp=datetime.datetime.now()
        ))