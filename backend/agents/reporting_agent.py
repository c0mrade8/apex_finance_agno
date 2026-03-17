import uuid
import datetime
from core.state_manager import set_agent_status
from models.alert import Alert
from models.agent_log import AgentLog


class ReportingAgent:

    def __init__(self, db, agent):
        self.db = db
        self.agent = agent

    def run(self, period):

        try:
            set_agent_status("ReportingAgent", "GLOBAL", "STARTED")

            # fetch alerts (ideally filter by period)
            all_alerts = self.db.query(Alert).all()

            high_priority = [
                f"[{a.severity}] {a.company_id}: {a.message}"
                for a in all_alerts if a.severity in ["CRITICAL", "HIGH"]
            ][:20]

            prompt = f"""
            You are CFO of a Private Equity Fund.

            Period: {period}

            Critical Issues:
            {high_priority}

            Generate structured report:

            1. Portfolio Health (2 lines)
            2. Top 3 Risks
            3. Best Performing Segment
            4. Key Recommendations

            Keep it concise and professional.
            """

            response = self.agent.run(prompt)

            self.db.add(Alert(
                id=str(uuid.uuid4()),
                company_id="GLOBAL",
                message=f"EXECUTIVE SUMMARY:\n{response.content}",
                severity="LOW"
            ))

            self.save_log("ReportingAgent", response.content)

            self.db.commit()

            set_agent_status("ReportingAgent", "GLOBAL", "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("ReportingAgent", "GLOBAL", "FAILED")
            print(f"Reporting Error: {e}")

    def save_log(self, agent_name, message):

        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent_name,
            company_id="GLOBAL",
            message=message,
            timestamp=datetime.datetime.now()
        ))