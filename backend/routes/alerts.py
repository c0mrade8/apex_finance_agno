from fastapi import APIRouter
from database.connection import SessionLocal
from models.alert import Alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("/")
def get_alerts():

    db = SessionLocal()

    try:

        alerts = db.query(Alert).all()

        return [
            {
                "company": a.company_id,
                "message": a.message,
                "severity": a.severity
            }
            for a in alerts
        ]

    finally:
        db.close()