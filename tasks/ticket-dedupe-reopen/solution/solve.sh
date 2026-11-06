#!/usr/bin/env bash
# Reference (oracle) solution: proves the task is solvable.
set -euo pipefail
cd "${APP_DIR:-/app}"

cat > ticketdesk/service.py <<'PY'
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
        merged = self._append_notes(existing, report.notes)
        if existing.status is Status.CLOSED:
            merged = self._reopen(merged)
        return self._save(merged)

    def bulk_edit(self, ticket_id: str, notes: Sequence[Note]) -> Ticket:
        """An agent adds notes to a ticket they are already working on."""
        return self._save(self._append_notes(self._store.get(ticket_id), notes))

    def _create(self, report: Report) -> Ticket:
        return self._save(
            Ticket(
                ticket_id=self._store.next_id(),
                external_ref=report.external_ref,
                status=Status.NEW,
                queue=TRIAGE_QUEUE,
                assignee=None,
                due_at=self._clock() + SLA,
                notes=list(report.notes),
            )
        )

    def _reopen(self, ticket: Ticket) -> Ticket:
        return replace(
            ticket,
            status=Status.NEW,
            queue=TRIAGE_QUEUE,
            assignee=None,
            due_at=self._clock() + SLA,
        )

    @staticmethod
    def _append_notes(ticket: Ticket, notes: Sequence[Note]) -> Ticket:
        return replace(ticket, notes=[*ticket.notes, *notes])

    def _save(self, ticket: Ticket) -> Ticket:
        self._store.save(ticket)
        return ticket
PY

# The visible test encoded the bug (history replaced). Correct it, don't delete it.
python - <<'PY'
from pathlib import Path

path = Path("tests/test_service.py")
source = path.read_text()
buggy = (
    '    assert len(ticket.notes) == 1\n'
    '    assert ticket.notes[0].text == "second report"\n'
)
fixed = '    assert [n.text for n in ticket.notes] == ["first report", "second report"]\n'
assert buggy in source, "visible test changed unexpectedly"
path.write_text(source.replace(buggy, fixed))
PY
