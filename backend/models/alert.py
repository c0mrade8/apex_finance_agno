from sqlalchemy import Column, String
from database.connection import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True)
    company_id = Column(String)
    message = Column(String)
    severity = Column(String)