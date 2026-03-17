from sqlalchemy import Column, String, Float, Integer
from database.connection import Base

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String, primary_key=True)
    company_id = Column(String)
    year = Column(Integer)
    month = Column(Integer)
    account_name = Column(String)
    account_code = Column(String)
    budget_amount = Column(Float)