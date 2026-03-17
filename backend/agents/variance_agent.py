import uuid
import datetime
from core.state_manager import set_agent_status
from models.trial_balance import TrialBalance
from models.budget import Budget
from models.alert import Alert
from models.agent_log import AgentLog

class VarianceAgent:
    def __init__(self, db, agent):
        """
        Initialize with SQLAlchemy session and an Agno Agent instance.
        """
        self.db = db
        self.agent = agent

    def run(self, company_id, period):
        try:
            # 1. Signal start to Orchestrator/UI
            set_agent_status("VarianceAgent", company_id, "STARTED")

            # Fetch Trial Balance and Budget data
            entries = self.db.query(TrialBalance).filter_by(
                company_id=company_id, period=period
            ).all()

            budgets = self.db.query(Budget).filter_by(
                company_id=company_id
            ).all()

            # Early exit if data is missing
            if not entries or not budgets:
                self.save_log(company_id, "VarianceAgent", f"Missing data for period {period}")
                set_agent_status("VarianceAgent", company_id, "COMPLETED")
                return

            # Map budget by account code and month
            budget_map = {(b.account_code, b.month): b.budget_amount for b in budgets}

            for t in entries:
                try:
                    # Extract month from period string (e.g., '2025-01')
                    year, month = map(int, t.period.split("-"))
                except (ValueError, AttributeError):
                    continue

                if (t.account_code, month) not in budget_map:
                    continue

                # 2. Accounting Logic: Normal Balance Correction
                # Assets/Expenses: (Debit - Credit) | Revenue/Liabilities: (Credit - Debit)
                raw_balance = t.debit - t.credit
                if t.account_type in ['Revenue', 'Liability', 'Equity']:
                    actual = -raw_balance
                else:
                    actual = raw_balance

                budget = budget_map[(t.account_code, month)]

                # Prevent DivisionByZero; handle cases where actual exists but budget is 0
                if budget == 0:
                    if abs(actual) > 1000:
                        dollar_variance = actual
                        percent_variance = 100.0
                    else:
                        continue
                else:
                    dollar_variance = actual - budget
                    percent_variance = (dollar_variance / budget) * 100

                # 3. Assignment Materiality Rule: Variance > 10% OR > $50,000
                if abs(percent_variance) > 10 or abs(dollar_variance) > 50000:
                    
                    prompt = f"""
                    Context: You are a PE Fund Controller analyzing {t.account_type} for {company_id}.
                    Account: {t.account_name} ({t.account_code})

                    Financial Performance:
                    - Actual: ${actual:,.2f}
                    - Budget: ${budget:,.2f}
                    - Variance: ${dollar_variance:,.2f} ({percent_variance:.2f}%)

                    Task:
                    - Explain the likely business reason for this variance.
                    - Assess the impact on the portfolio company's EBITDA.
                    - Provide a professional recommendation for the management team.
                    """

                    response = self.agent.run(prompt)

                    # Persist the finding as a High Severity Alert
                    self.create_alert(company_id, response.content, "HIGH")

            self.db.commit()
            
            # 4. Signal success for the next Sequential Agent to begin
            set_agent_status("VarianceAgent", company_id, "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("VarianceAgent", company_id, "FAILED")
            print(f"❌ Error in VarianceAgent for {company_id}: {e}")

    def create_alert(self, company_id, message, severity):
        self.db.add(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            message=message,
            severity=severity
        ))

    def save_log(self, company_id, agent, message):
        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent,
            company_id=company_id,
            message=message,
            timestamp=datetime.datetime.now()
        ))
        self.db.commit()