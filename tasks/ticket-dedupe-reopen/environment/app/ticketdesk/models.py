"""Domain models for the ticketdesk service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

TRIAGE_QUEUE = "TRIAGE"


class Status(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Note:
    author: str
    text: str


@dataclass(frozen=True)
class Report:
    """An incoming problem report from an upstream source system."""

    external_ref: str
    source: str
    notes: tuple[Note, ...] = ()


@dataclass
class Ticket:
    ticket_id: str
    external_ref: str
    status: Status
    queue: str
    assignee: str | None
    due_at: datetime
    notes: list[Note] = field(default_factory=list)
