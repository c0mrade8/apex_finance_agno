import uuid
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert
from pydantic import BaseModel, Field
from typing import List, Literal
from models.agent_log import AgentLog
import datetime

#pydantic validation schemas
class RevenueAuditInsight(BaseModel):
    account_code: str = Field(description="The matching ledger general revenue account identifier")
    account_name: str = Field(description="The general ledger revenue account description title")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Forensic risk assessment for potential premature revenue recognition")
    potential_cause: str = Field(description="Identified cause or operational hypothesis for the financial variance anomaly")
    suggested_audit_procedure: str = Field(description="Actionable verification procedure for the PE fund auditors (e.g., sampling specific invoices)")

class RevenueAnalysisPackage(BaseModel):
    executive_summary: str = Field(description="Fund controller level executive summary assessing the validity of the revenue growth profile")
    flagged_anomalies: List[RevenueAuditInsight] = Field(description="Array of individual revenue lines displaying misrecognition or compliance risks")


class RevenueAgent:
    
    def __init__(self, db, agent_instance):
        """
        db = Thread-isolated database session instance passed by Orchestrator
        agent_instance = Agno Agent model instance bound to Groq
        """
        self.db = db
        self.agent = agent_instance

    def run(self, company_id, period):

        try:
            set_agent_status("RevenueAgent", company_id, "STARTED")

            # current period revenue
            current_entries = self.db.query(TrialBalance).filter(
                TrialBalance.company_id == company_id,
                TrialBalance.period == period,
                TrialBalance.account_type == "Revenue"
            ).all()

            if not current_entries:
                self.save_log(company_id, "RevenueAgent", f"No revenue ledger entries discovered for period {period}")
                set_agent_status("RevenueAgent", company_id, "COMPLETED")
                return
            
            try:
                year,month = map(int, period.split("-"))
                if month == 1:
                    prev_period = f"{year-1}-12"
                else:
                    prev_period = f"{year}-{month-1:02d}"

            except (IndexError, ValueError): prev_period = None

            prev_entries = []
            if prev_period:
                prev_entries = self.db.query(TrialBalance).filter(
                    TrialBalance.company_id == company_id,
                    TrialBalance.period == prev_period,
                    TrialBalance.account_type == "Revenue"
                ).all()

            current_rev_map = {e.account_code: e for e in current_entries}
            prev_rev_map = {e.account_code: (e.credit-e.debit) for e in prev_entries}

            flagged_revenue_batch=[]
            for code, curr_entry in current_rev_map.items():
                curr_bal = curr_entry.credit - curr_entry.debit
                prev_bal = prev_rev_map.get(code, 0.0)
                if prev_bal == 0.0:
                    growth_pct = 100.0 if curr_bal > 5000 else 0.0
                    delta=curr_bal
                else: 
                    delta=curr_bal - prev_bal
                    growth_pct=(delta/abs(prev_bal))*100

            # trigger only if abnormal
                if abs(growth_pct) > 25.0 and abs(delta) > 10000:
                    flagged_revenue_batch.append({
                            "account_code": code,
                            "account_name": curr_entry.account_name,
                            "current_balance": float(curr_bal),
                            "previous_balance": float(prev_bal),
                            "dollar_variance": float(delta),
                            "growth_percentage": round(float(growth_pct), 2)
                        })
                
            if not flagged_revenue_batch:
                self.save_log(company_id, "RevenueAgent", f"Revenue horizontal growth verified within standard parameters for period {period}.")
                set_agent_status("RevenueAgent", company_id, "COMPLETED")
                return

            prompt = f"""
            You are a senior Private Equity Fund Controller and Forensic Auditor analyzing revenue recognition patterns for portfolio entity '{company_id}' during period '{period}'.
            
            Horizontal review has flagged significant, non-standard revenue expansion metrics compared to the immediate prior period '{prev_period}'.
            
            Evaluate the dataset for compliance risks, including:
            1. Bill-and-hold schema fraud or channel stuffing.
            2. Premature revenue recognition (recognizing contract values before performance obligations are fully satisfied).
            3. Cut-off errors near the closing timeline boundaries.

            Flagged Revenue Variances Dataset Array:
            {flagged_revenue_batch}
            """

            response = self.agent.run(prompt, response_mode=RevenueAnalysisPackage)
            structured_output: RevenueAnalysisPackage = response.content

            #Mapping Output Schemas to Database Alerts ---
            for anomaly in structured_output.flagged_anomalies:
                alert_payload = (
                    f"$$$ Revenue Growth Anomaly Detected [{anomaly.account_code} - {anomaly.account_name}]:\n"
                    f"• Operational Risk Profile: {anomaly.risk_level}\n"
                    f"• Forensic Source Driver: {anomaly.potential_cause}\n"
                    f"• Recommended Verification Track: {anomaly.suggested_audit_procedure}"
                )
                self.create_alert(company_id, alert_payload, anomaly.risk_level)

            set_agent_status("RevenueAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("RevenueAgent", company_id, "FAILED")
            print(f"XXX Error in revenue agent for {company_id}: {e}")

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
            company_id=company_id,
            message=message,
            timestamp=str(datetime.datetime.now())
        ))