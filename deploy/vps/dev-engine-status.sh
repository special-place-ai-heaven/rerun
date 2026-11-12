#!/bin/sh
# Read-and-probe check of the development engine (deploy/vps/dev-engine.yml) beside the live one.
# Run from the clone, after the development engine is up:
#   sudo sh deploy/vps/dev-engine-status.sh
# One labelled line per check. No secret and no environment value is printed: the live engine key is
# read into a variable, used in one request, and unset.
set -eu
cd "$(dirname "$0")/../.."
DEV=${DEV_ENGINE_CONTAINER:-rerun-dev-engine-dev-1}

say() { printf '%s\n' "$*"; }
dev() { docker exec "$DEV" "$@" </dev/null; }
devi() { docker exec -i "$DEV" "$@"; }
live_id() { docker compose ps -q engine | head -n 1; }
live_state() { docker inspect "$1" -f 'started={{.State.StartedAt}} restarts={{.RestartCount}} oomkilled={{.State.OOMKilled}}'; }

LIVE=$(live_id)
[ -n "$LIVE" ] || { say "P0 FAIL no live engine container found"; exit 1; }
BASE=$(live_state "$LIVE")

say "P0 live-engine $BASE"
say "P0 host-memory-free $(free -m | awk '/^Mem:/ {print $7 " MB available"}')"
say "P0 host-disk-free $(df -h / | awk 'NR==2 {print $4 " free"}')"

# P1: how the container is configured.
say "P1 mounts $(docker inspect "$DEV" -f '{{range .Mounts}}[{{.Type}} {{.Name}} -> {{.Destination}}] {{end}}')"
say "P1 privileged=$(docker inspect "$DEV" -f '{{.HostConfig.Privileged}}') capadd=$(docker inspect "$DEV" -f '{{.HostConfig.CapAdd}}') pidmode='$(docker inspect "$DEV" -f '{{.HostConfig.PidMode}}')' devices=$(docker inspect "$DEV" -f '{{len .HostConfig.Devices}}')"
say "P1 network-mode=$(docker inspect "$DEV" -f '{{.HostConfig.NetworkMode}}') port-bindings=$(docker inspect "$DEV" -f '{{json .HostConfig.PortBindings}}')"
ENVNAMES=$(docker inspect "$DEV" -f '{{range .Config.Env}}{{println .}}{{end}}' | sed 's/=.*//' | sort | tr '\n' ' ')
say "P1 env-names $ENVNAMES"
for V in RERUN_API_KEY RERUN_HUB_BASE_URL RERUN_PAIR_TOKEN RERUN_HUB_URL; do
    case " $ENVNAMES" in
        *" $V "*) say "P1 forbidden-variable $V PRESENT" ;;
        *) say "P1 forbidden-variable $V absent" ;;
    esac
done
say "P1 memory-limit=$(docker inspect "$DEV" -f '{{.HostConfig.Memory}}') nano-cpus=$(docker inspect "$DEV" -f '{{.HostConfig.NanoCpus}}') shm=$(docker inspect "$DEV" -f '{{.HostConfig.ShmSize}}')"
say "P1 log-config $(docker inspect "$DEV" -f '{{.HostConfig.LogConfig.Type}} {{json .HostConfig.LogConfig.Config}}')"

# P2: nothing of the live setup is reachable from inside.
if dev test -e /data/hub.json; then say "P2 hub.json PRESENT"; else say "P2 hub.json absent"; fi
CODE=$(dev curl -s -o /dev/null -m 5 -w '%{http_code}' http://app:3000 2>/dev/null || true)
case "$CODE" in
    ''|000) say "P2 live-app-by-name unreachable (expected)" ;;
    *) say "P2 live-app-by-name REACHABLE http=$CODE" ;;
esac

# P3: health.
say "P3 health http=$(dev curl -s -o /dev/null -m 5 -w '%{http_code}' http://localhost:3000/health || true)"

# P4: create a coworker, create a webhook trigger, fire it, read the run row.
AG=$(dev curl -s -m 20 -X POST http://localhost:3000/agents -H 'content-type: application/json' \
    -d '{"config":{"name":"dev-probe"}}' | devi jq -r '.id // empty' || true)
if [ -n "$AG" ]; then
    TR=$(dev curl -s -m 20 -X POST "http://localhost:3000/agents/$AG/triggers" -H 'content-type: application/json' \
        -d '{"name":"probe","body":"Say hello."}')
    SLUG=$(printf '%s' "$TR" | devi jq -r '.slug // empty' || true)
    TOK=$(printf '%s' "$TR" | devi jq -r '.token // empty' || true)
    FIRE=$(dev curl -s -m 30 -X POST "http://localhost:3000/agents/$AG/triggers/$SLUG/fire" -H 'content-type: application/json' \
        -d "{\"token\":\"$TOK\",\"method\":\"POST\"}")
    TOK=
    RUN=$(printf '%s' "$FIRE" | devi jq -r '.runId // empty' || true)
    SES=$(printf '%s' "$FIRE" | devi jq -r '.sessionId // empty' || true)
    sleep 3
    ST=$(dev curl -s -m 10 "http://localhost:3000/agents/$AG/runs/$RUN" | devi jq -r '.status // empty' || true)
    say "P4 coworker=${AG:+created} trigger=${SLUG:+created} run-id=${RUN:-none} session-id=${SES:-none} run-status=${ST:-none}"
else
    say "P4 FAIL coworker not created"
fi

# P5: does a stray promise rejection end the process, and with what exit code.
set +e
dev node -e "setTimeout(()=>Promise.reject(new Error('x')));setTimeout(()=>{},5000)" >/dev/null 2>&1
RC=$?
set -e
say "P5 node-unhandled-rejection exit-code=$RC"

# P6: the live engine, from the host: cancel a run that does not exist. 401 means the key is refused.
KEY=$(sed -n 's/^RERUN_ENGINE_API_KEY=//p' .env | tail -n 1 | sed "s/^'\(.*\)'\$/\1/; s/^\"\(.*\)\"\$/\1/")
IP=$(docker inspect "$LIVE" -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' | awk '{print $1}')
if [ -n "$KEY" ] && [ -n "$IP" ]; then
    P6=$(printf 'Authorization: Bearer %s\n' "$KEY" | curl -s -o /dev/null -m 10 -w '%{http_code}' -X POST -H @- \
        "http://$IP:3000/agents/none/runs/none/cancel" || true)
    unset KEY
    say "P6 live-cancel-missing-run http=${P6:-none}"
else
    unset KEY
    say "P6 FAIL no engine key in .env or no live engine address"
fi

# P7: the live engine is unchanged since P0.
AFTER=$(live_state "$LIVE")
say "P7 live-engine $AFTER"
if [ "$AFTER" = "$BASE" ]; then say "P7 live-engine unchanged"; else say "P7 live-engine CHANGED"; fi
