from database.connection import SessionLocal
from agents.trial_balance_agent import TrialBalanceValidatorAgent

db = SessionLocal()

agent = TrialBalanceValidatorAgent(db)

results = agent.run()

print(results[:5])

db.close()