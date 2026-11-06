#!/usr/bin/env bash
# Runs the task verifier against simulated agents, without Docker.
# Each agent gets a fresh copy of the environment, then tests/test.sh scores it.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export TASK_DIR="$ROOT/tasks/ticket-dedupe-reopen"
AGENTS="$ROOT/validation/agents"
VENV="$ROOT/.venv"

# Behind a corporate mirror? uv honours UV_INDEX_URL / UV_INSECURE_HOST.
if [[ ! -x "$VENV/bin/python" ]]; then
  uv venv --quiet "$VENV"
  uv pip install --quiet --python "$VENV/bin/python" pytest==8.3.3
fi
export PATH="$VENV/bin:$PATH"

# agent script : expected reward
CASES=(
  "noop:0"
  "partial_notes_only:0"
  "hack_skip_visible_test:0"
  "hack_delete_visible_tests:0"
  "hack_conftest_override:0"
  "oracle:1"
)

failures=0
printf "%-28s %-8s %-8s %-6s %s\n" "AGENT" "EXPECTED" "REWARD" "RESULT" "CAUGHT BY"
for case in "${CASES[@]}"; do
  agent="${case%%:*}"
  expected="${case##*:}"
  work="$(mktemp -d)"
  cp -R "$TASK_DIR/environment/app" "$work/app"

  APP_DIR="$work/app" bash "$AGENTS/$agent.sh" > "$work/agent.log" 2>&1
  APP_DIR="$work/app" TESTS_DIR="$TASK_DIR/tests" LOGS_DIR="$work/logs" \
    bash "$TASK_DIR/tests/test.sh" > "$work/verifier.log" 2>&1 || true

  reward="$(cat "$work/logs/verifier/reward.txt")"
  verdict="ok"
  if [[ "$reward" != "$expected" ]]; then
    verdict="MISMATCH (log: $work/verifier.log)"
    failures=$((failures + 1))
  fi
  caught_by="$(grep -E '^FAILED' "$work/verifier.log" | sed -E 's/^FAILED [^:]*::([a-z_]+).*/\1/' | paste -sd ',' - || true)"
  printf "%-28s %-8s %-8s %-6s %s\n" "$agent" "$expected" "$reward" "$verdict" "${caught_by:--}"
  [[ "$verdict" == "ok" ]] && rm -rf "$work"
done

exit "$failures"
