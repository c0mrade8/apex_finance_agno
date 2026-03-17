import uuid
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.alert import Alert


class TBValidatorAgent:

    def __init__(self, db, agent):
        self.db = db
        self.agent = agent

    def run_validation(self, company_id, period):

        try:
            set_agent_status("TBValidator", company_id, "STARTED")

            entries = self.db.query(TrialBalance).filter_by(
                company_id=company_id, period=period
            ).all()

            if not entries:
                self.save_log(company_id, "TBValidator", "No trial balance data found")
                set_agent_status("TBValidator", company_id, "COMPLETED")
                return

            # 1. Math Check
            debit = sum(e.debit for e in entries)
            credit = sum(e.credit for e in entries)

            if abs(debit - credit) > 0.01:
                self.create_alert(
                    company_id,
                    f"Out of balance for {period}: ${debit-credit:,.2f}",
                    "CRITICAL"
                )

            # 2. Smart LLM Context
            relevant_entries = sorted(
                entries,
                key=lambda x: abs(x.debit - x.credit),
                reverse=True
            )[:30]

            context_data = [
                {"name": e.account_name, "code": e.account_code}
                for e in relevant_entries
            ]

            # 3. Structured Prompt
            prompt = f"""
            Analyze these accounts for {company_id}.

            Identify:
            - Misclassified accounts
            - Unusual account usage

            Return:
            - account name
            - issue
            - severity (LOW/MEDIUM/HIGH)

            Data:
            {context_data}
            """

            response = self.agent.run(prompt)

            # 4. Save log
            self.save_log(company_id, "TBValidator", response.content)

            # 5. Convert LLM output → alerts (simple heuristic)
            if "HIGH" in response.content.upper():
                self.create_alert(company_id, response.content, "HIGH")

            self.db.commit()

            set_agent_status("TBValidator", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("TBValidator", company_id, "FAILED")
            print(f"TBValidator Error for {company_id}: {e}")

    def create_alert(self, company_id, message, severity):

        self.db.add(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            message=message,
            severity=severity
        ))

    def save_log(self, company_id, agent_name, message):

        from models.agent_log import AgentLog
        import datetime

        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            company_id=company_id,
            agent_name=agent_name,
            message=message,
            timestamp=str(datetime.datetime.now())
        ))