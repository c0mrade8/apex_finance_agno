# models/workflow_state.py

import uuid
from sqlalchemy import Column, String, DateTime
from database.connection import Base
import datetime

class WorkflowState(Base):
    __tablename__ = "workflow_state"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String)   # or GLOBAL
    agent_name = Column(String)
    status = Column(String)  # STARTED / COMPLETED / FAILED
    timestamp = Column(DateTime, default=datetime.datetime.now)