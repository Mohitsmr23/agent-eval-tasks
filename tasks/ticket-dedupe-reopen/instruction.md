# Duplicate reports wipe ticket history and reopen tickets to the wrong person

`/app` contains **ticketdesk**, a small Python service that turns problem
reports from upstream systems into tickets. A report whose `external_ref`
matches an existing ticket is a *duplicate* and is merged into that ticket
instead of creating a new one (`TicketService.ingest`). Agents can also add
notes to a ticket directly (`TicketService.bulk_edit`).

Operations have reported three problems:

1. After a duplicate report arrives, the ticket's earlier notes are gone.
2. When a duplicate arrives for a **closed** ticket, the ticket comes back as
   `NEW`, but it is still assigned to the agent who closed it, and it is
   immediately overdue.
3. Tickets that an agent is actively working on get bounced back to `NEW`
   whenever a duplicate report arrives.

## Required behaviour

- **Notes are never lost.** A duplicate report or a bulk edit results in the
  ticket's existing notes followed by the incoming notes, in order.
- **Duplicate for a CLOSED ticket:** reopen it. Status becomes `NEW`, queue
  becomes `TRIAGE_QUEUE`, the assignee is cleared (`None`), and `due_at` is
  reset to *now + `SLA`* using the service's injected clock.
- **Duplicate for an open ticket** (`NEW` or `IN_PROGRESS`): status, queue,
  assignee and `due_at` stay exactly as they are. Only the notes change.
- **Bulk edit** never changes status, queue, assignee or `due_at`, even on a
  closed ticket. Only the notes change.
- A duplicate report never creates a second ticket.

## Constraints

- Keep the public API of `ticketdesk.models`, `ticketdesk.store` and
  `ticketdesk.service` unchanged (class names, method names and signatures).
- The existing suite in `/app/tests` must pass when you are done. Do not delete
  tests. If an existing test asserts behaviour that contradicts the
  requirements above, correct the test.

Run the suite with `cd /app && python -m pytest`.
