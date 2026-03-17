from sqlalchemy import Column, String, Float
from database.connection import Base

class IntercompanyTransaction(Base):
    __tablename__ = "intercompany_transactions"

    id = Column(String, primary_key=True)
    transaction_id = Column(String)
    selling_entity_id = Column(String)
    buying_entity_id = Column(String)
    selling_entity_name = Column(String)
    buying_entity_name = Column(String)
    amount = Column(Float)
    description = Column(String)
    gl_account = Column(String)
    period = Column(String)