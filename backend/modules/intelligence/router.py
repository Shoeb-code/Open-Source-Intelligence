from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.modules.intelligence import service
from backend.modules.intelligence.schemas import (
    GenerateInsightsRequest,
    InsightsHistoryResponse,
    InsightsReportResponse,
)
from backend.modules.persons.service import get_person_by_id

router = APIRouter(prefix="/persons", tags=["AI Insights"])


@router.post(
    "/{person_id}/generate-insights",
    response_model=InsightsReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_person_insights(
    person_id: str,
    payload: GenerateInsightsRequest = Body(default_factory=GenerateInsightsRequest),
    db: Session = Depends(get_db),
):
    """Generates and persists a 7-section AI insights report from existing collected database records."""
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return service.generate_and_save_insights(db, person, request=payload)


@router.get("/{person_id}/insights", response_model=InsightsHistoryResponse)
def get_person_insights(
    person_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves the latest AI insights report and generation history for a person."""
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return service.get_insights_history(db, person_id)

