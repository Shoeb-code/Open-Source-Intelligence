from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class ExperienceItem(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    company_linkedin_profile_url: Optional[str] = None
    logo_url: Optional[str] = None


class EducationItem(BaseModel):
    school: Optional[str] = None
    degree_name: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    school_linkedin_profile_url: Optional[str] = None


class ProjectItem(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ActivityItem(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    activity_status: Optional[str] = None


class StructuredLinkedInProfile(BaseModel):
    headline: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None
    profile_pic_url: Optional[str] = None
    follower_count: Optional[int] = None
    connections: Optional[int] = None
    summary: Optional[str] = None
    experiences: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    activities: List[ActivityItem] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)


class LinkedInEnrichRequest(BaseModel):
    force: bool = Field(
        default=False,
        description="Set to true to re-run live enrichment even if the profile was already enriched."
    )
    profile_url: Optional[str] = Field(
        default=None,
        description="Optional verified LinkedIn /in/ profile URL override."
    )


class LinkedInImportRequest(BaseModel):
    file_path: Optional[str] = Field(
        default=None,
        description="Optional relative/filename path of a cached *_enrichlayer_response.json file to import."
    )
    target_id: Optional[str] = Field(
        default=None,
        description="Optional explicit target person ID to bind the cached profile payload to."
    )


class LinkedInEnrichResponse(BaseModel):
    success: bool
    enrichment_status: str
    credits_cost: int = 0
    message: str
    profile_enriched_at: Optional[datetime] = None
    structured_profile: StructuredLinkedInProfile
    target_id: str

    model_config = ConfigDict(from_attributes=True)

