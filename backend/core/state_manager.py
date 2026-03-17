# core/state_manager.py

from core.redis_client import redis_client
from models.workflow_state import WorkflowState
from database.connection import SessionLocal
import datetime
import uuid

def set_agent_status(agent, company_id, status):

    # 1.Redis (real-time)
    key = f"{company_id}:{agent}"
    redis_client.set(key, status)

    # 2.PostgreSQL (persistent)
    db = SessionLocal()

    try:
        record = WorkflowState(
            id=str(uuid.uuid4()),
            company_id=company_id,
            agent_name=agent,
            status=status,
            timestamp=datetime.datetime.now()
        )

        db.add(record)
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"State Error: {e}")

    finally:
        db.close()

def get_workflow_progress(company_id):
    db = SessionLocal()

    states = db.query(WorkflowState).filter_by(company_id=company_id).all()

    return [
        {
            "agent": s.agent_name,
            "status": s.status,
            "time": s.timestamp
        }
        for s in states
    ]