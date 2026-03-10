# Lette AI — Intelligent Property Management Operating System

> "An AI operating system for property managers that reads every message, knows every tenant, tracks every pattern, and tells you exactly what to do — before you even ask."

## Overview

Lette AI is a full-stack intelligent property management communication system. It analyses emails across a portfolio of properties, auto-prioritises issues, generates AI-drafted responses, detects portfolio-wide patterns, and proactively surfaces what matters most — turning 100 messages into 5 clear priorities in under a minute.

Built for the Lette AI hackathon challenge targeting Forward Deployed Engineers and Product Engineers.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ · FastAPI (async) |
| Database | SQLite via `aiosqlite` |
| AI | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| Real-time | WebSocket via FastAPI |
| Frontend | React 18 · Tailwind CSS · Vite |
| Voice | Web Speech API (browser TTS) |
| Export | `openpyxl` (Excel) |

---

## Project Structure

```
lette-ai/
├── backend/
│   ├── main.py                     # FastAPI entry point, CORS, lifespan startup
│   ├── config.py                   # Environment config, constants
│   ├── database.py                 # SQLite async schema + connection helpers
│   ├── models.py                   # Pydantic request/response schemas
│   ├── ingest.py                   # Load JSON data, build contact profiles
│   ├── ai_pipeline.py              # Thread analysis, morning brief, pattern detection
│   ├── knowledge_base.py           # Contact profile management + auto-fill logic
│   ├── workflow_engine.py          # Auto-escalation, pattern detection, status rules
│   ├── export_engine.py            # Excel/report generation
│   ├── notification_engine.py      # Voice script + push notification generation
│   ├── email_processor.py          # Real-time incoming email pipeline
│   ├── procurement_engine.py       # Contractor procurement & negotiation engine
│   └── routers/
│       ├── dashboard.py            # Dashboard summary + morning brief
│       ├── threads.py              # Thread CRUD + analysis
│       ├── messages.py             # Message queries + incoming email webhook
│       ├── properties.py           # Property endpoints + aggregated stats
│       ├── contacts.py             # Contact/tenant knowledge base
│       ├── exports.py              # Excel download endpoints
│       ├── notifications.py        # Voice + push notification endpoints
│       ├── procurement.py          # Contractor procurement endpoints
│       ├── chat.py                 # Natural language query endpoint
│       └── ws.py                   # WebSocket for real-time updates
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Layout.jsx              # App shell: sidebar + main + detail panel
│       │   ├── Dashboard.jsx           # Main dashboard orchestrator
│       │   ├── ThreadList.jsx          # Priority-sorted thread list
│       │   ├── ThreadDetail.jsx        # Full thread view (slide-out panel)
│       │   ├── MorningBrief.jsx        # AI morning brief modal/card
│       │   ├── VoiceBrief.jsx          # Voice playback (Web Speech API)
│       │   ├── PatternAlerts.jsx       # Portfolio-wide pattern warnings
│       │   ├── ProcurementPanel.jsx    # Contractor quote tracking per thread
│       │   ├── ProcurementDashboard.jsx # All active procurement jobs
│       │   ├── ContractorDirectory.jsx # Contractor registry with performance history
│       │   ├── NotificationToast.jsx   # Real-time WebSocket notification pop-ups
│       │   ├── DraftQueue.jsx          # PM draft review queue
│       │   ├── AutoReplyLog.jsx        # Auto-sent reply audit log
│       │   ├── SimulateButton.jsx      # Demo mode email simulator
│       │   └── ExportButton.jsx        # Excel export trigger
│       └── hooks/
│           ├── useWebSocket.js         # WebSocket connection + event handling
│           └── useVoice.js             # Web Speech API TTS hook
├── data/
│   └── proptech-test-data__1_.json
├── exports/                            # Generated Excel files (gitignored)
├── .env
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

```bash
# 1. Create .env in the project root
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "LETTE_DB_PATH=lette.db" >> .env
echo "ANALYSIS_BATCH_SIZE=5" >> .env
echo "ANALYSIS_MODEL=claude-sonnet-4-20250514" >> .env

# 2. Backend
cd backend
pip install -r requirements.txt
cp ../.env .env
python main.py
# → Inits DB, ingests data, starts on http://localhost:8000
# → API docs at http://localhost:8000/docs

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → Opens on http://localhost:5173
```

---

## Core Features

### AI Analysis Pipeline

- **Thread Analysis** — Claude reads every email thread, scores urgency (1–10), classifies category, extracts risk flags, and generates a recommended action plan + draft reply.
- **Morning Brief** — Summarises the entire portfolio into a written briefing and a TTS-optimised voice script under 60 seconds.
- **Pattern Detection** — Identifies portfolio-wide patterns: recurring maintenance clusters, sentiment decline, escalation spikes, and overdue responses.
- **Smart Drafts** — AI-drafted responses auto-fill tenant name, unit, and lease details. Unknown contacts are prompted politely for missing info.

### Real-Time Email Processing

Incoming emails trigger a full 7-step pipeline:

1. **Identify sender** — match against the contact knowledge base
2. **Match thread** — link to existing thread or create new
3. **Load context** — assemble tenant profile, thread history, property state
4. **AI analysis** — full contextual analysis with action level decision
5. **Decide action** — `pm_immediate` / `pm_review` / `auto_reply` / `info_only`
6. **Execute** — queue drafts, send auto-replies, escalate threads, trigger alerts
7. **Notify** — push real-time WebSocket events to the dashboard

### Contractor Procurement Engine

Automates the full procurement lifecycle when maintenance work is needed:

| Stage | What happens |
|-------|-------------|
| Detect need | AI classifies maintenance thread and flags contractor requirement |
| Find contractors | Matches specialty, service area, emergency availability |
| Send quote requests | AI drafts personalised emails; sets deadlines (48h high, 72h low) |
| Process responses | AI extracts price, availability, duration from contractor replies |
| Compare quotes | Generates comparison matrix with pros/cons and recommendation |
| Negotiate | Uses competitive intelligence to draft negotiation emails |
| Book & notify | Confirms booking, notifies tenant, updates thread |

For **critical** urgency: skips quoting — auto-books the best emergency-available contractor immediately.

### Auto-Escalation Rules

The workflow engine applies business rules post-analysis:

- 3+ follow-ups from same sender → escalate to HIGH
- Thread open > 5 days unresolved → +2 urgency points
- Legal terms (RTB, solicitor, tribunal) → minimum score 8
- Threatening sentiment → minimum score 8
- All escalations logged in `escalation_history` with reasons

### Exports

One-click Excel downloads (`.xlsx`) with colour-coded urgency, auto-sized columns, and filter headers:

- **Open Issues** — all open threads with contact details and recommended actions
- **Tenant Contacts** — full contact sheet with lease dates and sentiment
- **Overdue Responses** — threads where tenants are waiting
- **Property Report** — per-property summary with health scores
- **Contractor Invoices** — contractor threads with payment references

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard` | Stats + top 5 priorities |
| `GET/POST` | `/api/dashboard/morning-brief` | Get or generate morning brief |
| `GET` | `/api/threads` | Filtered, sorted thread list |
| `POST` | `/api/threads/{id}/analyse` | Trigger AI analysis for one thread |
| `POST` | `/api/messages/incoming` | Incoming email webhook |
| `POST` | `/api/demo/simulate-email` | Trigger a demo scenario |
| `GET` | `/api/procurement` | All active procurement jobs |
| `POST` | `/api/procurement/{id}/book` | Book selected contractor |
| `GET` | `/api/contractors` | Contractor registry |
| `GET` | `/api/exports/open-issues` | Download Excel of open issues |
| `POST` | `/api/chat` | Natural language query |
| `WS` | `/ws` | Real-time event stream |

Full interactive docs available at `http://localhost:8000/docs`.

---

## Demo Scenarios

Use the **Simulate** button (demo mode only) to trigger pre-built email scenarios live:

| Scenario | What it shows |
|----------|--------------|
| `tenant_followup` | Eoin Byrne's 4th follow-up mentioning the RTB → CRITICAL escalation, PM-immediate alert |
| `emergency` | New tenant reports gas smell → CRITICAL, voice alert |
| `new_prospect` | Unknown person asks about 3-bed availability → LOW, auto-draft requesting details |
| `contractor_invoice` | Contractor sends second invoice reminder → MEDIUM, draft queued for PM review |
| `unknown_sender` | Vague email from unrecognised address → LOW, draft requesting clarification |

---

## Dataset

`data/proptech-test-data__1_.json` contains:

- 100 emails · 92 threads · 5 Irish properties (BTR and PRS)
- Sender types: tenant (36), internal (18), contractor (15), legal (9), system (8), landlord (6), prospect (5), external (3)
- 68 unread · 32 read

---

## Build Order

| Phase | Focus | Time |
|-------|-------|------|
| 1 | Data layer: schema + ingest | 45 min |
| 2 | AI pipeline: thread analysis + morning brief | 1.5 h |
| 3 | Workflow engine + knowledge base | 45 min |
| 4 | REST API: all routers | 1 h |
| 5 | WebSocket + bulk analysis endpoint | 30 min |
| 6 | React dashboard: core view + ThreadDetail | 2 h |
| 7 | Advanced: exports, voice, search, drafts | 1.5 h |
| 8 | Polish: animations, empty states, mobile | 1 h |
