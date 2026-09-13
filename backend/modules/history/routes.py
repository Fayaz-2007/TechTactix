"""
FastAPI routes for browsing/managing persistent chat history and the
optional "projects" grouping layer on top of it.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.modules.history.db import (
    create_project,
    create_session,
    delete_session,
    get_messages,
    list_projects,
    list_sessions,
    project_exists,
    session_exists,
)
from backend.modules.knowledge_base.vector_store import list_documents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["history", "projects"])


class ProjectRequest(BaseModel):
    name: str


@router.get("/history")
async def get_history(project_id: Optional[str] = None):
    return list_sessions(project_id=project_id)


@router.get("/history/{session_id}")
async def get_session_history(session_id: str):
    if not session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return get_messages(session_id)


@router.delete("/history/{session_id}")
async def delete_session_history(session_id: str):
    if not delete_session(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return {"status": "deleted", "session_id": session_id}


@router.post("/projects")
async def create_project_route(request: ProjectRequest):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name is required.")

    project_id = str(uuid.uuid4())
    create_project(project_id, name)
    return {"id": project_id, "name": name}


@router.get("/projects")
async def get_projects():
    return list_projects()


@router.get("/projects/{project_id}/documents")
async def get_project_documents(project_id: str):
    if not project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return list_documents(project_id=project_id)


@router.get("/projects/{project_id}/sessions")
async def get_project_sessions(project_id: str):
    if not project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return list_sessions(project_id=project_id)
