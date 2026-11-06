#!/usr/bin/env bash
# Runs the reference solution. Must score 1, or the task is unsolvable.
set -euo pipefail
bash "$TASK_DIR/solution/solve.sh"
