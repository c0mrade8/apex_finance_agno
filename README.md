# Apex Finance AI – Multi-Agent Month-End Close Orchestration System

## Overview
Apex Finance AI is an autonomous, multi-agent platform designed to automate the month-end close process across multiple portfolio companies for a Private Equity firm.

The system replaces a manual 12–15 day close cycle with an AI-driven workflow completed in 1–2 days, delivering real-time financial insights and improved accuracy.

---

## Key Features

- Multi-agent architecture with specialized financial agents  
- Autonomous execution using Celery and scheduled workflows  
- Real-time dashboard for monitoring alerts, logs, and workflow  
- Event-driven orchestration of accounting processes  
- Automated executive summary generation using LLMs  
- Email notification system for reporting  
- Cross-company financial consolidation  

---

## System Architecture

The system follows a distributed, event-driven architecture with asynchronous task execution.

### High-Level Flow

Frontend (React + Vite)  
          ↓  
FastAPI Backend (API Layer)  
          ↓  
Celery Task Queue (Redis Broker)  
          ↓  
Orchestrator (Workflow Engine)  
          ↓  
Specialized Agents  
          ↓  
PostgreSQL (Data Storage) + Redis (State Management)

### Components

- **Frontend**
  - Built with React (TypeScript)
  - Displays alerts, logs, workflow status, and charts

- **FastAPI Backend**
  - Exposes REST APIs
  - Triggers orchestrator via Celery

- **Celery + Redis**
  - Handles asynchronous execution of workflows
  - Enables background processing and scheduling

- **Orchestrator**
  - Controls execution order of agents
  - Manages workflow groups (per-company and global)

- **Agents**
  - Perform domain-specific financial analysis
  - Generate alerts and logs

- **PostgreSQL**
  - Stores financial data, alerts, logs, and results

- **Redis**
  - Acts as message broker and lightweight state store

---

## Agents Implemented

| Agent | Responsibility |
|------|----------------|
| Orchestrator | Controls workflow and execution |
| Trial Balance Validator | Validates accounting integrity |
| Variance Analysis | Detects financial deviations |
| Accrual Verification | Ensures correct accruals |
| Intercompany Agent | Handles intercompany mismatches |
| Revenue Agent | Applies revenue recognition logic |
| Expense Agent | Detects misclassified expenses |
| Cash Flow Agent | Reconciles bank and GL balances |
| Consolidation Agent | Aggregates multi-company data |
| Reporting Agent | Generates summaries and notifications |

---

## Autonomous Execution

- Celery Worker executes background tasks  
- Celery Beat enables scheduled runs  
- Redis acts as message broker and state store  

Supports:
- Manual triggering via API  
- Scheduled autonomous execution  

---

## Frontend Dashboard

- Overview of alerts, logs, and workflow status  
- Company-level processing indicators  
- Real-time updates using polling  
- Data visualization using charts  
- Agent activity tracking  

---

## Email Automation

- Executive summaries generated using LLM  
- Triggered after completion of month-end close  
- Designed for stakeholders such as CFOs and partners  

---

## Tech Stack

### Backend
- FastAPI  
- SQLAlchemy  
- PostgreSQL  
- Redis  
- Celery  

### Frontend
- React (TypeScript)  
- Vite  
- Tailwind CSS  
- Recharts  

### AI Integration
- LLM-based reasoning via agent framework  

### DevOps
- Docker  
- Docker Compose  

---

## Setup Instructions

### Clone Repository

```bash
git clone <your-repo-url>
cd apex_agno
```
### User Input
- Please find the .env file
- Add the following data:
  1. Groq API KEY
  2. SENDGRID API KEY
  3. POSTGRES PASSWORD
  
### Run with Docker
```bash
docker-compose up --build
```
This starts:
- FastAPI backend
- PostgreSQL database
- Redis
- Celery worker
- Celery beat scheduler
- Frontend

## Acess Services

| Service | URL |
| :--- | :--- |
| **Backend** | [http://localhost:8000](http://localhost:8000) |
| **Backend API** | [http://localhost:8000](http://localhost:8000) |
| **Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Frontend Dashboard** | [http://localhost:5173](http://localhost:5173) |

### Manual Set-up
-Backend
```bash
cd backend
uvicorn main:app --reload
```
-Celery Worker
```Bash
celery -A celery_app.celery worker --loglevel=info -P eventlet --concurrency=1
```

-Celery Beat
```bash
celery -A celery_app.celery worker --loglevel=info
```

-Frontend
```bash
cd frontend
npm install
npm run dev
```

### Workflow Execution
- API endpoint /orchestrator/run is triggered
- Task is queued via Celery
- Orchestrator executes agents in defined sequence
- Agents analyze financial data and generate outputs
- Alerts and logs are stored
- Reporting agent generates executive summary
- Email notification is sent
- Frontend dashboard updates in real time


### Project Structure

```text
backend/
  ├── agents/          # Individual AI agent logic
  ├── models/          # Database schemas and Pydantic models
  ├── orchestrator/    # Sequencing and execution logic
  ├── core/            # Configuration and security settings
  ├── tasks.py         # Celery task definitions
  └── celery_app.py    # Celery and Redis configuration

frontend/
  ├── components/      # Reusable UI components
  ├── api/             # API client (Axios/Fetch) integration
  └── pages/           # Main dashboard and views

docker-compose.yml     # Multi-container orchestration
```
