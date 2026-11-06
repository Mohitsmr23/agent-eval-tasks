"""Hidden verifier for ticket-dedupe-reopen.

Fail-to-pass: behaviour the original code gets wrong.
Pass-to-pass: behaviour that must survive the fix, including the visible suite.
Values (refs, names, times) deliberately differ from the visible tests so a
solution hard-coded against those tests does not pass.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from ticketdesk.models import TRIAGE_QUEUE, Note, Report, Status
from ticketdesk.service import SLA, TicketService
from ticketdesk.store import InMemoryTicketStore

APP_DIR = os.environ.get("APP_DIR", "/app")
MIN_VISIBLE_TESTS = 4
START = datetime(2031, 6, 15, 14, 30, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


@pytest.fixture
def env():
    store = InMemoryTicketStore()
    clock = FakeClock(START)
    return store, clock, TicketService(store, clock=clock)


def _note(author: str, text: str) -> Note:
    return Note(author, text)


def _assign(store, ticket, status: Status, assignee: str):
    worked = replace(ticket, status=status, assignee=assignee, queue="NETWORK")
    store.save(worked)
    return worked


# ---------------------------------------------------------------- fail-to-pass


def test_duplicate_appends_notes_in_order(env):
    _, _, service = env
    service.ingest(Report("ZX-77", "monitor", (_note("mon", "a1"), _note("mon", "a2"))))
    ticket = service.ingest(Report("ZX-77", "monitor", (_note("mon", "b1"),)))
    assert [n.text for n in ticket.notes] == ["a1", "a2", "b1"]


def test_bulk_edit_appends_notes(env):
    _, _, service = env
    ticket = service.ingest(Report("ZX-78", "monitor", (_note("mon", "origin"),)))
    edited = service.bulk_edit(ticket.ticket_id, [_note("bo", "x"), _note("bo", "y")])
    assert [n.text for n in edited.notes] == ["origin", "x", "y"]


def test_duplicate_for_closed_ticket_reopens_to_triage(env):
    store, clock, service = env
    ticket = service.ingest(Report("ZX-79", "monitor", (_note("mon", "first"),)))
    _assign(store, ticket, Status.CLOSED, "bo")
    clock.advance(timedelta(days=9, minutes=17))

    reopened = service.ingest(Report("ZX-79", "monitor", (_note("mon", "again"),)))

    assert reopened.status is Status.NEW
    assert reopened.queue == TRIAGE_QUEUE
    assert reopened.assignee is None
    assert reopened.due_at == clock.now + SLA
    assert [n.text for n in reopened.notes] == ["first", "again"]


def test_duplicate_for_in_progress_ticket_keeps_assignment(env):
    store, clock, service = env
    ticket = service.ingest(Report("ZX-80", "monitor"))
    worked = _assign(store, ticket, Status.IN_PROGRESS, "carmen")
    clock.advance(timedelta(hours=5))

    after = service.ingest(Report("ZX-80", "monitor", (_note("mon", "still broken"),)))

    assert after.status is Status.IN_PROGRESS
    assert after.assignee == "carmen"
    assert after.queue == "NETWORK"
    assert after.due_at == worked.due_at


def test_result_is_persisted(env):
    store, _, service = env
    ticket = service.ingest(Report("ZX-81", "monitor", (_note("mon", "p"),)))
    service.ingest(Report("ZX-81", "monitor", (_note("mon", "q"),)))
    assert [n.text for n in store.get(ticket.ticket_id).notes] == ["p", "q"]


# ---------------------------------------------------------------- pass-to-pass


def test_duplicate_without_notes_keeps_history(env):
    _, _, service = env
    service.ingest(Report("ZX-82", "monitor", (_note("mon", "keep me"),)))
    ticket = service.ingest(Report("ZX-82", "monitor"))
    assert [n.text for n in ticket.notes] == ["keep me"]


def test_duplicate_for_new_ticket_stays_new(env):
    _, clock, service = env
    created = service.ingest(Report("ZX-83", "monitor"))
    clock.advance(timedelta(hours=3))
    after = service.ingest(Report("ZX-83", "monitor"))
    assert after.status is Status.NEW
    assert after.due_at == created.due_at


def test_bulk_edit_on_closed_ticket_does_not_reopen(env):
    store, clock, service = env
    ticket = service.ingest(Report("ZX-84", "monitor"))
    closed = _assign(store, ticket, Status.CLOSED, "dev")
    clock.advance(timedelta(days=2))

    edited = service.bulk_edit(ticket.ticket_id, [_note("dev", "post-mortem")])

    assert edited.status is Status.CLOSED
    assert edited.assignee == "dev"
    assert edited.queue == "NETWORK"
    assert edited.due_at == closed.due_at


def test_duplicate_never_creates_second_ticket(env):
    store, _, service = env
    for _ in range(3):
        service.ingest(Report("ZX-85", "monitor"))
    assert len(store.all()) == 1


def test_visible_suite_passes_and_was_not_gutted():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    passed = re.search(r"(\d+) passed", result.stdout)
    assert passed and int(passed.group(1)) >= MIN_VISIBLE_TESTS, result.stdout
