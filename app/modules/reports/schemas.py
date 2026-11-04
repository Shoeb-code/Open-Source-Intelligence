from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class SourceResponse(BaseModel):
    id: str
    source_url: str
    canonical_url: Optional[str]
    source_type: str
    extraction_status: str
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppearanceAnalysisResponse(BaseModel):
    summary: Optional[str]
    topics: Optional[List[str]] = []
    key_points: Optional[List[str]] = []
    person_role: Optional[str]
    evidence: Optional[List[str]] = []
    model_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AppearanceResponse(BaseModel):
    id: str
    person_id: str
    appearance_type: str
    title: str
    description: Optional[str]
    publisher: Optional[str]
    published_at: Optional[datetime]
    identity_status: str
    confidence_score: float
    sources: List[SourceResponse] = []
    analysis: Optional[AppearanceAnalysisResponse] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StartResearchRequest(BaseModel):
    person_id: str


class ResearchJobResponse(BaseModel):
    id: str
    person_id: str
    status: str
    progress: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimelineItemResponse(BaseModel):
    appearance_id: str
    date: str
    title: str
    appearance_type: str
    publisher: Optional[str]
    summary: Optional[str]
    confidence_score: float
    primary_source_url: Optional[str]


class ReportResponse(BaseModel):
    person: Dict[str, Any]
    executive_summary: str
    statistics: Dict[str, Any]
    timeline: List[TimelineItemResponse]
    recurring_topics: List[Dict[str, Any]]
    important_statements: List[Dict[str, Any]]
    limitations_and_coverage: str
    generated_at: str

