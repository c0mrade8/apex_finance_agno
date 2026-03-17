from sqlalchemy import Column, String, Float
from database.connection import Base

class Accrual(Base):
    __tablename__ = "accrual_schedules"

    id = Column(String, primary_key=True)
    company_id = Column(String)
    accrual_type = Column(String)
    amount = Column(Float)
    gl_account = Column(String)
    frequency = Column(String)
    last_booked_date = Column(String)