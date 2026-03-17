from services.data_ingestion import load_trial_balances, load_budgets, load_intercompany_transactions, load_bank_statements, load_accruals

if __name__ == "__main__":
    print("Starting Data Ingestion......")

    load_trial_balances()
    load_budgets()
    load_intercompany_transactions()
    load_bank_statements()
    load_accruals()

    print("ALL DATA LOADED SUCCESSFULLY!")