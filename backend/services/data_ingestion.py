import pandas as pd
import uuid
from pathlib import Path
from database.connection import SessionLocal
from models.trial_balance import TrialBalance
from models.budget import Budget
from models.intercompany import IntercompanyTransaction
from models.bank_statements import BankStatements
from models.accrual import Accrual
from models.company import Company
import json

CURRENT_FILE_DIR = Path(__file__).resolve().parent

DATA_DIR = CURRENT_FILE_DIR.parent / "data"

print(f"INGESTION DEBUG: Searching for files in: {DATA_DIR}")

if not DATA_DIR.exists():
    print(f"ERROR: Data directory NOT FOUND at {DATA_DIR}")


def load_companies():

    db = SessionLocal()

    file = DATA_DIR / "company_metadata.json"

    with open(file, "r") as f:
        data = json.load(f)

    try:
        for c in data:

            exists = db.query(Company).filter_by(
                company_id=c["id"]
            ).first()

            if exists:
                continue

            record = Company(
                id=str(uuid.uuid4()),
                company_id=c["id"],
                company_name=c["name"],
                industry=c["industry"],
                revenue_annual=float(c["revenue_annual"]),
                employees=int(c["employees"])
            )

            db.add(record)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Company Load Error: {e}")

    db.close()
    print("Companies Loaded")


#trial balances + prior year
def load_trial_balances():

    db = SessionLocal()
    folders = ["trial_balances", "prior_year"]

    for folder in folders:

        files = (DATA_DIR / folder).glob("*.csv")

        for file in files:

            df = pd.read_csv(file)

            try:
                for _, row in df.iterrows():

                    exists = db.query(TrialBalance).filter_by(
                        company_id=row["company_id"],
                        account_code=str(row["account_code"]),
                        period=row["period"]
                    ).first()

                    if exists:
                        continue

                    record = TrialBalance(
                        id=str(uuid.uuid4()),
                        company_id=row["company_id"],
                        account_code=str(row["account_code"]),
                        account_name=row["account_name"],
                        account_type=row["account_type"],
                        debit=float(row["debit"]) if row["debit"] else 0.0,
                        credit=float(row["credit"]) if row["credit"] else 0.0,
                        balance=float(row["balance"]),
                        period=row["period"]
                    )

                    db.add(record)

                db.commit()

            except Exception as e:
                db.rollback()
                print(f"TB Load Error ({file}): {e}")

    db.close()
    print("Trial Balance + Prior Year Loaded")


#budgets
def load_budgets():

    db = SessionLocal()
    files = (DATA_DIR / "budgets").glob("*.csv")

    for file in files:

        df = pd.read_csv(file)

        try:
            for _, row in df.iterrows():

                exists = db.query(Budget).filter_by(
                    company_id=row["company_id"],
                    account_code=str(row["account_code"]),
                    month=int(row["month"]),
                    year=int(row["year"])
                ).first()

                if exists:
                    continue

                record = Budget(
                    id=str(uuid.uuid4()),
                    company_id=row["company_id"],
                    year=int(row["year"]),
                    month=int(row["month"]),
                    account_code=str(row["account_code"]),
                    account_name=str(row["account_name"]),
                    budget_amount=float(row["budget_amount"])
                )

                db.add(record)

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"Budget Load Error ({file}): {e}")

    db.close()
    print("Budgets Loaded")


#intercompany transactions
def load_intercompany_transactions():

    db = SessionLocal()
    files = (DATA_DIR / "intercompany").glob("*.csv")

    for file in files:

        df = pd.read_csv(file)

        try:
            for _, row in df.iterrows():

                exists = db.query(IntercompanyTransaction).filter_by(
                    transaction_id=row["transaction_id"]
                ).first()

                if exists:
                    continue

                record = IntercompanyTransaction(
                    id=str(uuid.uuid4()),
                    transaction_id=row["transaction_id"],
                    selling_entity_id=row["selling_entity_id"],
                    buying_entity_id=row["buying_entity_id"],
                    selling_entity_name=row["selling_entity_name"],
                    buying_entity_name=row["buying_entity_name"],
                    amount=float(row["amount"]),
                    description=row["description"],
                    gl_account=row["gl_account"],
                    period=row["date"][:7]
                )

                db.add(record)

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"Intercompany Load Error ({file}): {e}")

    db.close()
    print("Intercompany Loaded")


#bank statements
def load_bank_statements():

    db = SessionLocal()
    files = (DATA_DIR / "bank_statements").glob("*.csv")

    for file in files:

        df = pd.read_csv(file)

        try:
            for _, row in df.iterrows():

                debit = float(row["debit"]) if row["debit"] else 0.0
                credit = float(row["credit"]) if row["credit"] else 0.0

                record = BankStatements(
                    id=str(uuid.uuid4()),
                    company_id=row["company_id"],
                    date=row["date"],
                    description=row["description"],
                    debit=debit,
                    credit=credit,
                    balance=float(row["balance"]),
                    period=row["period"]
                )

                db.add(record)

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"Bank Load Error ({file}): {e}")

    db.close()
    print("Bank Statements Loaded")


#accruals
def load_accruals():

    db = SessionLocal()
    files = (DATA_DIR / "accrual_schedules").glob("*.csv")

    for file in files:

        df = pd.read_csv(file)

        try:
            for _, row in df.iterrows():

                exists = db.query(Accrual).filter_by(
                    company_id=row["company_id"],
                    accrual_type=row["accrual_type"]
                ).first()

                if exists:
                    continue

                record = Accrual(
                    id=str(uuid.uuid4()),
                    company_id=row["company_id"],
                    accrual_type=row["accrual_type"],
                    gl_account=row["gl_account"],
                    amount=float(row["amount"]),
                    frequency=row["frequency"],
                    last_booked_date=row["last_booked_date"]
                )

                db.add(record)

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"Accrual Load Error ({file}): {e}")

    db.close()
    print("Accruals Loaded")

