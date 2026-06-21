import uuid
import datetime
from core.state_manager import set_agent_status
from core.email_service import send_email
from models.alert import Alert
from models.agent_log import AgentLog
from pydantic import BaseModel, Field
from typing import List

class ExecutiveClosePackage(BaseModel):
    portfolio_health_summary: str = Field(description="A concise 2-line high-level overview of portfolio status")
    top_risks_identified: List[str] = Field(description="List of the top 3 critical material risks discovered during the close")
    best_performing_segment: str = Field(description="Identified optimal sector or high-growth entity block")
    key_recommendations: List[str] = Field(description="Actionable macroeconomic mandates for strategic alignment")

class ReportingAgent:

    def __init__(self, db, agent_instance):
        """
        db = Thread-isolated global database session instance passed by Orchestrator
        agent_instance = Agno Agent model instance bound to Groq
        """
        self.db = db
        self.agent = agent_instance

    def run(self, period) -> bool:

        try:
            set_agent_status("ReportingAgent", "GLOBAL", "STARTED")

            time_threshold = datetime.datetime.now() - datetime.timedelta(hours=24)

            # fetch alerts (ideally filter by period)
            all_alerts = self.db.query(Alert).filter(Alert.severity.in_(["CRITICAL", "HIGH"]), getattr(Alert, "timestamp", datetime.datetime.now()) >= time_threshold).all()

            high_priority = [
                f"[{a.severity}] {a.company_id}: {a.message}"
                for a in all_alerts
            ][:25]

            prompt = f"""
            You are the Managing Director and Chief Financial Officer of a top-tier Private Equity Fund.
            
            Synthesize the attached array of critical exceptions, mathematical variances, and compliance risks flagged across our portfolio companies during the closing cycle for period '{period}'.
            
            Enforce strict adherence to the requested output schema fields.

            Portfolio Exceptions Log Array:
            {high_priority if high_priority else "No high or critical anomalies flagged during this processing window."}
            """

            response = self.agent.run(prompt, response_model=ExecutiveClosePackage)
            if isinstance(response.content, str):
                self.save_log("GLOBAL", "ReportingAgent", f"Reporting fallback string caught: {response.content}")
                set_agent_status("ReportingAgent", "GLOBAL", "FAILED")
                return False
            structured_output=response.content
            #Dynamic HTML Email Summary Compilation
            risks_html = "".join([f"<li>{risk}</li>" for risk in structured_output.top_risks_identified])
            rec_html = "".join([f"<li>{rec}</li>" for rec in structured_output.key_recommendations])
            
            email_content = f"""
            <div style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px;">
                <h2 style="color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; margin-top: 0;">Apex Capital — Executive Closing Summary</h2>
                <p><b>Closing Evaluation Period Context:</b> <span style="background-color: #edf2f7; padding: 2px 6px; border-radius: 4px;">{period}</span></p>

                <h3 style="color: #2c5282; margin-top: 20px;">I. Portfolio Health Overview</h3>
                <p style="font-style: italic; color: #4a5568; background-color: #f7fafc; padding: 10px; border-left: 4px solid #4299e1;">
                    {structured_output.portfolio_health_summary}
                </p>

                <h3 style="color: #2c5282;">II. Primary Material Risk Matrices</h3>
                <ul style="padding-left: 20px; margin-top: 5px;">
                    {risks_html if risks_html else "<li>No systemic financial exposure flags remain unmitigated.</li>"}
                </ul>

                <h3 style="color: #2c5282;">III. Segment Performance Drivers</h3>
                <p>💡 {structured_output.best_performing_segment}</p>

                <h3 style="color: #2c5282;">IV. Strategic CFO Directives</h3>
                <ol style="padding-left: 20px; margin-top: 5px;">
                    {rec_html}
                </ol>

                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 25px 0;" />
                <p style="font-size: 11px; color: #a0aec0; text-align: center; margin-bottom: 0;">
                    This transaction package was fully aggregated and compiled autonomously via Apex Finance AI orchestration layers.
                </p>
            </div>
            """

            send_email(
                subject=f"Month-End Close Summary — Portfolio Allocation Review [{period}]",
                content=email_content
            )

            self.create_alert("GLOBAL", f"EXECUTIVE SUMMARY LOGGED:\n{structured_output.portfolio_health_summary}", "LOW")

            self.save_log("GLOBAL", "ReportingAgent", structured_output.portfolio_health_summary)

            set_agent_status("ReportingAgent", "GLOBAL", "COMPLETED")
            return True

        except Exception as e:
            self.db.rollback()
            set_agent_status("ReportingAgent", "GLOBAL", "FAILED")
            print(f"Error in ReportingAgent: {e}")
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
            agent_name=agent_name,
            company_id=company_id,
            message=message,
            timestamp=datetime.datetime.now()
        ))