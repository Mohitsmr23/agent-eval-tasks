#!/usr/bin/env bash
# Partial fix: stops the notes wipe but ignores reopen and assignment rules.
set -euo pipefail
cd "$APP_DIR"
python - <<'PY'
from pathlib import Path

service = Path("ticketdesk/service.py")
service.write_text(service.read_text().replace(
    "history = incoming if incoming else existing.notes",
    "history = [*existing.notes, *incoming]",
))
test = Path("tests/test_service.py")
test.write_text(test.read_text().replace(
    '    assert len(ticket.notes) == 1\n    assert ticket.notes[0].text == "second report"\n',
    '    assert [n.text for n in ticket.notes] == ["first report", "second report"]\n',
))
PY
