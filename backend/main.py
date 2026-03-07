import logging
import os
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    logger.info("Initialising database…")
    await init_db()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) FROM messages") as c:
            msg_count = (await c.fetchone())[0]

    if msg_count == 0:
        logger.info("No data found — running ingestion…")
        from ingest import ingest_data
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await ingest_data()
    else:
        logger.info(f"Database ready ({msg_count} messages already loaded).")

    logger.info("🚀 Lette AI backend started. AI analysis ready — trigger from dashboard.")
    yield
    # ── Shutdown ─────────────────────────────────────────────
    logger.info("Shutting down.")


app = FastAPI(
    title="Lette AI — Property Management OS",
    description="Intelligent property management communication triage system.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
from routers import (
    dashboard, threads, messages, properties,
    contacts, procurement, exports, notifications, chat, ws
)

app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(threads.router, prefix="/api", tags=["Threads"])
app.include_router(messages.router, prefix="/api", tags=["Messages"])
app.include_router(properties.router, prefix="/api", tags=["Properties"])
app.include_router(contacts.router, prefix="/api", tags=["Contacts"])
app.include_router(procurement.router, prefix="/api", tags=["Procurement"])
app.include_router(exports.router, prefix="/api", tags=["Exports"])
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(ws.router, tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "Lette AI Property Management OS",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/api/health", tags=["Health"])
async def health():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM messages") as c:
            messages_count = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM threads") as c:
            threads_count = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM threads WHERE analysed_at IS NOT NULL"
        ) as c:
            analysed_count = (await c.fetchone())[0]

    return {
        "status": "healthy",
        "messages": messages_count,
        "threads": threads_count,
        "analysed": analysed_count,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
