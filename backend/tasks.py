from celery_app import celery_app
from database.connection import SessionLocal
from agents.orchestrator_agent import Orchestrator
from agents.trial_balance_agent import TBValidatorAgent
from agents.variance_agent import VarianceAgent
from agents.cash_flow_agent import CashFlowAgent
from agents.accrual_agent import AccrualAgent
from agents.revenue_recog_agent import RevenueAgent
from agents.expense_agent import ExpenseAgent
from agents.intercompany_agent import IntercompanyAgent
from agents.consolidation_agent import ConsolidationAgent
from agents.reporting_agent import ReportingAgent
from sqlalchemy import text
from dotenv import load_dotenv
import time
import os

load_dotenv()

@celery_app.task(name="backend.tasks.run_audit_task")
def run_audit_task(period: str):
    try:
        print(f"⚙️ CELERY WORKER: Starting Autonomous Audit for {period}")
        #db readiness check
        is_data_ready = False
        prev_count = -1
        stable_streak = 0
        max_retries = 15  # Gives ingestion enough retry windows to finish writing
        
        print("⏳ Celery Worker: Verifying Database Ingestion Stability...")
        for i in range(max_retries):
            # Open a fresh short-lived session inside the loop iteration 
            # to bypass SQLAlchemy snapshot isolation and see newly committed rows.
            db_check = SessionLocal()
            try:
                current_count = db_check.execute(text("SELECT COUNT(*) FROM trial_balances")).scalar() or 0
                
                if current_count > 0 and current_count == prev_count:
                    stable_streak += 1
                    # Must hold identical across 2 consecutive iterations (approx 8 seconds of silence)
                    if stable_streak >= 2:
                        print(f"✅ Ingestion stabilized cleanly at {current_count} records. Starting Orchestrator.")
                        is_data_ready = True
                        db_check.close()
                        break
                    else:
                        print(f"⏳ Count matched once ({current_count}). Verifying stability on next check...")
                else:
                    stable_streak = 0  # Reset streak if data is actively growing
                    if current_count > 0:
                        print(f"⏳ Ingestion active... Current rows committed: {current_count}. Waiting...")
                    else:
                        print("⏳ Waiting for ingestion script to begin writing records...")
                
                prev_count = current_count
            except Exception as read_err:
                print(f"Waiting for database schemas to initialize... ({read_err})")
                stable_streak = 0
            finally:
                db_check.close()
            
            time.sleep(4.0)  # Check every 4 seconds
        
        if not is_data_ready:
            print("❌ WORKER ERROR: Data Ingestion timed out stabilization. Aborting pipeline.")
            return {"status": "FAILED", "error": "Database ingestion not stabilized"}
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("WORKER ERROR: GROQ_API_KEY is not set in the environment!")
            return {"status": "FAILED", "error": "Missing API Key"}

        # 1. Initialize Agents with the Worker's DB session
        # Use a lightweight model for the worker to avoid rate limits
        from agno.agent import Agent
        from agno.models.groq import Groq
        groq_model = Groq(id="llama-3.3-70b-versatile", temperature=0.0)
        # llm=Agent(model=groq_model,
        #           description="You are a strict JSON-only data extraction engine. You never return markdown, explanations, or conversational text.",
        #           markdown=False)
        #mapping names to raw un-intantiated classes so that we can create separate instances inside each thread in the Orchestrator
        agent_blueprint = {
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

        # 2. Run the Orchestrator
        orchestrator = Orchestrator(SessionLocal, groq_model, agent_blueprint)
        companies = [
            "techforge_saas", "precisionmfg_inc", "retailco", 
            "healthservices_plus", "logisticspro", "industrialsupply_co", "dataanalytics_corp", "ecopackaging_ltd"
        ]
        
        orchestrator.run_month_end(companies, period)
        
        return {"status": "SUCCESS", "period": period}
    except Exception as e:
        print(f"CELERY ERROR: {str(e)}")
        return {"status": "FAILED", "error": str(e)}