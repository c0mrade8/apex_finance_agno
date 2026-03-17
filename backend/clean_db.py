
from database.connection import SessionLocal
from models.trial_balance import TrialBalance
from models.budget import Budget
from models.intercompany import IntercompanyTransaction
from models.bank_statements import BankStatements
from models.accrual import Accrual
from models.agent_log import AgentLog   
from models.alert import Alert
from models.company import Company
from models.workflow_state import WorkflowState

def reset_and_initialize():
    db = SessionLocal()
    try:
        print("Wiping all tables to start fresh...")
        
        #Clear tables to avoid Foreign Key constraint issues
        db.query(Alert).delete()
        db.query(AgentLog).delete()
        db.query(WorkflowState).delete()
        db.query(TrialBalance).delete()
        db.query(Budget).delete()
        db.query(IntercompanyTransaction).delete()
        db.query(BankStatements).delete()
        db.query(Accrual).delete()
        db.query(Company).delete()
        
        db.commit()
        print("Database is now clean.")
        
    except Exception as e:
        db.rollback()
        print(f"Failed to reset database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    confirm = input("Are you sure you want to delete ALL data? (y/n): ")
    if confirm.lower() == 'y':
        reset_and_initialize()