import uuid
import datetime
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert
from models.bank_statements import BankStatements
from models.agent_log import AgentLog
from sqlalchemy import cast, Integer


class CashFlowAgent:

    def __init__(self, db, agent):
        self.db = db
        self.agent = agent

    def run(self, company_id, period):

        try:
            set_agent_status("CashFlowAgent", company_id, "STARTED")

            # GL Cash (use account codes)
            cash_entries = self.db.query(TrialBalance).filter(
                TrialBalance.company_id == company_id,
                TrialBalance.period == period,
                cast(TrialBalance.account_code, Integer).between(1000, 1100)
            ).all()

            gl_balance = sum(e.debit - e.credit for e in cash_entries)

            # Bank statement (compute ending balance)
            bank_entries = self.db.query(BankStatements).filter_by(
                company_id=company_id,
                period=period
            ).all()

            if not bank_entries:
                set_agent_status("CashFlowAgent", company_id, "COMPLETED")
                return

            bank_balance = float(bank_entries[-1].balance)

            diff = gl_balance - bank_balance

            if abs(diff) > 1.0:

                hint = (
                    "Possible missing expense or bank fee"
                    if diff > 0 else
                    "Possible deposit not recorded"
                )

                prompt = f"""
                Company: {company_id}
                Period: {period}

                GL Balance: {gl_balance}
                Bank Balance: {bank_balance}
                Difference: {diff}

                Hint: {hint}

                Tasks:
                - Identify cause
                - Timing difference or error
                - Suggest journal entry
                """

                response = self.agent.run(prompt)

                if abs(diff) > 100000:
                    severity = "CRITICAL"
                elif abs(diff) > 10000:
                    severity = "HIGH"
                else:
                    severity = "MEDIUM"

                self.create_alert(
                    company_id,
                    f"Cash Recon Issue ({diff}): {response.content}",
                    severity
                )

                self.save_log(company_id, "CashFlowAgent", response.content)

            self.db.commit()

            set_agent_status("CashFlowAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("CashFlowAgent", company_id, "FAILED")
            print(f"CashFlow Error: {e}")

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