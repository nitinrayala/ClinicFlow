from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def empty_note() -> dict:
    return {"symptoms": [], "history": [], "findings": [], "plan": []}


class Base(DeclarativeBase):
    pass


class Clinic(Base):
    __tablename__ = "clinics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Kolkata")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("id", "clinic_id"), CheckConstraint("role IN ('doctor', 'staff')"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RateLimit(Base):
    __tablename__ = "rate_limits"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (UniqueConstraint("id", "clinic_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    date_of_birth: Mapped[date]


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (UniqueConstraint("id", "clinic_id"), ForeignKeyConstraint(["patient_id", "clinic_id"], ["patients.id", "patients.clinic_id"]))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    patient_id: Mapped[str] = mapped_column(String(36))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(250))


class Encounter(Base):
    __tablename__ = "encounters"
    __table_args__ = (
        UniqueConstraint("id", "clinic_id"),
        ForeignKeyConstraint(["appointment_id", "clinic_id"], ["appointments.id", "appointments.clinic_id"]),
        CheckConstraint("status IN ('draft', 'approved')"),
        CheckConstraint("draft_revision >= 0 AND transcript_revision >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    appointment_id: Mapped[str] = mapped_column(String(36), unique=True)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    transcript: Mapped[str] = mapped_column(Text, default="")
    transcript_revision: Mapped[int] = mapped_column(default=0)
    draft_revision: Mapped[int] = mapped_column(default=0)
    note: Mapped[dict] = mapped_column(JSON, default=empty_note)
    proposed_tasks: Mapped[list] = mapped_column(JSON, default=list)
    generation_status: Mapped[str] = mapped_column(String(16), default="idle")
    current_generation_id: Mapped[str | None] = mapped_column(String(36))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_draft_revision: Mapped[int | None]
    approved_transcript_revision: Mapped[int | None]


class TranscriptVersion(Base):
    __tablename__ = "transcript_versions"
    __table_args__ = (UniqueConstraint("encounter_id", "revision"), ForeignKeyConstraint(["encounter_id", "clinic_id"], ["encounters.id", "encounters.clinic_id"]))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(String(36))
    encounter_id: Mapped[str] = mapped_column(String(36))
    revision: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NoteVersion(Base):
    __tablename__ = "note_versions"
    __table_args__ = (ForeignKeyConstraint(["encounter_id", "clinic_id"], ["encounters.id", "encounters.clinic_id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(String(36))
    encounter_id: Mapped[str] = mapped_column(String(36), index=True)
    draft_revision: Mapped[int]
    transcript_revision: Mapped[int]
    note: Mapped[dict] = mapped_column(JSON)
    proposed_tasks: Mapped[list] = mapped_column(JSON)
    kind: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (ForeignKeyConstraint(["encounter_id", "clinic_id"], ["encounters.id", "encounters.clinic_id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(String(36))
    encounter_id: Mapped[str] = mapped_column(String(36), index=True)
    draft_revision: Mapped[int]
    transcript_revision: Mapped[int]
    note: Mapped[dict] = mapped_column(JSON, default=empty_note)
    proposed_tasks: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="running")
    prompt_version: Mapped[str] = mapped_column(String(20), default="1")
    latency_ms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("encounter_id", "proposal_id"),
        ForeignKeyConstraint(["encounter_id", "clinic_id"], ["encounters.id", "encounters.clinic_id"]),
        ForeignKeyConstraint(["assignee_id", "clinic_id"], ["users.id", "users.clinic_id"]),
        CheckConstraint("status IN ('open', 'in_progress', 'done')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(String(36), index=True)
    encounter_id: Mapped[str] = mapped_column(String(36), index=True)
    proposal_id: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(1000))
    due_date: Mapped[date | None]
    assignee_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (ForeignKeyConstraint(["encounter_id", "clinic_id"], ["encounters.id", "encounters.clinic_id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    clinic_id: Mapped[str] = mapped_column(String(36))
    encounter_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
