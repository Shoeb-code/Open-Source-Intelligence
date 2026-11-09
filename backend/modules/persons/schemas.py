from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class SocialProfileCreate(BaseModel):
    platform: str = Field(..., description="e.g. linkedin, youtube, instagram, twitter, web")
    profile_url: str = Field(..., description="Public profile URL")
    username: Optional[str] = Field(None, description="Optional profile handle/username")


class SocialProfileResponse(BaseModel):
    id: str
    person_id: str
    platform: str
    username: Optional[str]
    profile_url: str
    verification_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PersonCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Full name of the individual")
    profession: Optional[str] = Field(None, max_length=255, description="Profession or title, e.g. 'Software Engineer'")
    biography: Optional[str] = Field(None, description="Short background or known career bio")
    
    # Direct profile URLs as defined in TDD Section 4.1
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    instagram_url: Optional[str] = Field(None, description="Instagram profile URL")
    youtube_url: Optional[str] = Field(None, description="YouTube channel or profile URL")
    
    additional_profiles: Optional[List[SocialProfileCreate]] = Field(default_factory=list)


class PersonUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Full name of the individual")
    profession: Optional[str] = Field(None, max_length=255, description="Profession or title")
    biography: Optional[str] = Field(None, description="Short background or known career bio")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    instagram_url: Optional[str] = Field(None, description="Instagram profile URL")
    youtube_url: Optional[str] = Field(None, description="YouTube channel or profile URL")
    additional_profiles: Optional[List[SocialProfileCreate]] = None


class PersonResponse(BaseModel):
    id: str
    name: str
    profession: Optional[str]
    biography: Optional[str]
    social_profiles: List[SocialProfileResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IdentityContext(BaseModel):
    """Normalized identity reference used by Discovery and Verification engines."""
    person_id: str
    name: str
    profession: Optional[str] = None
    organizations: List[str] = []
    known_usernames: List[str] = []
    profile_urls: Dict[str, str] = {}

