import uuid
import datetime
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.budget import Budget
from models.alert import Alert
from models.agent_log import AgentLog
from pydantic import BaseModel, Field
from typing import List
import json

class AccountCommentary(BaseModel):
    account_code: str = Field(description="The matching ledger general account code identifier")
    account_name: str = Field(description="The target evaluation account title")
    business_driver: str = Field(description="Forensic hypothesis explaining the variance or variance driver anomaly")
    ebitda_impact_assessment: str = Field(description="Detailed effect mapping on company EBITDA margins and operational stability")
    remediation_recommendation: str = Field(description="Actionable control metrics or course correction steps for portfolio leadership")

class ExecutiveVariancePackage(BaseModel):
    executive_summary: str = Field(description="Fund controller level operational overview paragraph of the corporate variance profile")
    detailed_analyses: List[AccountCommentary] = Field(description="Array of targeted variance explanations grouped per material line item")

class VarianceAgent:
    def __init__(self, db, agent_instance):
        """
        db = Thread-isolated database session instance passed by Orchestrator
        agent_instance = Agno Agent model instance bound to Groq
        """
        self.db = db
        self.agent = agent_instance

    def run(self, company_id, period):
        try:
            # 1. Signal start to Orchestrator/UI
            set_agent_status("VarianceAgent", company_id, "STARTED")

            # Fetch Trial Balance and Budget data
            entries = self.db.query(TrialBalance).filter_by(
                company_id=company_id, period=period
            ).all()

            budgets = self.db.query(Budget).filter_by(
                company_id=company_id
            ).all()

            # Early exit if data is missing
            if not entries or not budgets:
                self.save_log(company_id, "VarianceAgent", f"Missing data context fields for period {period}")
                set_agent_status("VarianceAgent", company_id, "COMPLETED")
                return

            # Map budget by account code and month
            budget_map = {(str(b.account_code).strip(), b.month): b.budget_amount for b in budgets}

            material_variances_batch = []
            for t in entries:
                try:
                    # Extract month from period string (e.g., '2025-01')
                    year, month = map(int, t.period.split("-"))
                except (ValueError, AttributeError):
                    continue

                code_key = str(t.account_code).strip()
                if (code_key, month) not in budget_map:
                    continue

                # 2. Accounting Logic: Normal Balance Correction
                raw_balance = float(t.debit or 0.0) - float(t.credit or 0.0)
                if t.account_type in ['Revenue', 'Liability', 'Equity']:
                    actual = -raw_balance
                else:
                    actual = raw_balance

                budget = float(budget_map[(code_key, month)] or 0.0)

                # Prevent DivisionByZero
                if budget == 0:
                    if abs(actual) > 5000:
                        dollar_variance = actual
                        percent_variance = 100.0
                    else:
                        continue
                else:
                    dollar_variance = actual - budget
                    percent_variance = (dollar_variance / budget) * 100

                is_material_dollar = abs(dollar_variance) > 50000
                is_material_percent = abs(percent_variance) > 10 and abs(dollar_variance) > 5000

                if is_material_dollar or is_material_percent:
                    material_variances_batch.append({
                        "account_code": code_key,
                        "account_name": t.account_name,
                        "account_type": t.account_type,
                        "actual": float(actual),
                        "budget": float(budget),
                        "dollar_variance": float(dollar_variance),
                        "percent_variance": round(float(percent_variance), 2)
                    })

            if not material_variances_batch:
                self.save_log(company_id, "VarianceAgent", f"No material variances flagged for period {period}")
                set_agent_status("VarianceAgent", company_id, "COMPLETED")
                return

            # 3. Batch Prompts Execution
            prompt = f"""
            You are a Private Equity Fund Controller auditing the variance performance packages of portfolio entity '{company_id}' for '{period}'.
                
            Review the attached array of materially significant line item financial variances. Your objective is to formulate structural forensic conclusions for each item.

            For each ledger line item variance context record:
            1. Generate a likely business reason or macro driver causing this structural discrepancy.
            2. Formulate a quantitative assessment mapping how this delta trends against entity EBITDA targets.
            3. Write an actionable strategic direction recommendation message for company senior management.

            Financial Dataset Input Array:
            {material_variances_batch}
            """

            response = self.agent.run(prompt, response_model=ExecutiveVariancePackage)
            raw_content = response.content

            # 🚀 ROBUST TYPE GUARD: Clean and parse string fallbacks seamlessly
            if isinstance(raw_content, ExecutiveVariancePackage):
                structured_output = raw_content
            elif isinstance(raw_content, str):
                cleaned_text = raw_content.strip()
                
                # Check for rate-limiting messages early
                if "rate_limit_exceeded" in cleaned_text or "Rate limit reached" in cleaned_text:
                    self.save_log(company_id, "VarianceAgent", "Groq API rate limit hit during package analysis. Skipping iteration window safely.")
                    set_agent_status("VarianceAgent", company_id, "COMPLETED")
                    return

                start_idx = cleaned_text.find('{')
                end_idx = cleaned_text.rfind('}')
                if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                    self.save_log(company_id, "VarianceAgent", f"API provider returned a non-JSON error or empty text stream. Raw slice context: {cleaned_text[:150]}")
                    set_agent_status("VarianceAgent", company_id, "COMPLETED")
                    return
                    
                cleaned_text = cleaned_text[start_idx:end_idx + 1]
                try:
                    parsed_dict = json.loads(cleaned_text)
                    
                    for wrapper_key in ["variance_analysis", "variance_package", "executive_variance_package", "detailed_analyses"]:
                        if wrapper_key in parsed_dict and isinstance(parsed_dict[wrapper_key], dict):
                            parsed_dict = parsed_dict[wrapper_key]
                            break
                    
                    # Map structural variance arrays to what Pydantic expects
                    if "variance_analysis" in parsed_dict and isinstance(parsed_dict["variance_analysis"], list):
                        parsed_dict["detailed_analyses"] = parsed_dict.pop("variance_analysis")
                    
                    # Fallback defaults for missing non-nullable fields
                    if "executive_summary" not in parsed_dict:
                        parsed_dict["executive_summary"] = f"Automated corporate variance profile review completed for {company_id}."
                    if "detailed_analyses" not in parsed_dict:
                        parsed_dict["detailed_analyses"] = []
                        
                    # Normalize nested element keys to catch unexpected LLM aliases on the fly
                    if isinstance(parsed_dict.get("detailed_analyses"), list):
                        normalized = []
                        for item in parsed_dict["detailed_analyses"]:
                            normalized.append({
                                "account_code": str(item.get("account_code", "0000")).strip(),
                                "account_name": item.get("account_name") or item.get("account") or "Unknown Account",
                                "business_driver": item.get("business_driver") or item.get("reason") or item.get("explanation") or item.get("issue") or "Variance driver noted.",
                                "ebitda_impact_assessment": item.get("ebitda_impact_assessment") or item.get("ebitda_impact") or "Operational review required.",
                                "remediation_recommendation": item.get("remediation_recommendation") or item.get("remediation_recommendation") or item.get("recommendation") or "Review ledger thresholds."
                            })
                        parsed_dict["detailed_analyses"] = normalized

                    structured_output = ExecutiveVariancePackage(**parsed_dict)
                except Exception as parse_err:
                    self.save_log(company_id, "VarianceAgent", f"JSON package extraction failed: {str(parse_err)}. Saving raw trace snapshot.")
                    set_agent_status("VarianceAgent", company_id, "FAILED")
                    return
            else:
                self.save_log(company_id, "VarianceAgent", f"Unexpected response object type payload received: {type(raw_content)}")
                set_agent_status("VarianceAgent", company_id, "FAILED")
                return

            # 4. Save summary log to the execution ledger
            self.save_log(company_id, "VarianceAgent", structured_output.executive_summary)

            # Map the response object items dynamically back into individual database alert tables
            for analysis in structured_output.detailed_analyses:
                alert_payload = (
                    f"!!! [{analysis.account_code}] {analysis.account_name} Variance Report:\n"
                    f"• Operational Driver: {analysis.business_driver}\n"
                    f"• EBITDA Implication: {analysis.ebitda_impact_assessment}\n"
                    f"• Recommendation: {analysis.remediation_recommendation}"
                )
                self.create_alert(company_id, alert_payload, "HIGH")

            set_agent_status("VarianceAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("VarianceAgent", company_id, "FAILED")
            import traceback
            print(f"XXX VARIANCE AGENT CRASH DETAILS FOR {company_id}:")
            traceback.print_exc()

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
            timestamp=datetime.datetime.now()
        ))