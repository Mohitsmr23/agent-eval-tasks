#!/usr/bin/env bash
# Harbor verifier. Writes 1 to reward.txt only if every hidden check passes.
# Paths are overridable so validate.sh can run the same script without Docker.
APP_DIR="${APP_DIR:-/app}"
TESTS_DIR="${TESTS_DIR:-/tests}"
LOGS_DIR="${LOGS_DIR:-/logs}"

mkdir -p "$LOGS_DIR/verifier"
cd "$APP_DIR" || exit 1

# --noconftest and --rootdir stop a conftest.py planted in /app from
# patching the hidden tests.
if APP_DIR="$APP_DIR" PYTHONPATH="$APP_DIR" python -m pytest \
    "$TESTS_DIR/test_outputs.py" \
    --rootdir "$TESTS_DIR" --noconftest -p no:cacheprovider -rA; then
  echo 1 > "$LOGS_DIR/verifier/reward.txt"
else
  echo 0 > "$LOGS_DIR/verifier/reward.txt"
fi
