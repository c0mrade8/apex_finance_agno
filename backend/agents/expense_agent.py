import uuid
import datetime
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert
from models.agent_log import AgentLog


class ExpenseAgent:

    def __init__(self, db, agent):
        self.db = db
        self.agent = agent

    def run(self, company_id, period):

        try:
            set_agent_status("ExpenseAgent", company_id, "STARTED")

            expenses = self.db.query(TrialBalance).filter(
                TrialBalance.company_id == company_id,
                TrialBalance.period == period,
                TrialBalance.account_type.in_(["Operating Expense", "COGS"])
            ).all()

            if not expenses:
                set_agent_status("ExpenseAgent", company_id, "COMPLETED")
                return

            # Optional pre-filter (basic rule)
            suspicious = [
                e for e in expenses
                if "legal" in e.account_name.lower() or "travel" in e.account_name.lower()
            ]

            data = [
                {
                    "name": e.account_name,
                    "amount": float(e.debit - e.credit)
                }
                for e in (suspicious if suspicious else expenses)
            ]

            prompt = f"""
            Analyze expense accounts:

            {data}

            Return:
            - original account
            - suggested category
            - reason
            - confidence score (0-100)
            """

            response = self.agent.run(prompt)

            # smarter alert logic
            if "misclass" in response.content.lower() or "reclass" in response.content.lower():
                
                severity = "HIGH" if "90" in response.content else "MEDIUM"

                self.create_alert(
                    company_id,
                    f"Expense Reclassification: {response.content}",
                    severity
                )

            self.save_log(company_id, "ExpenseAgent", response.content)

            self.db.commit()

            set_agent_status("ExpenseAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("ExpenseAgent", company_id, "FAILED")
            print(f"❌ Expense Error: {e}")

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