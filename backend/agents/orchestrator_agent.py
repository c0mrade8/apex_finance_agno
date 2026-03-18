import uuid
import datetime
from core.state_manager import set_agent_status
from models.agent_log import AgentLog
import time

class Orchestrator:

    def __init__(self, db, agents):
        """
        agents = {
            "tb": TBValidatorAgent,
            "variance": VarianceAgent,
            "cash": CashFlowAgent,
            "accrual": AccrualAgent,
            "revenue": RevenueAgent,
            "expense": ExpenseAgent,
            "intercompany": IntercompanyAgent,
            "consolidation": ConsolidationAgent,
            "reporting": ReportingAgent
        }
        """
        self.db = db
        self.agents = agents

    def run_month_end(self, companies, period):

        try:
            set_agent_status("Orchestrator", "GLOBAL", "STARTED")
            self.log("Orchestrator", f"Starting month-end close for {period}")

            # -----------------------------
            # GROUP 1: PARALLEL (Per Company)
            # -----------------------------
            for company in companies:


                self.log("Orchestrator", f"Running Group 1 for {company}")

                self.agents["tb"].run_validation(company, period)
                time.sleep(2)
                self.agents["variance"].run(company, period)
                time.sleep(2)
                self.agents["cash"].run(company, period)
                time.sleep(2)

            # -----------------------------
            # GROUP 2: SEQUENTIAL
            # -----------------------------
            for company in companies:

                try:

                    self.log("Orchestrator", f"Running Group 2 for {company}")

                    self.agents["accrual"].run(company, period)
                    time.sleep(2)
                    self.agents["revenue"].run(company, period)
                    time.sleep(2)
                    self.agents["expense"].run(company, period)
                    time.sleep(2)
                    self.db.commit()
                except Exception as e:
                    self.db.rollback()
                    self.log("Orchestrator", f"Error in Group 2 for {company}: {e}")

            # -----------------------------
            # GROUP 3: CROSS COMPANY
            # -----------------------------
            self.log("Orchestrator", "Running Intercompany Agent")
            self.agents["intercompany"].run(period)
            time.sleep(3)

            # -----------------------------
            # GROUP 4: CONSOLIDATION
            # -----------------------------
            self.log("Orchestrator", "Running Consolidation")
            self.agents["consolidation"].run(period)
            time.sleep(3)

            self.log("Orchestrator", "Running Reporting & Sending Email Summary")
            self.agents["reporting"].run(period)

            # -----------------------------
            set_agent_status("Orchestrator", "GLOBAL", "COMPLETED")
            self.log("Orchestrator", "Month-end close completed successfully")

            self.db.commit()

        except Exception as e:
            set_agent_status("Orchestrator", "GLOBAL", "FAILED")
            self.db.rollback()
            print(f"Orchestrator Error: {e}")
            self.db.commit()

    def log(self, agent, message):

        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent,
            company_id="GLOBAL",
            message=message,
            timestamp=datetime.datetime.now()
        ))