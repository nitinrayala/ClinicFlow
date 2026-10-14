from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    segment_id: str = Field(pattern=r"^s[1-9][0-9]*$", max_length=12)
    quote: str = Field(min_length=1, max_length=4000)
    transcript_revision: int = Field(ge=0)
    source_text: str | None = None
    generation_id: str | None = None


class Fact(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=2000)
    origin: Literal["manual", "ai", "doctor-edited"] = "manual"
    evidence: list[Evidence] = Field(default_factory=list, max_length=15)
    evidence_reviewed: bool = False

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Fact text cannot be blank")
        return value.strip()


class Note(StrictModel):
    symptoms: list[Fact] = Field(default_factory=list, max_length=40)
    history: list[Fact] = Field(default_factory=list, max_length=40)
    findings: list[Fact] = Field(default_factory=list, max_length=40)
    plan: list[Fact] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [fact.id for facts in (self.symptoms, self.history, self.findings, self.plan) for fact in facts]
        if len(ids) != len(set(ids)):
            raise ValueError("Fact IDs must be unique")
        return self


class ProposedTask(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    due_date: date | None = None
    assignee_id: str | None = Field(default=None, max_length=36)
    evidence: list[Evidence] = Field(default_factory=list, max_length=15)
    timing_text: str | None = Field(default=None, max_length=250)

    @field_validator("description")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Task description cannot be blank")
        return value.strip()


class RevisionRequest(StrictModel):
    draft_revision: int = Field(ge=0)
    transcript_revision: int = Field(ge=0)


class SaveEncounter(RevisionRequest):
    transcript: str = Field(max_length=20000)
    note: Note
    proposed_tasks: list[ProposedTask] = Field(max_length=30)

    @model_validator(mode="after")
    def unique_tasks(self):
        ids = [task.id for task in self.proposed_tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Proposed task IDs must be unique")
        return self


class LoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class TaskUpdate(StrictModel):
    status: Literal["open", "in_progress", "done"] | None = None
    assignee_id: str | None = Field(default=None, max_length=36)


# Separate provider schema has only extraction fields; identity and provenance are server-owned.
class ExtractedEvidence(StrictModel):
    segment_id: str
    quote: str


class ExtractedFact(StrictModel):
    text: str
    evidence: list[ExtractedEvidence]


class ExtractedNote(StrictModel):
    symptoms: list[ExtractedFact]
    history: list[ExtractedFact]
    findings: list[ExtractedFact]
    plan: list[ExtractedFact]


class ExtractedTask(StrictModel):
    description: str
    timing_text: str | None
    evidence: list[ExtractedEvidence]


class Extraction(StrictModel):
    note: ExtractedNote
    proposed_tasks: list[ExtractedTask]
