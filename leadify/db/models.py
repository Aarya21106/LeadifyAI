import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, JSON, Enum as SQLEnum, func, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from leadify.common.enums import LeadStatus, LeadEventType, FollowUpDraftStatus

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String)
    company: Mapped[Optional[str]] = mapped_column(String)
    first_email_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[LeadStatus] = mapped_column(SQLEnum(LeadStatus), default=LeadStatus.ACTIVE, index=True)

    events: Mapped[List["LeadEvent"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    scores: Mapped[List["LeadScore"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    drafts: Mapped[List["FollowUpDraft"]] = relationship(back_populates="lead", cascade="all, delete-orphan")

class LeadEvent(Base):
    __tablename__ = "lead_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[LeadEventType] = mapped_column(SQLEnum(LeadEventType), index=True)
    raw_data: Mapped[dict] = mapped_column(JSON)
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="events")

class LeadScore(Base):
    __tablename__ = "lead_scores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    delta: Mapped[int] = mapped_column(Integer)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    scored_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="scores")

class FollowUpDraft(Base, TimestampMixin):
    __tablename__ = "follow_up_drafts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    score_at_draft: Mapped[int] = mapped_column(Integer)
    signal_summary: Mapped[Optional[str]] = mapped_column(Text)
    writer_model: Mapped[str] = mapped_column(String)
    reviewer_feedback: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[FollowUpDraftStatus] = mapped_column(SQLEnum(FollowUpDraftStatus), default=FollowUpDraftStatus.PENDING_REVIEW, index=True)

    lead: Mapped["Lead"] = relationship(back_populates="drafts")

class GmailCredentials(Base):
    __tablename__ = "gmail_credentials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    access_token: Mapped[str] = mapped_column(Text)  # Should be encrypted in practice
    refresh_token: Mapped[str] = mapped_column(Text) # Should be encrypted in practice
    token_expiry: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
