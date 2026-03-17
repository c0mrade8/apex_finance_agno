from database.connection import SessionLocal
from agents.variance_agent import VarianceAgent

db = SessionLocal()

agent = VarianceAgent(db)

results = agent.run()

print(results[:5])  # print first 5 alerts

db.close()