from database.connection import engine, Base

import models.company
import models.trial_balance
import models.budget
import models.bank_statements
import models.alert
import models.intercompany
import models.accrual
import models.agent_log

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()