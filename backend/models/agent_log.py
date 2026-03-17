from sqlalchemy import Column, String
from database.connection import Base

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True)
    company_id = Column(String, nullable=False)
    agent_name = Column(String)
    message = Column(String)
    timestamp = Column(String)