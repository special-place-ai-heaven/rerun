#!/bin/sh
# Prints one PASS/FAIL row per factory done-test R1-R4 and R6, with the evidence (names and ids only, never a key).
# It runs inside the runner container, which already holds the dev engine key and the ledger volume.
#   sudo sh deploy/vps/factory-status.sh
# Needs the runner up: sudo docker compose -f deploy/vps/factory-runner.yml up -d
set -eu
cd "$(dirname "$0")/../.."
exec docker compose -f deploy/vps/factory-runner.yml exec -T factory-runner python3 -I /app/status_report.py "$@"
