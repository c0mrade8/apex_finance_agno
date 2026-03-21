import sys
import os

# Ensure the root directory is in the path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine, Base
# IMPORTANT: Import ALL models here so Base knows they exist
from models.trial_balance import TrialBalance
from models.budget import Budget
from models.intercompany import IntercompanyTransaction
from models.bank_statements import BankStatements
from models.accrual import Accrual
from models.agent_log import AgentLog   
from models.alert import Alert
from models.company import Company
from models.workflow_state import WorkflowState

def rebuild_database():
    print("WARNING: This will delete ALL tables and ALL data in 'apex_finance'.")
    #confirm = input("Are you absolutely sure? (y/n): ")
    confirm='y'
    
    if confirm.lower() == 'y':
        try:
            # 1. Drop all existing tables
            print("Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            
            # 2. Create all tables based on current models
            print("Creating all tables from models...")
            Base.metadata.create_all(bind=engine)
            
            print("Database schema rebuilt successfully!")
            print("You can now run your Ingestion script.")
            
        except Exception as e:
            print(f"Error during rebuild: {e}")
    else:
        print("Reset cancelled.")

if __name__ == "__main__":
    rebuild_database()