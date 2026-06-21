import uuid
import datetime
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert
from models.intercompany import IntercompanyTransaction
from models.agent_log import AgentLog
from pydantic import BaseModel, Field
from typing import List

class ConsolidatedMetricInsight(BaseModel):
    metric_name: str = Field(description="The name of the evaluated consolidated metric (e.g., Revenue, EBITDA)")
    calculated_value: float = Field(description="The adjusted, post-elimination currency balance")
    variance_commentary: str = Field(description="PE Fund level analytical summary regarding this metric's group performance")

class ConsolidationAnalysisPackage(BaseModel):
    executive_summary: str = Field(description="Fund controller level executive overview summarizing total portfolio operational performance")
    key_portfolio_risks: List[str] = Field(description="Bullet-point matrix identifying material cross-company or macro-spend risks")
    strategic_recommendations: List[str] = Field(description="Actionable operational mandates for portfolio company management teams")


class ConsolidationAgent:

    def __init__(self, db, agent_instance):
        self.db = db
        self.agent = agent_instance

    def run(self, period) -> bool:

        try:
            set_agent_status("ConsolidationAgent", "GLOBAL", "STARTED")

            tb_data = self.db.query(TrialBalance).filter_by(period=period).all()
            if not tb_data:
                self.save_log("GLOBAL", "ConsolidationAgent", f"No trial balance records found for the period {period}")
                set_agent_status("ConsolidationAgent", "GLOBAL", "COMPLETED")
                return True

            total_revenue = 0.0
            total_expenses = 0.0
            entity_performance_matrix = {}
            for t in tb_data:
                bal=float(t.credit - t.debit) if t.account_type == "Revenue" else float(t.debit - t.credit)
                if t.company_id not in entity_performance_matrix:
                    entity_performance_matrix[t.company_id] = {"revenue": 0.0, "expenses": 0.0,}
                if t.account_type == "Revenue":
                    total_revenue += bal
                    entity_performance_matrix[t.company_id]["revenue"] += bal

                elif t.account_type in ["Operating Expense", "COGS"]:
                    total_expenses += bal
                    entity_performance_matrix[t.company_id]["expenses"] += bal

            # Intercompany eliminations
            ic_txns = self.db.query(IntercompanyTransaction).filter_by(period=period).all()

            revenue_eliminations = 0.0
            expense_eliminations = 0.0

            for tx in ic_txns:
                desc = tx.description.lower()
                amt = float(tx.amount)
                # Differentiate between operational expenses vs clearing asset shifts
                if any(x in desc for x in ["revenue", "sale", "service", "fee"]):
                    revenue_eliminations += amt
                if any(x in desc for x in ["expense", "cost", "purchase", "reimbursement"]):
                    expense_eliminations += amt

            # Apply precise multi-entity elimination adjustments
            cons_revenue = total_revenue - revenue_eliminations
            cons_expenses = total_expenses - expense_eliminations
            cons_ebitda = cons_revenue - cons_expenses

            # Sanity guardrail checks
            if cons_revenue < 0:
                self.create_alert("GLOBAL", f"CRITICAL: Negative consolidated revenue detected (${cons_revenue:,.2f})", "CRITICAL")

            prompt = f"""
            You are a Managing Director and Chief Financial Officer auditing the aggregated monthly consolidation package across the entire portfolio for period '{period}'.
            
            Review the calculated totals and individual portfolio entity metrics. Enforce standard corporate finance elimination rules.

            Calculated Consolidated Financial Profiles:
            • Raw Combined Revenue: ${total_revenue:,.2f} (Eliminations Applied: -${revenue_eliminations:,.2f}) -> Consolidated Revenue: ${cons_revenue:,.2f}
            • Raw Combined Expenses: ${total_expenses:,.2f} (Eliminations Applied: -${expense_eliminations:,.2f}) -> Consolidated Expenses: ${cons_expenses:,.2f}
            • Consolidated Fund EBITDA: ${cons_ebitda:,.2f}

            Portfolio Breakdown Context:
            {entity_performance_matrix}
            """

            response = self.agent.run(prompt, response_model=ConsolidationAnalysisPackage)
            if isinstance(response.content, str):
                self.save_log("GLOBAL", "ConsolidationAgent", f"Consolidation validation fallback string caught: {response.content}")
                set_agent_status("ConsolidationAgent", "GLOBAL", "FAILED")
                return False
            structured_output: ConsolidationAnalysisPackage= response.content

            self.save_log("GLOBAL", "ConsolidationAgent", structured_output.executive_summary)
            alert_summary = (
                f"Consolidated Closing Package Staged:\n"
                f"• Rev: ${cons_revenue:,.2f} | EBITDA: ${cons_ebitda:,.2f}\n"
                f"• Top Risk Profile: {structured_output.key_portfolio_risks[0] if structured_output.key_portfolio_risks else 'Stable'}\n"
                f"• CFO Mandate: {structured_output.strategic_recommendations[0] if structured_output.strategic_recommendations else 'Maintain Course'}"
            )
            self.create_alert("GLOBAL", alert_summary, "LOW")

            set_agent_status("ConsolidationAgent", "GLOBAL", "COMPLETED")
            return True

        except Exception as e:
            self.db.rollback()
            set_agent_status("ConsolidationAgent", "GLOBAL", "FAILED")
            print(f"XXX Error in ConsolidationAgent: {e}")
            return False

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