from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database.connection import get_db
from backend.modules.reports.schemas import (
    StartResearchRequest,
    ResearchJobResponse,
    AppearanceResponse,
    TimelineItemResponse,
    SourceResponse,
    ReportResponse
)
from backend.modules.reports import service
from backend.modules.persons.service import get_person_by_id
from backend.workers.tasks import execute_research_pipeline

research_router = APIRouter(prefix="/research", tags=["Research Operations"])
person_reports_router = APIRouter(prefix="/persons", tags=["Appearances & Reports"])


@research_router.post("/start", response_model=ResearchJobResponse, status_code=status.HTTP_202_ACCEPTED)
def start_research_job(
    payload: StartResearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Initiates an asynchronous public appearance discovery and intelligence research job."""
    person = get_person_by_id(db, payload.person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    job = service.create_research_job(db, payload.person_id)

    # Dispatch to background executor
    if settings.WORKER_MODE == "celery":
        try:
            from backend.workers.celery_app import celery_app
            celery_app.send_task("execute_research_pipeline", args=[job.id])
        except Exception:
            # Fallback to FastAPI BackgroundTasks if Celery daemon is unavailable
            background_tasks.add_task(execute_research_pipeline, job.id)
    else:
        background_tasks.add_task(execute_research_pipeline, job.id)

    return job


@research_router.get("/{job_id}", response_model=ResearchJobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Polls the status, progress (0-100%), and error state of a research job."""
    job = service.get_research_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    return job


@person_reports_router.get("/{person_id}/appearances", response_model=List[AppearanceResponse])
def get_appearances(
    person_id: str,
    identity_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieves discovered public appearances for a person, optionally filtered by identity status."""
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return service.get_appearances_by_person(db, person_id, identity_status=identity_status)


@person_reports_router.get("/{person_id}/timeline", response_model=List[TimelineItemResponse])
def get_timeline(person_id: str, db: Session = Depends(get_db)):
    """Retrieves chronological timeline of public appearances."""
    report = service.generate_report_for_person(db, person_id)
    if not report:
        raise HTTPException(status_code=404, detail="Person not found")
    return report["timeline"]


@person_reports_router.get("/{person_id}/sources", response_model=List[SourceResponse])
def get_sources(person_id: str, db: Session = Depends(get_db)):
    """Retrieves all collected web and media source references for an individual."""
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return service.get_sources_by_person(db, person_id)


@person_reports_router.get("/{person_id}/report", response_model=ReportResponse)
def get_consolidated_report(person_id: str, db: Session = Depends(get_db)):
    """Generates and retrieves the consolidated public appearance intelligence report."""
    report = service.generate_report_for_person(db, person_id)
    if not report:
        raise HTTPException(status_code=404, detail="Person not found")
    return report

