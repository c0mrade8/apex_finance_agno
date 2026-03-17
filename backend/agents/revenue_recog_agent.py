import uuid
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert


class RevenueAgent:

    def __init__(self, db, agent):
        self.db = db
        self.agent = agent

    def run(self, company_id, period):

        try:
            set_agent_status("RevenueAgent", company_id, "STARTED")

            # current period revenue
            current_entries = self.db.query(TrialBalance).filter(
                TrialBalance.company_id == company_id,
                TrialBalance.period == period,
                TrialBalance.account_type == "Revenue"
            ).all()

            # previous period (simple month back)
            prev_entries = self.db.query(TrialBalance).filter(
                TrialBalance.company_id == company_id,
                TrialBalance.account_type == "Revenue"
            ).all()

            current_rev = sum(e.credit - e.debit for e in current_entries)
            prev_rev = sum(e.credit - e.debit for e in prev_entries) / 3  # approx

            if prev_rev == 0:
                set_agent_status("RevenueAgent", company_id, "COMPLETED")
                return

            growth_pct = (current_rev - prev_rev) / abs(prev_rev)

            # trigger only if abnormal
            if abs(growth_pct) > 0.25:

                prompt = f"""
                Company: {company_id}

                Current Revenue: {current_rev}
                Historical Avg Revenue: {prev_rev}
                Growth: {growth_pct:.2%}

                Tasks:
                - Is this spike valid?
                - Could this be revenue misrecognition?
                - Risk level
                - Possible cause
                """

                response = self.agent.run(prompt)

                self.create_alert(
                    company_id,
                    f"Revenue anomaly: {response.content}",
                    "HIGH"
                )

                self.save_log(company_id, "RevenueAgent", response.content)

            self.db.commit()

            set_agent_status("RevenueAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("RevenueAgent", company_id, "FAILED")
            print(f"❌ Revenue Error: {e}")

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