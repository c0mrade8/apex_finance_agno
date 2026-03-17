from fastapi import FastAPI
from routes import orchestrator, alerts, logs, workflow
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Apex Finance AI Platform")

app.include_router(orchestrator.router)
app.include_router(alerts.router)
app.include_router(logs.router)
app.include_router(workflow.router)
#app.include_router(companies.router)