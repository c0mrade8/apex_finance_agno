import uuid
from core.state_manager import set_agent_status
from models.accrual import Accrual
from models.trial_balance import TrialBalance
from models.alert import Alert


class AccrualAgent:

    def __init__(self, db, agent):
        self.db = db
        self.agent = agent

    def run(self, company_id, current_period):

        try:
            set_agent_status("AccrualAgent", company_id, "STARTED")

            accruals = self.db.query(Accrual).filter_by(company_id=company_id).all()
            tb_entries = self.db.query(TrialBalance).filter_by(
                company_id=company_id,
                period=current_period
            ).all()

            if not accruals:
                set_agent_status("AccrualAgent", company_id, "COMPLETED")
                return

            tb_map = {
                e.account_code: (e.debit - e.credit)
                for e in tb_entries
            }

            current_month = int(current_period.split("-")[1])

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

                tb_balance = tb_map.get(
                    getattr(a, "gl_account_code", None),
                    0
                )

                # 2. Variance logic
                variance_pct = abs(tb_balance - a.amount) / (a.amount + 1e-6)

                if not is_booked or variance_pct > 0.2:

                    prompt = f"""
                    Company: {company_id}
                    Accrual: {a.accrual_type}

                    Expected: {a.amount}
                    Actual TB: {tb_balance}
                    Last Booked: {a.last_booked_date}

                    Tasks:
                    - Is accrual missing?
                    - Risk level (LOW/MEDIUM/HIGH)
                    - Suggested journal entry
                    """

                    response = self.agent.run(prompt)

                    self.create_alert(
                        company_id,
                        f"{a.accrual_type}: {response.content}",
                        "HIGH"
                    )

                    self.save_log(company_id, "AccrualAgent", response.content)

            self.db.commit()

            set_agent_status("AccrualAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("AccrualAgent", company_id, "FAILED")
            print(f"❌ Accrual Error: {e}")

    def create_alert(self, company_id, message, severity):

        self.db.add(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            message=message,
            severity=severity
        ))

    def save_log(self, company_id, agent, message):

        from models.agent_log import AgentLog
        import datetime

        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent,
            message=message,
            timestamp=str(datetime.datetime.now())
        ))