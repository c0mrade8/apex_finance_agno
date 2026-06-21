import uuid
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Union
from models.agent_log import AgentLog
import datetime
import json

class DiscoveredAccountIssue(BaseModel):
    account_name: str = Field(description="Name of the evaluated financial account")
    account_code: Union[str, int] = Field(description="The general ledger classification code")
    issue: str = Field(description="Detailed explanation of misclassification or anomaly")
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="The calculated structural impact metric")
    
    @field_validator('account_code', mode='before')
    @classmethod
    def serialize_code_to_string(cls, v):
        if v is not None:
            return str(v).strip()
        return v
    
    @field_validator('severity', mode='before')
    @classmethod
    def force_uppercase_severity(cls, v):
        if isinstance(v, str):
            val = v.upper().strip()
            if val in ["LOW", "MEDIUM", "HIGH"]:
                return val
        return "MEDIUM"  # Default fallback severity to prevent literal mismatches

class LedgerAnalysisResult(BaseModel):
    analysis_summary: str = Field(description="Overall executive summary of ledger integrity")
    anomalies_found: List[DiscoveredAccountIssue] = Field(default=[], description="List of individual account errors")


class TBValidatorAgent:

    def __init__(self, db, agent_instance):
        """
        db = Thread-isolated database session instance passed by Orchestrator
        agent_instance = Agno Agent model instance bound to Groq
        """
        self.db = db
        self.agent = agent_instance

    def run_validation(self, company_id, period) -> bool:

        try:
            set_agent_status("TBValidator", company_id, "STARTED")

            entries = self.db.query(TrialBalance).filter_by(
                company_id=company_id, period=period
            ).all()

            if not entries:
                self.save_log(company_id, "TBValidator", "No trial balance data found")
                set_agent_status("TBValidator", company_id, "COMPLETED")
                return False

            # 1. Math Check
            total_debit = sum(float(e.debit or 0.0) for e in entries)
            total_credit = sum(float(e.credit or 0.0) for e in entries)
            variance = abs(total_debit - total_credit)

            if variance > 0.01:
                error_msg = f"Ledger Discrepancy Found: Out of balance for {period}. Discrepancy: ${total_debit - total_credit:,.2f} (Debits: ${total_debit:,.2f}, Credits: ${total_credit:,.2f})"
                print(f"⚠️ {company_id}: {error_msg}")
                self.create_alert(
                    company_id,
                    f"Out of balance for {period}, the variance found is: ${variance:,.2f}",
                    "HIGH"
                )
                self.save_log(company_id, "TBValidator", f"Mathematical variance flagged: ${variance:,.2f}. Handing over to adjustment pipelines.")

            # 2. Smart LLM Context
            material_entries = sorted(
                entries,
                key=lambda x: max(float(x.debit or 0.0), float(x.credit or 0.0)),
                reverse=True
            )[:25]

            csv_context = "Code,Name,Type,Debit,Credit\n"
            for e in material_entries:
                a_type = getattr(e, "account_type", "unknown")
                csv_context += f"{e.account_code},{e.account_name},{a_type},{e.debit or 0},{e.credit or 0}\n"

            # 3. Structured Prompt
            prompt = f"""
            You are a senior forensic accountant and financial auditor conducting a trial balance integrity check for {company_id} during {period}.

            Examine the provided General Ledger accounts for:
            1. Misclassifications (e.g., an Expense account categorized under an Asset code blueprint, or vice versa).
            2. Abnormal balances or unusual usage based on common accounting logic definitions.

            You MUST respond with a valid JSON object matching this exact schema:
            {{
              "analysis_summary": "Overall executive summary text goes here",
              "anomalies_found": [
                {{
                  "account_name": "Account Name",
                  "account_code": "Code",
                  "issue": "Detailed description of the anomaly found",
                  "severity": "LOW" | "MEDIUM" | "HIGH"
                }}
              ]
            }}

            Target Financial Dataset:
            {csv_context}
            """

            response = self.agent.run(prompt)
            raw_content = response.content
            
            print(f"!!!DEBUGGING: {raw_content}")

            if isinstance(raw_content, str):
                cleaned_text = raw_content.strip()
                start_idx = cleaned_text.find('{')
                end_idx = cleaned_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    cleaned_text = cleaned_text[start_idx:end_idx + 1]
                
                try:
                    parsed_dict = json.loads(cleaned_text)
                    
                    # 🚀 DEFENSIVE DEFENSE MAPPING: Handle flexible/alternative keys dynamically
                    if "anomalies_found" not in parsed_dict and isinstance(parsed_dict, list):
                        parsed_dict = {"anomalies_found": parsed_dict}
                    
                    if "analysis_summary" not in parsed_dict:
                        parsed_dict["analysis_summary"] = f"Automated trial balance audit review completed for {company_id}."
                        
                    anomalies = parsed_dict.get("anomalies_found", [])
                    normalized_anomalies = []
                    
                    for item in anomalies:
                        # Extract account descriptors safely
                        acc_name = item.get("account_name", "Unknown Account")
                        acc_code = item.get("account_code", "0000")
                        
                        # Fallback list for issue mappings
                        acc_issue = item.get("issue") or item.get("description") or item.get("issue_type") or "Potential ledger anomaly flagged."
                        acc_sev = item.get("severity") or "MEDIUM"
                        
                        normalized_anomalies.append({
                            "account_name": acc_name,
                            "account_code": acc_code,
                            "issue": acc_issue,
                            "severity": acc_sev
                        })
                        
                    parsed_dict["anomalies_found"] = normalized_anomalies
                    structured_data = LedgerAnalysisResult(**parsed_dict)
                    
                except Exception as parse_err:
                    self.save_log(company_id, "TBValidator", f"JSON string extraction failed: {str(parse_err)}. Content: {raw_content[:150]}")
                    set_agent_status("TBValidator", company_id, "FAILED")
                    return False
            else:
                structured_data = raw_content

            # 4. Save log output summary to execution ledger
            self.save_log(company_id, "TBValidator", structured_data.analysis_summary)

            for anomaly in structured_data.anomalies_found:
                if anomaly.severity in ["MEDIUM", "HIGH"]:
                    alert_message = f"Account {anomaly.account_code} ({anomaly.account_name}) Flagged: {anomaly.issue}"
                    self.create_alert(
                        company_id,
                        alert_message,
                        anomaly.severity
                    )

            set_agent_status("TBValidator", company_id, "COMPLETED")
            return True

        except Exception as e:
            self.db.rollback()
            set_agent_status("TBValidator", company_id, "FAILED")
            import traceback
            print(f"💥 TBVALIDATOR CRASH DETAILS FOR {company_id}:")
            traceback.print_exc()
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
            company_id=company_id,
            agent_name=agent_name,
            message=message,
            timestamp=datetime.datetime.now()
        ))