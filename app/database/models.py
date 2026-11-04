import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database.connection import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Person(Base):
    __tablename__ = "persons"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    name = Column(String(255), nullable=False, index=True)
    profession = Column(String(255), nullable=True)
    biography = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    social_profiles = relationship("SocialProfile", back_populates="person", cascade="all, delete-orphan")
    research_jobs = relationship("ResearchJob", back_populates="person", cascade="all, delete-orphan")
    appearances = relationship("Appearance", back_populates="person", cascade="all, delete-orphan")


class SocialProfile(Base):
    __tablename__ = "social_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    person_id = Column(String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # linkedin, instagram, youtube, twitter, web
    username = Column(String(255), nullable=True)
    profile_url = Column(String(1024), nullable=False)
    verification_status = Column(String(50), default="PENDING")  # PENDING, VERIFIED, UNVERIFIED
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    person = relationship("Person", back_populates="social_profiles")


class ResearchJob(Base):
    __tablename__ = "research_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    person_id = Column(String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="PENDING", index=True)  # PENDING, RUNNING, COMPLETED, FAILED, PARTIALLY_COMPLETED
    progress = Column(Integer, default=0)  # 0 to 100%
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    person = relationship("Person", back_populates="research_jobs")
    logs = relationship("CollectionLog", back_populates="job", cascade="all, delete-orphan")


class Appearance(Base):
    __tablename__ = "appearances"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    person_id = Column(String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    appearance_type = Column(String(50), nullable=False, index=True)  # PODCAST, INTERVIEW, NEWS_ARTICLE, CONFERENCE, WEBINAR, OTHER
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    publisher = Column(String(255), nullable=True, index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    identity_status = Column(String(50), default="NEEDS_REVIEW", index=True)  # VERIFIED, LIKELY_MATCH, NEEDS_REVIEW, REJECTED
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    person = relationship("Person", back_populates="appearances")
    sources = relationship("Source", back_populates="appearance", cascade="all, delete-orphan")
    analysis = relationship("AppearanceAnalysis", back_populates="appearance", uselist=False, cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    appearance_id = Column(String(36), ForeignKey("appearances.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url = Column(String(1024), nullable=False)
    canonical_url = Column(String(1024), nullable=True, index=True)
    source_type = Column(String(50), nullable=False)  # YOUTUBE, NEWS, PODCAST, EVENT, WEBPAGE
    extracted_content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    collected_at = Column(DateTime, default=utc_now)
    extraction_status = Column(String(50), default="PENDING")  # SUCCESS, TRANSCRIPT_UNAVAILABLE, RESTRICTED, FAILED

    # Relationships
    appearance = relationship("Appearance", back_populates="sources")


class AppearanceAnalysis(Base):
    __tablename__ = "appearance_analysis"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    appearance_id = Column(String(36), ForeignKey("appearances.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=True)
    topics = Column(JSON, nullable=True)  # List of string topics
    key_points = Column(JSON, nullable=True)  # List of key takeaways
    person_role = Column(String(100), nullable=True)  # SPEAKER, GUEST, INTERVIEWEE, HOST, MENTIONED
    evidence = Column(JSON, nullable=True)  # List of quotes or citations
    model_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    appearance = relationship("Appearance", back_populates="analysis")


class CollectionLog(Base):
    __tablename__ = "collection_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    job_id = Column(String(36), ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # SUCCESS, WARNING, ERROR, SKIPPED
    error_message = Column(Text, nullable=True)
    execution_time = Column(Float, nullable=True)  # In seconds
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    job = relationship("ResearchJob", back_populates="logs")

