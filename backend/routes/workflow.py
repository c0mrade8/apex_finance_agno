from fastapi import APIRouter
from database.connection import SessionLocal
from models.workflow_state import WorkflowState

router = APIRouter(prefix="/workflow", tags=["Workflow"])

@router.get("/")
def get_workflow():

    db = SessionLocal()

    try:

        states = db.query(WorkflowState).all()

        return [
            {
                "agent": s.agent_name,
                "company": s.company_id,
                "status": s.status,
                "time": s.timestamp
            }
            for s in states
        ]
    finally:
        db.close()