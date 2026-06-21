import uuid
import time
import json
import datetime
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert
from models.agent_log import AgentLog
from pydantic import BaseModel, Field
from typing import List, Literal

class ExpenseReclassificationInsight(BaseModel):
    account_code: str = Field(description="The general ledger account code scrutinized")
    account_name: str = Field(description="The original account description name")
    suggested_category: str = Field(description="The correct target expense grouping or financial category allocation")
    reasoning: str = Field(description="Detailed forensic auditing deduction justifying this reclassification")
    confidence_score: int = Field(description="The calculated confidence assessment score metrics bounded between 0 and 100")
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Determined compliance impact severity calculation")

class ExpenseAnalysisPackage(BaseModel):
    executive_summary: str = Field(description="Fund controller level executive summary assessing general expense allocation accuracy")
    reclassifications_flagged: List[ExpenseReclassificationInsight] = Field(default=[], description="List of misclassified accounts requiring adjustments")


class ExpenseAgent:

    def __init__(self, db, agent_instance):
        """
        db = Thread-isolated database session instance passed by Orchestrator
        agent_instance = Agno Agent model instance bound to Groq
        """
        self.db = db
        self.agent = agent_instance

    def run(self, company_id, period) -> bool:

        try:
            set_agent_status("ExpenseAgent", company_id, "STARTED")

            expenses = self.db.query(TrialBalance).filter(
                TrialBalance.company_id == company_id,
                TrialBalance.period == period,
                TrialBalance.account_type.in_(["Operating Expense", "COGS"])
            ).all()

            if not expenses:
                self.save_log(company_id, "ExpenseAgent", f"No Operating Expense or COGS line items found for period {period}")
                set_agent_status("ExpenseAgent", company_id, "COMPLETED")
                return True
            
            sorted_expenses= sorted(expenses, key=lambda x: (x.debit-x.credit), reverse=True)

            dataset_payload = [
                {
                    "account_code": e.account_code,
                    "account_name": e.account_name,
                    "account_type": e.account_type,
                    "amount": float(e.debit - e.credit)
                }
                for e in sorted_expenses[:20]  # Analyze the top 20 most material accounts
            ]

            prompt = f"""
            You are a senior Private Equity Fund Controller and Forensic Auditor analyzing the operational spend accounts of portfolio entity '{company_id}' for period '{period}'.

            Analyze the attached Operating Expense and COGS general ledger line items for misclassifications or internal tracking anomalies. Typical anomalies include:
            1. Capital expenditures (CapEx) incorrectly booked as operational software expenses (OpEx).
            2. Personal travel or discretionary spend wrapped inside critical client service codes.
            3. Professional legal fees misclassified under general utilities or overhead.

            Review the ledger lines, determine if reclassification is necessary, and calculate a confidence metric score (0-100).
            
            CRITICAL INSTRUCTION: You must return a single valid JSON object following the requested schema. 
            Ensure all property names and string values are enclosed strictly in standard double quotes ("). Never use single quotes ('). 
            Do not include any conversational introductions, headers, or text outside the raw JSON properties.
            
            Target Financial Spend Dataset:
            {dataset_payload}
            """

            time.sleep(2.0)

            response = self.agent.run(prompt, response_model=ExpenseAnalysisPackage)
            raw_content = response.content

            if isinstance(raw_content, ExpenseAnalysisPackage):
                structured_output = raw_content
            elif isinstance(raw_content, str):
                cleaned_text = raw_content.strip()
                
                if "rate_limit_exceeded" in cleaned_text or "Rate limit reached" in cleaned_text or "Request too large" in cleaned_text:
                    self.save_log(company_id, "ExpenseAgent", "Groq limit reached during operational spend tracking. Skipping loop window safely.")
                    set_agent_status("ExpenseAgent", company_id, "COMPLETED")
                    return True

                start_idx = cleaned_text.find('{')
                end_idx = cleaned_text.rfind('}')
                if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                    self.save_log(company_id, "ExpenseAgent", f"API provider returned a non-JSON error or empty text stream. Context: {cleaned_text[:150]}")
                    set_agent_status("ExpenseAgent", company_id, "COMPLETED")
                    return True

                cleaned_text = cleaned_text[start_idx:end_idx + 1]
                
                try:
                    parsed_dict = json.loads(cleaned_text)

                    for wrapper_key in ["expense_analysis", "spend_analysis", "reclassification_package"]:
                        if wrapper_key in parsed_dict and isinstance(parsed_dict[wrapper_key], dict):
                            parsed_dict = parsed_dict[wrapper_key]
                            break
                            
                    # Remap key aliases if model fluctuates from required structure name
                    if "reclassifications_flagged" not in parsed_dict and "reclassifications" in parsed_dict:
                        parsed_dict["reclassifications_flagged"] = parsed_dict.pop("reclassifications")
                        
                    # Provide clean default values for mandatory string fields
                    if "executive_summary" not in parsed_dict:
                        parsed_dict["executive_summary"] = f"Automated ledger operating expense spend allocation check completed for {company_id}."
                    if "reclassifications_flagged" not in parsed_dict:
                        parsed_dict["reclassifications_flagged"] = []
                        
                    # 🚀 2. KEY NORMALIZATION: Standardize child fields so they never miss Pydantic requirements
                    if isinstance(parsed_dict.get("reclassifications_flagged"), list):
                        normalized = []
                        for item in parsed_dict["reclassifications_flagged"]:
                            normalized.append({
                                "account_code": str(item.get("account_code", "0000")).strip(),
                                "account_name": item.get("account_name") or "Unknown Account",
                                "suggested_category": item.get("suggested_category") or item.get("target_category") or "Reclassification required.",
                                "reasoning": item.get("reasoning") or item.get("reason") or item.get("justification") or "Audit discrepancy.",
                                "confidence_score": int(item.get("confidence_score", item.get("confidence", 80))),
                                "severity": item.get("severity") if str(item.get("severity")).upper() in ["LOW", "MEDIUM", "HIGH"] else "MEDIUM"
                            })
                        parsed_dict["reclassifications_flagged"] = normalized

                    structured_output = ExpenseAnalysisPackage(**parsed_dict)
                except Exception as parse_err:
                    self.save_log(company_id, "ExpenseAgent", f"JSON expense parsing compilation failed: {str(parse_err)}")
                    set_agent_status("ExpenseAgent", company_id, "FAILED")
                    return False
            else:
                self.save_log(company_id, "ExpenseAgent", f"Unexpected response object layout type payload: {type(raw_content)}")
                set_agent_status("ExpenseAgent", company_id, "FAILED")
                return False

            self.save_log(company_id, "ExpenseAgent", structured_output.executive_summary)

            for item in structured_output.reclassifications_flagged:
                # Filter to alert only on meaningful confidence thresholds
                if item.confidence_score > 70:
                    alert_payload = (
                        f"$X Expense Misclassification Flagged [{item.account_code} - {item.account_name}]:\n"
                        f"• Proposed Target Allocation: {item.suggested_category}\n"
                        f"• Auditor Justification: {item.reasoning}\n"
                        f"• Confidence Score: {item.confidence_score}/100"
                    )
                    self.create_alert(company_id, alert_payload, item.severity)

            set_agent_status("ExpenseAgent", company_id, "COMPLETED")
            return True

        except Exception as e:
            self.db.rollback()
            set_agent_status("ExpenseAgent", company_id, "FAILED")
            print(f"XXX Error in ExpenseAgent for {company_id}: {e}")
            return False

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