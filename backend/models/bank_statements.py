from sqlalchemy import Column, String, Float
from database.connection import Base

class BankStatements(Base):
    __tablename__ = "bank_statements"

    id = Column(String, primary_key=True)
    company_id = Column(String)
    date = Column(String)
    description = Column(String)
    debit = Column(Float)
    credit = Column(Float)
    balance = Column(Float)
    period = Column(String)