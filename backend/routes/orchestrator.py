from fastapi import APIRouter
from tasks import run_audit_task

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])

@router.post("/run")
def run_close(period: str):
    # .delay() pushes the job to Redis and returns immediately
    task = run_audit_task.delay(period)
    
    return {
        "task_id": task.id,
        "status": "dispatched",
        "message": f"Background audit started for {period}"
    }