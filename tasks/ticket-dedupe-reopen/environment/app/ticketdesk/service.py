"""Ticket ingestion: creates new tickets and merges duplicate reports."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime, timedelta

from ticketdesk.models import TRIAGE_QUEUE, Note, Report, Status, Ticket
from ticketdesk.store import InMemoryTicketStore

SLA = timedelta(hours=24)


class TicketService:
    def __init__(self, store: InMemoryTicketStore, clock: Callable[[], datetime]) -> None:
        self._store = store
        self._clock = clock

    def ingest(self, report: Report) -> Ticket:
        """Create a ticket, or merge the report into the ticket with the same external_ref."""
        existing = self._store.find_by_ref(report.external_ref)
        if existing is None:
            return self._create(report)
        return self._update(existing, list(report.notes), status=Status.NEW)

    def bulk_edit(self, ticket_id: str, notes: Sequence[Note]) -> Ticket:
        """An agent adds notes to a ticket they are already working on."""
        existing = self._store.get(ticket_id)
        return self._update(existing, list(notes), status=existing.status)

    def _create(self, report: Report) -> Ticket:
        ticket = Ticket(
            ticket_id=self._store.next_id(),
            external_ref=report.external_ref,
            status=Status.NEW,
            queue=TRIAGE_QUEUE,
            assignee=None,
            due_at=self._clock() + SLA,
            notes=list(report.notes),
        )
        self._store.save(ticket)
        return ticket

    def _update(self, existing: Ticket, incoming: list[Note], status: Status) -> Ticket:
        updated = replace(existing, status=status, notes=self._merge_notes(existing, incoming))
        self._store.save(updated)
        return updated

    @staticmethod
    def _merge_notes(existing: Ticket, incoming: list[Note]) -> list[Note]:
        """Append incoming notes to the ticket's history."""
        history = incoming if incoming else existing.notes
        return list(history)
