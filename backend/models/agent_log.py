from sqlalchemy import Column, String
from database.connection import Base

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True)
    agent_name = Column(String)
    message = Column(String)
    timestamp = Column(String)