from sqlalchemy import Column, String, Float
from database.connection import Base

class TrialBalance(Base):
    __tablename__ = "trial_balances"

    id = Column(String, primary_key=True)
    company_id = Column(String)
    account_code = Column(String)
    account_name = Column(String)
    account_type = Column(String)
    debit = Column(Float)
    credit = Column(Float)
    balance = Column(Float)
    period = Column(String)