"""
Application entrypoint: wires every backend module's router into one
FastAPI app.

Run with:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

--host 0.0.0.0 is what makes the LAN client-server mode possible: it binds
on every network interface, not just localhost, so a second laptop on the
same network can reach this machine's IP address.
"""

from fastapi import FastAPI

from backend.modules.history.routes import router as history_router
from backend.modules.ingestion.routes import router as ingestion_router
from backend.modules.knowledge_base.routes import router as knowledge_base_router
from backend.modules.llm.routes import router as llm_router
from backend.modules.monitor.routes import router as monitor_router
from backend.modules.reports.routes import router as reports_router

app = FastAPI(title="Sovereign On-Premise Agentic AI Workbench")

app.include_router(history_router)
app.include_router(ingestion_router)
app.include_router(knowledge_base_router)
app.include_router(llm_router)
app.include_router(monitor_router)
app.include_router(reports_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
