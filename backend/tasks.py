from celery_app import celery_app
from database.connection import SessionLocal
from agents.orchestrator_agent import Orchestrator
#import agents
from agents.trial_balance_agent import TBValidatorAgent
from agents.variance_agent import VarianceAgent
from agents.cash_flow_agent import CashFlowAgent
from agents.accrual_agent import AccrualAgent
from agents.revenue_recog_agent import RevenueAgent
from agents.expense_agent import ExpenseAgent
from agents.intercompany_agent import IntercompanyAgent
from agents.consolidation_agent import ConsolidationAgent
from agents.reporting_agent import ReportingAgent
from agents.trial_balance_agent import TBValidatorAgent
from agents.variance_agent import VarianceAgent

from dotenv import load_dotenv
import os

load_dotenv()

@celery_app.task(name="backend.tasks.run_audit_task")
def run_audit_task(period: str):
    db = SessionLocal()
    try:
        print(f"⚙️ CELERY WORKER: Starting Autonomous Audit for {period}")
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("WORKER ERROR: GROQ_API_KEY is not set in the environment!")
            return {"status": "FAILED", "error": "Missing API Key"}

        print(f"⚙️ CELERY WORKER: Starting Autonomous Audit for {period}")

        # 1. Initialize Agents with the Worker's DB session
        # Use a lightweight model for the worker to avoid rate limits
        from agno.agent import Agent
        from agno.models.groq import Groq
        llm = Agent(model=Groq(id="llama-3.1-8b-instant"))

        agents = {
            "tb": TBValidatorAgent(db, llm),
            "variance": VarianceAgent(db, llm),
            "cash": CashFlowAgent(db, llm),
            "accrual": AccrualAgent(db, llm),
            "revenue": RevenueAgent(db, llm),
            "expense": ExpenseAgent(db, llm),
            "intercompany": IntercompanyAgent(db, llm),
            "consolidation": ConsolidationAgent(db, llm),
            "reporting": ReportingAgent(db, llm)
        }

        # 2. Run the Orchestrator
        orchestrator = Orchestrator(db, agents)
        companies = [
            "techforge_saas", "precisionmfg_inc", "retailco", 
            "healthservices_plus", "logisticspro", "industrialsupply_co", "dataanalytics_corp", "ecopackaging_ltd"
        ]
        
        orchestrator.run_month_end(companies, period)
        
        return {"status": "SUCCESS", "period": period}
    except Exception as e:
        print(f"CELERY ERROR: {str(e)}")
        return {"status": "FAILED", "error": str(e)}
    finally:
        db.close()