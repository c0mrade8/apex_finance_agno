from fastapi import APIRouter
from database.connection import SessionLocal
from models.agent_log import AgentLog

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("/")
def get_logs():

    db = SessionLocal()

    try:
        logs = db.query(AgentLog).all()

        return [
            {
                "agent": l.agent_name,
                "message": l.message,
                "time": l.timestamp
            }
            for l in logs
        ]
    finally:
        db.close()