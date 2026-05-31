"""
nf-core Pipeline management API — list registry, see installed, install on demand.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.db.job import InstalledPipeline
from app.models.db.user import User
from app.api.routes.auth import get_current_user
from app.services import nfcore_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class InstallRequest(BaseModel):
    name: str
    revision: str | None = None


@router.get("/registry")
def get_registry():
    """Curated list of nf-core pipelines available to install."""
    installed = set(nfcore_manager.list_installed())
    registry = nfcore_manager.list_registry()
    for p in registry:
        p["installed"] = p["name"] in installed
    return registry


@router.get("/installed")
def get_installed(db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    fs_installed = nfcore_manager.list_installed()
    return {"installed": fs_installed}


@router.post("/install")
def install(req: InstallRequest, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    entry = nfcore_manager.get_registry_entry(req.name)
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline not in registry")

    # Record install intent
    rec = InstalledPipeline(name=req.name, revision=req.revision,
                            status="installing", description=entry.get("description"))
    db.add(rec)
    db.commit()
    db.refresh(rec)

    from app.tasks.pipeline_tasks import install_pipeline_task
    task = install_pipeline_task.delay(req.name, req.revision)

    return {"job_id": task.id, "pipeline": req.name, "status": "installing"}


@router.get("/install/{task_id}")
def install_status(task_id: str):
    from app.core.celery_app import celery
    res = celery.AsyncResult(task_id)
    info = res.info if isinstance(res.info, dict) else {}
    return {
        "state": res.state,
        "progress": info.get("progress", 0),
        "message": info.get("message", ""),
        "result": res.result if res.successful() else None,
    }
