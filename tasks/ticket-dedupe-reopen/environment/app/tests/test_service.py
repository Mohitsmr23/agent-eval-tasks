from datetime import datetime, timezone

from ticketdesk.models import TRIAGE_QUEUE, Note, Report, Status
from ticketdesk.service import TicketService
from ticketdesk.store import InMemoryTicketStore

NOW = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)


def make_service():
    store = InMemoryTicketStore()
    return store, TicketService(store, clock=lambda: NOW)


def test_new_report_creates_ticket_in_triage():
    store, service = make_service()
    ticket = service.ingest(Report("EXT-1", "portal", (Note("src", "printer on fire"),)))
    assert ticket.status is Status.NEW
    assert ticket.queue == TRIAGE_QUEUE
    assert ticket.assignee is None
    assert len(store.all()) == 1


def test_duplicate_report_does_not_create_second_ticket():
    store, service = make_service()
    service.ingest(Report("EXT-1", "portal"))
    service.ingest(Report("EXT-1", "portal"))
    assert len(store.all()) == 1


def test_duplicate_report_notes():
    _, service = make_service()
    service.ingest(Report("EXT-1", "portal", (Note("src", "first report"),)))
    ticket = service.ingest(Report("EXT-1", "portal", (Note("src", "second report"),)))
    assert len(ticket.notes) == 1
    assert ticket.notes[0].text == "second report"


def test_bulk_edit_keeps_status():
    _, service = make_service()
    ticket = service.ingest(Report("EXT-1", "portal"))
    edited = service.bulk_edit(ticket.ticket_id, [Note("alice", "looking into it")])
    assert edited.status is ticket.status
