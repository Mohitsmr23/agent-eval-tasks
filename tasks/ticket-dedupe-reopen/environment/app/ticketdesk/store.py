"""A minimal in-memory ticket repository."""

from __future__ import annotations

from itertools import count

from ticketdesk.models import Ticket


class InMemoryTicketStore:
    def __init__(self) -> None:
        self._tickets: dict[str, Ticket] = {}
        self._ids = count(1)

    def next_id(self) -> str:
        return f"T-{next(self._ids):04d}"

    def save(self, ticket: Ticket) -> None:
        self._tickets[ticket.ticket_id] = ticket

    def get(self, ticket_id: str) -> Ticket:
        return self._tickets[ticket_id]

    def find_by_ref(self, external_ref: str) -> Ticket | None:
        return next(
            (t for t in self._tickets.values() if t.external_ref == external_ref),
            None,
        )

    def all(self) -> list[Ticket]:
        return list(self._tickets.values())
