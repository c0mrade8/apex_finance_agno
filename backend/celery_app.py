import eventlet
eventlet.monkey_patch()

from celery import Celery

celery_app = Celery(
    "apex_finance",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=['tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    # This ensures one audit finishes before the next scheduled one starts
    worker_max_tasks_per_child=1 
)

# 📅 THE SCHEDULER (Autonomous Mode)
celery_app.conf.beat_schedule = {
    "auto-audit-every-5-min": {
        "task": "backend.tasks.run_audit_task",
        "schedule": 300.0,  # Every 5 minutes for the demo
        "args": ("2026-01",) # Default period
    },
}