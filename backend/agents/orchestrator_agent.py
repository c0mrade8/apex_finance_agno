import uuid
import datetime
from core.state_manager import set_agent_status
from models.agent_log import AgentLog
from concurrent.futures import ThreadPoolExecutor
import time
from agno.agent import Agent

class Orchestrator:

    def __init__(self, db_session_factory, groq_model, agent_classes: dict):
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
        self.session_factory = db_session_factory
        self.groq_model=groq_model
        self.agent_classes = agent_classes

    def process_each_company(self, company, period):
        """
        Runs isolated pipeline for ONE company. 
        Safe to run inside a thread pool because it spins up its own DB session.
        """
        db=self.session_factory()
        try:
            # import time
            # import random
            # #time.sleep(random.uniform(5.0, 45.0))
            # time.sleep(12.0)
            # thread_llm = Agent(
            #     model=self.groq_model,
            #     description="You are a strict JSON-only financial extraction engine. You never return markdown narrative or conversational introductions."
            # )
            tb_llm = Agent(
                model=self.groq_model,
                description="You are a strict financial data validation engine. You must output raw JSON objects matching the schema exactly. Never output markdown formatting blocks like ```json."
            )
            variance_llm = Agent(
                model=self.groq_model,
                description="You are a strict Private Equity Fund Controller JSON API. Your output must be a single valid JSON object matching the required schema parameters. Absolutely no introductory text or conversational commentary allowed."
            )
            cash_llm = Agent(
                model=self.groq_model,
                description="You are an expert treasury accountant JSON extraction engine. You output exclusively structured JSON reconciliation metrics. No conversational headers or markdown text."
            )
            accrual_llm = Agent(
                model=self.groq_model,
                description="You are a forensic auditor JSON extraction API. Output exclusively a structured JSON package tracking omitted accruals."
            )
            expense_llm = Agent(
                model=self.groq_model,
                description="You are an accounting automation JSON extraction API. Output exclusively a structured expense analysis JSON package."
            )

            local_agents = {
                "tb": self.agent_classes["tb"](db, tb_llm),
                "variance": self.agent_classes["variance"](db, variance_llm),
                "cash": self.agent_classes["cash"](db, cash_llm),
                "accrual": self.agent_classes["accrual"](db, accrual_llm),
                "revenue": self.agent_classes["revenue"](db, expense_llm), # Uses expense/ledger llm
                "expense": self.agent_classes["expense"](db, expense_llm)
            }
            tb_valid=local_agents["tb"].run_validation(company, period)
            if not tb_valid:
                print(f"Trial Balance validation failed for {company}. Skipping further processing.")
                return False
            local_agents["variance"].run(company, period)
            local_agents["cash"].run(company, period)

            # Group 2 that actively modifies the ledger (DB)
            local_agents["accrual"].run(company,period)
            local_agents["revenue"].run(company,period)
            local_agents["expense"].run(company,period)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"ThreadError processing {company}: {e}")
            return False
        finally: db.close()

    def run_month_end(self, companies, period):
        global_db=None
        try:
            startup_db=self.session_factory()
            try:
                set_agent_status("Orchestrator", "GLOBAL", "STARTED")
                self.log(startup_db,"Orchestrator", f"Starting month-end close for {period}")
                startup_db.commit()
            finally: startup_db.close()

            with ThreadPoolExecutor(max_workers=4) as executor:
                #executor.map(lambda c: self.process_each_company(c, period), companies)
                futures=[]
                for company in companies:
                    future=executor.submit(self.process_each_company, company, period)
                    futures.append(future)
                    if company!=companies[-1]:
                        time.sleep(12.0)
                for future in futures:
                    future.result()

            global_db=self.session_factory()
            global_llm = Agent(
                model=self.groq_model,
                description="You are a strict JSON-only financial consolidation analysis engine."
            )
            global_agents={
                name: agent_class(global_db, global_llm) 
                for name, agent_class in self.agent_classes.items()
            }

            #Cross comapny agents that run after all individual company processing is done
            self.log(global_db,"Orchestrator", "Running Intercompany Agent")
            global_agents["intercompany"].run(period)
            time.sleep(3)

            #Consolidation and reporting run sequentially since they depend on each other and we want to ensure all intercompany adjustments are captured in the consolidation before reporting
            self.log(global_db,"Orchestrator", "Running Consolidation")
            global_agents["consolidation"].run(period)
            time.sleep(3)

            self.log(global_db,"Orchestrator", "Running Reporting & Sending Email Summary")
            global_agents["reporting"].run(period)

            # -----------------------------
            set_agent_status("Orchestrator", "GLOBAL", "COMPLETED")
            self.log(global_db,"Orchestrator", "Month-end close completed successfully")

            global_db.commit()

        except Exception as e:
            print(f"Orchestrator Global Error: {e}")
            set_agent_status("Orchestrator", "GLOBAL", "FAILED")

            error_db=global_db if global_db else self.session_factory()
            try:
                error_db.rollback()
                self.log(error_db, "Orchestrator", f"Global Failure: {e}")
                error_db.commit()
            finally: 
                if not global_db: error_db.close()
        finally:
            if global_db:
                global_db.close()

    def log(self, db, agent, message):

        db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent,
            company_id="GLOBAL",
            message=message,
            timestamp=datetime.datetime.now()
        ))