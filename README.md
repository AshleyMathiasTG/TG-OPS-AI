# TG OPS AI — Operational Intelligence Platform

> **AI-powered recruitment operations platform** built with LangGraph multi-agent orchestration, FastAPI, PostgreSQL, and Next.js 15.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           LANGGRAPH PIPELINE                        │
│                                                                     │
│  Scheduler / API Trigger                                            │
│       │                                                             │
│       ▼                                                             │
│  [data_fetch] ──► [data_clean] ──► [executive_summary]             │
│       │                                  │                          │
│       │                                  ▼                          │
│       │                          [risk_detection]                   │
│       │                                  │                          │
│       │                                  ▼                          │
│       │                            [analytics]                      │
│       │                                  │                          │
│       │                                  ▼                          │
│       │                         [decision_router]                   │
│       │                         /             \                     │
│       │              count < 3               count >= 3             │
│       │                 │                       │                   │
│       │           [notification]    [action_recommendation]         │
│       │                 │                  │                        │
│       │                 │             [approval]                    │
│       │                 │                  │                        │
│       │                 └──────────────────┘                        │
│       │                          │                                  │
│       │                    [persistence]                            │
│       │                          │                                  │
│       │                        [END]                                │
└─────────────────────────────────────────────────────────────────────┘
```

### AI Agent Roles

| Agent | Model | Responsibility |
|-------|-------|----------------|
| Executive Summary | `gpt-4o-mini` | Concise operational highlights |
| Database Query | `gpt-4o` | SQL generation for TG Database |
| Risk Detection | `gpt-4o` | Pattern-based risk identification |
| Analytics | Rule-based | KPI computation, trends |
| Action Recommendation | `gpt-4o` | Generates mitigation strategies |
| Formatting | `gpt-4o-mini` | Stakeholder-friendly output |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, TailwindCSS, Recharts, Framer Motion |
| Backend | FastAPI, Python 3.12, LangGraph 1.x, LangChain |
| AI | OpenAI API (gpt-4o, gpt-4o-mini) |
| Database | PostgreSQL (platform), MySQL (TG source, read-only) |
| ORM | SQLAlchemy 2.0 + Alembic |
| Scheduler | APScheduler 3.x |
| Infrastructure | Docker, Docker Compose |

---

## Project Structure

```
tg-ops-ai/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic settings
│   │   │   ├── database.py       # PostgreSQL connections
│   │   │   ├── tg_database.py    # MySQL source DB (read-only)
│   │   │   └── logging_config.py
│   │   ├── api/routers/
│   │   │   ├── pipeline.py       # Pipeline trigger + status
│   │   │   ├── dashboard.py      # KPIs + snapshots
│   │   │   ├── alerts.py         # Operational alerts
│   │   │   ├── approvals.py      # Approval workflow
│   │   │   ├── notifications.py  # In-app notifications
│   │   │   └── analytics.py      # Trends + heatmap
│   │   ├── db/models/            # SQLAlchemy ORM models (10 tables)
│   │   └── schemas/              # Pydantic request/response schemas
│   ├── agents/
│   │   ├── state.py              # TypedDict state definition
│   │   ├── graph.py              # LangGraph compiled graph
│   │   └── nodes/
│   │       ├── data_fetch.py     # TG DB / fixture loader
│   │       ├── data_clean.py     # ETL + normalisation
│   │       ├── executive_summary.py
│   │       ├── risk_detection.py
│   │       ├── analytics.py
│   │       ├── decision_router.py # Consecutive issue check
│   │       ├── action_recommendation.py
│   │       ├── approval.py
│   │       ├── notification.py
│   │       └── persistence.py
│   └── scheduler/
│       └── pipeline_scheduler.py  # APScheduler (hourly + daily)
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Executive dashboard
│   │   ├── alerts/               # Active alerts feed
│   │   ├── approvals/            # Human-in-the-loop approval center
│   │   ├── notifications/        # Notification center
│   │   └── analytics/            # KPI trends + heatmap
│   ├── components/
│   │   ├── layout/               # Sidebar, TopBar
│   │   ├── dashboard/            # KpiCards, ExecutiveSummary, TrendChart, Heatmap
│   │   ├── approvals/            # ApprovalCard with feedback
│   │   ├── alerts/               # AlertItem with dismiss
│   │   ├── notifications/        # NotificationBell
│   │   └── ui/                   # Badge, Button, Card (design system)
│   └── lib/
│       ├── api.ts                # Typed API client
│       └── utils.ts              # Helpers
├── db/
│   ├── migrations/               # Alembic migrations
│   └── seeds/fixtures.json       # Offline fixture data
├── docker-compose.yml
└── .env
```

---

## Quick Start

### Option A: Local Development (No Docker)

**Prerequisites**: Python 3.12, Node.js 22, PostgreSQL running

```bash
# 1. Clone / navigate to project
cd "TG OPS AI"

# 2. Backend setup
cd backend
pip install -r requirements.txt
# OR use the existing .venv:
.\.venv\Scripts\Activate.ps1

# 3. Start PostgreSQL (or use Docker just for DB)
docker run -d --name tg_postgres -e POSTGRES_USER=tgops -e POSTGRES_PASSWORD=tgops -e POSTGRES_DB=tg_ops_ai -p 5432:5432 postgres:16-alpine

# 4. Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# With PYTHONPATH set:
$env:PYTHONPATH="backend"; uvicorn backend.app.main:app --reload --port 8000

# 5. Frontend
cd ../frontend
npm install
npm run dev

# 6. Access
# Frontend:  http://localhost:3000
# API docs:  http://localhost:8000/api/docs
# Health:    http://localhost:8000/health
```

### Option B: Docker Compose (Full Stack)

```bash
docker compose up --build
```

Access:
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/docs
- **Health**: http://localhost:8000/health

---

## Key Business Logic

### Consecutive Issue Detection (3× Rule)

```
For every detected issue (by issue_key = hash of type + entity + account):
  - If occurrence_count < 3  → Store alert, send INFO/WARNING notification
  - If occurrence_count >= 3 → Generate AI recommendation, create approval card
```

### Risk Categories Detected

| Type | Description |
|------|-------------|
| `INTERVIEW_NO_SHOW` | Candidate missed scheduled interview |
| `TECH_REJECTION` | Technical rejection post phone screen |
| `BUDGET_MISMATCH` | Candidate salary expectation exceeds budget |
| `AGING_SUBMISSION` | Open position aging beyond SLA threshold |
| `RECRUITER_OVERLOAD` | Recruiter managing too many active submissions |
| `CLIENT_RISK` | High rejection/no-show rate for a specific account |
| `PIPELINE_STAGNATION` | No movement in a req for extended period |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/api/v1/pipeline/trigger` | Manually run the AI pipeline |
| `GET` | `/api/v1/pipeline/status/{run_id}` | Poll pipeline run status |
| `GET` | `/api/v1/dashboard/summary` | Latest KPIs + executive summary |
| `GET` | `/api/v1/alerts` | Active operational alerts |
| `PATCH` | `/api/v1/alerts/mark-read` | Mark alerts as read |
| `GET` | `/api/v1/approvals` | Pending AI recommendations |
| `PATCH` | `/api/v1/approvals/{id}/decide` | Approve or reject |
| `POST` | `/api/v1/approvals/{id}/feedback` | Submit thumbs up/down |
| `GET` | `/api/v1/notifications` | In-app notifications |
| `GET` | `/api/v1/analytics/overview` | Full analytics snapshot |
| `GET` | `/api/v1/analytics/risk-heatmap` | Account risk scores |

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `alerts` | Operational alerts from AI agents |
| `risk_events` | Detected risk patterns |
| `sla_events` | SLA breach tracking |
| `recommendations` | AI-generated action plans |
| `approvals` | Human-in-the-loop decisions |
| `feedback` | Thumbs up/down on outcomes |
| `notifications` | In-app notification log |
| `execution_logs` | Agent run audit trail |
| `issue_occurrences` | Consecutive detection tracker |
| `dashboard_snapshots` | Periodic KPI snapshots |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_DB` | Database name | `tg_ops_ai` |
| `DB_HOST` | TG source MySQL host | `10.60.20.8` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_MODEL` | Default model | `gpt-4o-mini` |
| `TGAP_FIXTURE_ONLY` | Use fixture data | `1` |
| `SKIP_PLATFORM_DB_PERSIST` | Skip DB writes | `1` |
| `DISABLE_SCHEDULER` | Disable APScheduler | `0` |

---

## Development Notes

- **Offline mode**: Set `TGAP_FIXTURE_ONLY=1` to use `db/seeds/fixtures.json` instead of MySQL
- **Skip DB writes**: Set `SKIP_PLATFORM_DB_PERSIST=1` when PostgreSQL is unavailable — all endpoints return rich mock data
- **LangSmith tracing**: Set `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` for full agent observability
- **Models**: Each agent has its own model override variable (`ORCHESTRATOR_MODEL`, `QUERY_AGENT_MODEL`, etc.)

---

## POC Scope

This is a production-grade POC. In production, add:
- JWT authentication
- Role-based access control (RBAC)
- Redis caching layer
- Teams/Outlook notification integration
- Email delivery pipeline
- CI/CD pipeline
- Monitoring (Datadog/Prometheus)
