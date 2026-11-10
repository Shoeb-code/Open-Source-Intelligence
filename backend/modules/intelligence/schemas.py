from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceCitation(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    published_at: Optional[str] = None


class InsightItem(BaseModel):
    title: str = Field(..., description="Concise headline of the insight")
    detail: str = Field(..., description="Evidence-backed insight or carefully labeled hypothesis")
    sub_category: Optional[str] = Field(None, description="e.g. Current Role, Expertise, Business Model, Opportunities")
    claim_type: Literal["VERIFIED_FACT", "AI_HYPOTHESIS"] = "VERIFIED_FACT"
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    supporting_sources: List[SourceCitation] = Field(default_factory=list)


class InsightSection(BaseModel):
    summary: Optional[str] = None
    insufficient_evidence: bool = False
    insufficient_evidence_note: Optional[str] = None
    items: List[InsightItem] = Field(default_factory=list)


class InsightsReportPayload(BaseModel):
    executive_overview: str
    data_coverage: Dict[str, int] = Field(default_factory=dict)
    professional_insights: InsightSection
    interest_insights: InsightSection
    knowledge_and_expertise: InsightSection
    company_insights: InsightSection
    recent_activities: InsightSection
    business_insights: InsightSection
    key_takeaways: InsightSection


class GenerateInsightsRequest(BaseModel):
    focus_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional analyst lens or priority context for insight synthesis.",
    )


class InsightsReportResponse(BaseModel):
    id: str
    person_id: str
    model_name: str
    prompt_version: str
    generation_time_seconds: float
    source_count: int
    generated_at: datetime
    report: InsightsReportPayload

    model_config = ConfigDict(from_attributes=True)


class InsightsHistoryResponse(BaseModel):
    person_id: str
    latest_report: Optional[InsightsReportResponse] = None
    history: List[InsightsReportResponse] = Field(default_factory=list)

