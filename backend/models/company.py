from sqlalchemy import Column, String, Integer, Float
from database.connection import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    company_id = Column(String, unique=True)
    company_name = Column(String)
    industry = Column(String)
    revenue_annual = Column(Float)
    employees = Column(Integer)