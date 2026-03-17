import uuid
import datetime
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert
from models.intercompany import IntercompanyTransaction
from models.agent_log import AgentLog


class ConsolidationAgent:

    def __init__(self, db, agent):
        self.db = db
        self.agent = agent

    def run(self, period):

        try:
            set_agent_status("ConsolidationAgent", "GLOBAL", "STARTED")

            tb_data = self.db.query(TrialBalance).filter_by(period=period).all()

            total_revenue = 0
            total_expenses = 0

            for t in tb_data:

                if t.account_type == "Revenue":
                    total_revenue += (t.credit - t.debit)

                elif t.account_type in ["Operating Expense", "COGS"]:
                    total_expenses += (t.debit - t.credit)

            # Intercompany eliminations
            ic_txns = self.db.query(IntercompanyTransaction).filter_by(period=period).all()
            total_eliminations = sum(float(t.amount) for t in ic_txns)

            cons_revenue = total_revenue - total_eliminations
            cons_expenses = total_expenses - total_eliminations
            cons_ebitda = cons_revenue - cons_expenses

            # sanity check
            if cons_revenue < 0:
                self.create_alert("GLOBAL", "Negative consolidated revenue detected", "CRITICAL")

            prompt = f"""
            Consolidated Financials ({period}):

            Revenue: {cons_revenue}
            Expenses: {cons_expenses}
            EBITDA: {cons_ebitda}

            Write:
            - portfolio performance summary
            - key risks
            - top-level recommendation
            """

            response = self.agent.run(prompt)

            self.create_alert(
                "GLOBAL",
                f"CONSOLIDATED REPORT: {response.content}",
                "LOW"
            )

            self.save_log("ConsolidationAgent", response.content)

            self.db.commit()

            set_agent_status("ConsolidationAgent", "GLOBAL", "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("ConsolidationAgent", "GLOBAL", "FAILED")
            print(f"❌ Consolidation Error: {e}")

    def create_alert(self, company_id, message, severity):

        self.db.add(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            message=message,
            severity=severity
        ))

    def save_log(self, agent, message):

        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent,
            message=message,
            timestamp=datetime.datetime.now()
        ))