from database.connection import SessionLocal
from agents.orchestrator_agent import Orchestrator

# import all agents
from agents.trial_balance_agent import TBValidatorAgent
from agents.variance_agent import VarianceAgent
from agents.cash_flow_agent import CashFlowAgent
from agents.accrual_agent import AccrualAgent
from agents.revenue_recog_agent import RevenueAgent
from agents.expense_agent import ExpenseAgent
from agents.intercompany_agent import IntercompanyAgent
from agents.consolidation_agent import ConsolidationAgent
from agents.reporting_agent import ReportingAgent

from agno.agent import Agent
from agno.models.groq import Groq

db = SessionLocal()

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

orchestrator = Orchestrator(db, agents)

companies = [
    "techforge_saas",
    "precisionmfg_inc",
    "retailco",
    "healthservices_plus",
    "logisticspro",
    "industrialsupply_co",
    "dataanalytics_corp",
    "ecopackaging_ltd"
]

orchestrator.run_month_end(companies, "2026-01")