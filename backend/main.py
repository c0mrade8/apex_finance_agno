from fastapi import FastAPI
from routes import orchestrator, alerts, logs, workflow
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="Apex Finance AI Platform")

#cors permissions for frontend

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Your React URL
    allow_credentials=True,
    allow_methods=["*"], # Allow GET, POST, etc.
    allow_headers=["*"], # Allow all headers
)

app.include_router(orchestrator.router)
app.include_router(alerts.router)
app.include_router(logs.router)
app.include_router(workflow.router)
#app.include_router(companies.router)