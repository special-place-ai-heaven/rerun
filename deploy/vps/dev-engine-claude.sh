#!/bin/sh
# A real model for the development engine through the owner's Claude subscription, with a one-run proof.
# Run from the clone, with the dev engine and the runner up (deploy/vps/FACTORY-M2.md, steps 3 and 5):
#   sudo sh deploy/vps/dev-engine-claude.sh           connect (asks for the token once), then the proof run
#   sudo sh deploy/vps/dev-engine-claude.sh probe     the proof run only
#   sudo sh deploy/vps/dev-engine-claude.sh check     is the connection there
#   sudo sh deploy/vps/dev-engine-claude.sh remove    remove the connection
# The token comes from `claude setup-token`, run by the owner where he is signed in to his Claude
# subscription. It is typed at a hidden prompt and piped once into the runner container, which hands it
# to the development engine; that engine keeps it in its own store. It is written to no file here, put on
# no command line and never printed. The live engine and its key are not involved.
set -eu
cd "$(dirname "$0")/../.."
realmodel() { docker compose -f deploy/vps/factory-runner.yml exec -T factory-runner python3 /app/realmodel.py "$@"; }

MODE=${1:-all}
case "$MODE" in
    probe|check|remove) realmodel "$MODE"; exit $? ;;
    all) ;;
    *) echo "usage: sudo sh deploy/vps/dev-engine-claude.sh [probe|check|remove]"; exit 2 ;;
esac

STATE=$(realmodel check) || { echo "No answer from the runner. Is it up? sudo docker compose -f deploy/vps/factory-runner.yml up -d"; exit 1; }
printf '%s\n' "$STATE"
case "$STATE" in
    *connection=absent*)
        trap 'stty echo 2>/dev/null || true' EXIT INT TERM
        printf 'Token from "claude setup-token" (hidden, Enter to cancel): '
        stty -echo 2>/dev/null || true
        read -r TOKEN || TOKEN=''
        stty echo 2>/dev/null || true
        echo
        [ -n "$TOKEN" ] || { echo "Cancelled: nothing sent."; exit 0; }
        printf '%s\n' "$TOKEN" | realmodel connect
        TOKEN=
        ;;
esac
realmodel probe
