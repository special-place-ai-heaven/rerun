#!/bin/sh
# Replaces the key the app and the engine share: RERUN_ENGINE_API_KEY in .env (the engine gets it as
# RERUN_API_KEY) and the engine's row in public.engine_pool, which is where the app reads it. App and
# engine are stopped while it changes, then started and checked. Run from the clone:
#   sudo sh deploy/vps/rotate-engine-key.sh check      shows what a rotation would find; changes nothing
#                                                      (it runs the database step with a throwaway key and rolls it back)
#   sudo sh deploy/vps/rotate-engine-key.sh rotate     new key in the database and .env, restart, verify
#   sudo sh deploy/vps/rotate-engine-key.sh rollback   puts the previous key back the same way
# A rotation that stopped part-way is finished by running rotate again; it reuses the same new key.
# How the key values travel: read from .env and from the record file .env.engine-key-rotation
# (root-only, git-ignored) into shell variables; to the database only as COPY data on psql's standard
# input, never in the SQL text; to curl only as a header on standard input (-H @-); written only to
# .env (the set-env.sh writer) and the record file. No key is on any command line and none is printed:
# every line prints names, counts and HTTP codes only.
set -eu
cd "$(dirname "$0")/../.."
LC_ALL=C
export LC_ALL
umask 077
SUPABASE_DIR=${SUPABASE_DIR:-/docker/supabase-rerun}
DBC=${SUPABASE_DB_CONTAINER:-supabase-db}
POLL=${ROTATE_POLL_S:-2}
WAIT=${ROTATE_WAIT_S:-90}
REC=.env.engine-key-rotation
ME="sudo sh deploy/vps/rotate-engine-key.sh"
DBM=none

say() { printf '%s\n' "$*"; }

# The key in .env: the last RERUN_ENGINE_API_KEY= line, one pair of surrounding quotes removed (as update.sh does).
envkey() { sed -n 's/^RERUN_ENGINE_API_KEY=//p' .env 2>/dev/null | tail -n 1 | sed "s/^'\(.*\)'\$/\1/; s/^\"\(.*\)\"\$/\1/"; }

# Acceptable: 32 or more of A-Z a-z 0-9 _ . ~ + / = - and nothing else (no blank, tab, quote or backslash).
ok_key() { case "$1" in ''|*[!A-Za-z0-9_.~+/=-]*) return 1 ;; esac; [ "${#1}" -ge 32 ]; }

# Same writer as set-env.sh: the value goes in single quotes, read by awk from the environment.
put() {
    case "$2" in *"'"*) echo "The value of $1 contains a single quote, which .env cannot hold. Nothing changed for it."; return 0 ;; esac
    K="$1" V="$2" awk 'BEGIN { k = ENVIRON["K"]; line = k "=\047" ENVIRON["V"] "\047" }
        $0 ~ "^" k "=" { if (!done) print line; done = 1; next } { print }
        END { if (!done) print line }' .env > .env.tmp && cat .env.tmp > .env && rm -f .env.tmp
}

# The record file: OLD= and NEW= while a swap is in progress, PREVIOUS= once it finished.
recval() { sed -n "s/^$1=//p" "$REC" 2>/dev/null | tail -n 1; }
recstate() {
    if [ ! -f "$REC" ]; then echo absent
    elif ok_key "$(recval OLD)" && ok_key "$(recval NEW)"; then echo in-progress
    elif ok_key "$(recval PREVIOUS)"; then echo finished
    else echo unreadable; fi
}

# Database access, SQL always on standard input. -e PGPASSWORD with no value makes docker take it from its own
# environment, so the password is on no command line.
psql_socket() { docker exec -i -u postgres "$DBC" psql -X -q -t -A -v ON_ERROR_STOP=1 -d postgres; }
psql_local() { docker exec -i "$DBC" psql -X -q -t -A -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d postgres; }
psql_password() { PGPASSWORD="$PW" docker exec -i -e PGPASSWORD "$DBC" psql -X -q -t -A -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d postgres; }
db() { "psql_$DBM"; }
pick_db() {
    for DBM in socket local password; do
        if [ "$DBM" = password ]; then
            PW=$(sed -n 's/^POSTGRES_PASSWORD=//p' "$SUPABASE_DIR/.env" 2>/dev/null | tail -n 1 | sed "s/^'\(.*\)'\$/\1/; s/^\"\(.*\)\"\$/\1/")
            [ -n "$PW" ] || continue
        fi
        if [ "$(printf '%s\n' '-- rotate-engine-key: ping' 'select 1;' | db 2>/dev/null)" = 1 ]; then return 0; fi
    done
    DBM=none
    return 1
}

# Opening lines of a program that needs the keys: they go in only as the one COPY data line.
sql_keys() {
    printf '%s\n' "-- rotate-engine-key: $1" '\set VERBOSITY terse' 'begin;' \
        'create temp table k(old text, new text) on commit drop;' 'copy k from stdin;'
    printf '%s\t%s\n' "$KEY_FROM" "$KEY_TO"
    printf '%s\n' '\.'
}
# Prints rows_old|rows_new|tables. Changes nothing: it ends in rollback.
sql_count() {
    sql_keys count
    cat <<'SQL'
select (select count(*) from public.engine_pool p join k on p.engine_api_key = k.old)
    || '|' || (select count(*) from public.engine_pool p join k on p.engine_api_key = k.new)
    || '|' || coalesce((select string_agg(table_schema || '.' || table_name, ',' order by table_schema, table_name)
        from information_schema.columns where column_name = 'engine_api_key'), '');
rollback;
SQL
}
# One transaction: old to new when exactly one row holds old and none new; nothing when it is already done;
# anything else aborts with the two counts (never a key) and psql exits non-zero. $1 names the program,
# $2 ends it: "swap commit" is the change, "rehearse rollback" runs the very same statements and undoes them.
sql_swap() {
    sql_keys "$1"
    cat <<'SQL'
create temp table s on commit drop as select
    (select count(*) from public.engine_pool p join k on p.engine_api_key = k.old) as o,
    (select count(*) from public.engine_pool p join k on p.engine_api_key = k.new) as n;
update public.engine_pool p set engine_api_key = k.new, updated_at = now()
    from k, s where p.engine_api_key = k.old and s.o = 1 and s.n = 0;
do $$
declare o bigint; n bigint;
begin
    select count(*) into o from public.engine_pool p join k on p.engine_api_key = k.old;
    select count(*) into n from public.engine_pool p join k on p.engine_api_key = k.new;
    if o <> 0 or n <> 1 then raise exception 'rows_old=% rows_new=%', o, n; end if;
end $$;
select case when o = 0 and n = 1 then 'already' else 'swapped' end from s;
SQL
    printf '%s\n' "$2;"
}
# Runs the database step for real and rolls it back, so a database that would refuse it says so before
# anything is stopped. Prints one line; returns 1 when the step would fail.
rehearse() {
    RES=$( { sql_swap rehearse rollback | db; } 2>&1 ) && RC=0 || RC=$?
    case "$RES" in *"$KEY_FROM"*|*"$KEY_TO"*) RES='(message withheld: it held a key)' ;; esac
    if [ "$RC" != 0 ]; then
        say "db-rehearsal FAIL: the database would refuse the change."
        printf '%s\n' "$RES" | grep '^ERROR' | head -n 3 || true
        RES=''
        return 1
    fi
    case "$RES" in *already*) say "db-rehearsal already (the database holds the new key; rolled back)" ;; *swapped*) say "db-rehearsal swapped (rolled back)" ;;
        *) say "db-rehearsal FAIL: no answer from the database step."; RES=''; return 1 ;; esac
    RES=''
}
# Sets ROWS_OLD ROWS_NEW TABLES from the count program; numbers and names only, else "error".
counts() {
    C=$(sql_count | db 2>/dev/null) || C=''
    case "$C" in *'|'*'|'*) ;; *) C='error|error|error' ;; esac
    ROWS_OLD=${C%%|*}
    C=${C#*|}
    ROWS_NEW=${C%%|*}
    TABLES=${C#*|}
    case "$ROWS_OLD$ROWS_NEW" in ''|*[!0-9]*) ROWS_OLD=error ROWS_NEW=error ;; esac
    case "$TABLES" in *[!A-Za-z0-9_.,]*) TABLES=error ;; esac
}

# HTTP code of a request made inside the engine container. With a key, the Bearer header goes on standard input.
code() {
    KEY_H=$1
    shift
    if [ -n "$KEY_H" ]; then
        printf 'Authorization: Bearer %s\n' "$KEY_H" | docker compose exec -T engine curl -s -o /dev/null -m 5 -w '%{http_code}' -H @- "$@" 2>/dev/null || true
    else
        docker compose exec -T engine curl -s -o /dev/null -m 5 -w '%{http_code}' "$@" </dev/null 2>/dev/null || true
    fi
    KEY_H=''
}
# Asks again every POLL seconds for up to WAIT seconds, while a service may still be starting, until the code is $1.
poll() {
    UNTIL=$1
    shift
    END=$(( $(date +%s) + WAIT ))
    while :; do
        GOT=$(code "$@")
        [ "$GOT" != "$UNTIL" ] || break
        [ "$(date +%s)" -lt "$END" ] || break
        sleep "$POLL"
    done
    printf '%s' "${GOT:-none}"
}
expect() {
    if [ "$3" = "$2" ]; then say "$1 http=$3 ok"; else say "$1 http=${3:-none} FAIL (want $2)"; FAILS=$((FAILS + 1)); fi
}

# Starts app and engine, but only when .env holds exactly the expected, acceptable key: never an engine
# with a blank or unknown key.
up() {
    KEY_NOW=$(envkey)
    if ok_key "$KEY_NOW" && [ "$KEY_NOW" = "$1" ]; then
        KEY_NOW=''
        docker compose up -d </dev/null
        return 0
    fi
    KEY_NOW=''
    say "start REFUSED: .env does not hold the expected key (or it is blank or malformed). App and engine are left STOPPED."
    stopped_help
}
stopped_help() {
    say "recover: '$ME check' shows the state. The record file $REC names the change in progress:"
    say "  '$ME rotate' finishes it and '$ME rollback' undoes it. Both check .env before starting anything."
    exit 1
}

# Old to new, in this order: record, stop, database, .env, start, verify. Safe to run again after any stop.
swap() {
    KEY_REC_BEFORE=$(cat "$REC" 2>/dev/null) || KEY_REC_BEFORE=''
    printf 'OLD=%s\nNEW=%s\n' "$KEY_FROM" "$KEY_TO" > "$REC"
    say "1/6 stop app engine"
    docker compose stop app engine </dev/null
    say "2/6 database (db-access=$DBM)"
    RES=$( { sql_swap swap commit | db; } 2>&1 ) && RC=0 || RC=$?
    case "$RES" in *"$KEY_FROM"*|*"$KEY_TO"*) RES='(message withheld: it held a key)' ;; esac
    if [ "$RC" != 0 ]; then
        say "db-swap FAIL: the database is unchanged."
        printf '%s\n' "$RES" | grep '^ERROR' | head -n 3 || true
        say "db-swap: zero rows holding the old key most likely means the key in .env is quoted or written differently from the one in the database."
        # Nothing changed, so the record goes back to what it was: a stale in-progress record would make
        # rotate and rollback expect keys that are in neither place.
        if [ -n "$KEY_REC_BEFORE" ]; then printf '%s\n' "$KEY_REC_BEFORE" > "$REC"; else rm -f "$REC"; fi
        KEY_REC_BEFORE=''
        say "record put back as it was before this run"
        up "$KEY_FROM"
        say "App and engine started again with the key they had. FAIL: nothing was rotated."
        exit 1
    fi
    case "$RES" in *already*) say "db-swap already (the database held the new key)" ;; *) say "db-swap swapped" ;; esac
    RES=''

    say "3/6 .env"
    KEY_NOW=$(envkey)
    if [ "$KEY_NOW" = "$KEY_TO" ]; then
        say "env-key already new"
    elif [ "$KEY_NOW" = "$KEY_FROM" ]; then
        # A failed write is caught by the re-read below, which leaves the containers stopped.
        put RERUN_ENGINE_API_KEY "$KEY_TO" || true
        if [ "$(envkey)" != "$KEY_TO" ]; then
            say "env-key FAIL: .env did not take the new key. App and engine are left STOPPED."
            stopped_help
        fi
        say "env-key written"
    else
        say "env-key FAIL: .env holds neither the old nor the new key. App and engine are left STOPPED."
        stopped_help
    fi
    KEY_NOW=''

    say "4/6 start"
    up "$KEY_TO"

    say "5/6 verify"
    FAILS=0
    expect "verify engine-health" 200 "$(poll 200 '' http://localhost:3000/health)"
    expect "verify engine-no-key" 401 "$(code '' http://localhost:3000/agents)"
    expect "verify engine-new-key" 200 "$(code "$KEY_TO" http://localhost:3000/agents)"
    expect "verify engine-old-key" 401 "$(code "$KEY_FROM" http://localhost:3000/agents)"
    expect "verify app-new-key" 400 "$(poll 400 "$KEY_TO" -X POST http://app:3000/api/hub)"
    expect "verify app-old-key" 401 "$(code "$KEY_FROM" -X POST http://app:3000/api/hub)"
    counts
    if [ "$ROWS_NEW" = 1 ] && [ "$ROWS_OLD" = 0 ]; then
        say "verify db rows-new=$ROWS_NEW rows-old=$ROWS_OLD ok"
    else
        say "verify db rows-new=$ROWS_NEW rows-old=$ROWS_OLD FAIL (want 1 and 0)"
        FAILS=$((FAILS + 1))
    fi
    if [ "$FAILS" != 0 ]; then
        say "FAIL: $FAILS check(s) did not pass. The record file $REC is kept."
        say "'$ME rollback' puts the key from before this $MODE back; '$ME check' shows the state."
        exit 1
    fi

    printf 'PREVIOUS=%s\n' "$KEY_FROM" > "$REC"
    say "6/6 record: the key replaced is kept in $REC for rollback"
    say "$MODE complete"
}

check() {
    if [ -f .env ]; then say "env-file present"; else say "env-file absent"; fi
    KEY_CUR=$(envkey)
    QUOTING=$(sed -n 's/^RERUN_ENGINE_API_KEY=/=/p' .env 2>/dev/null | tail -n 1 | sed "s/^='.*'\$/single/; s/^=\".*\"\$/double/; s/^=.*/none/")
    if ok_key "$KEY_CUR"; then KEYOK=yes; else KEYOK=no; fi
    say "env-key acceptable=$KEYOK quoting=${QUOTING:-no-line}"
    if pick_db; then say "db-access=$DBM"; else say "db-access FAIL: none of socket, local, password answered"; fi
    if [ "$DBM" != none ] && [ "$KEYOK" = yes ]; then
        KEY_FROM=$KEY_CUR
        KEY_TO=$KEY_CUR
        counts
        say "db-tables-with-engine_api_key ${TABLES:-none}"
        say "db-rows-holding-current-key $ROWS_OLD (expect 1)"
        # The database step itself, with a throwaway key that is kept nowhere, rolled back.
        KEY_TO=$(openssl rand -hex 32 2>/dev/null) || KEY_TO=''
        case "$KEY_TO" in *[!0-9a-f]*) KEY_TO='' ;; esac
        MINTED=${#KEY_TO}
        if [ "$MINTED" = 64 ]; then
            rehearse || true
        else
            say "db-rehearsal skipped (openssl gave no key)"
        fi
        KEY_TO=''
    else
        say "db-rows-holding-current-key skipped (needs db access and an acceptable key)"
    fi
    say "running $(docker compose ps --status running --services </dev/null 2>/dev/null | sort | tr '\n' ' ')"
    GOT=$(code '' http://localhost:3000/agents)
    say "engine-no-key http=${GOT:-none} (expect 401)"
    if [ "$KEYOK" = yes ]; then
        GOT=$(code "$KEY_CUR" http://localhost:3000/agents)
        say "engine-current-key http=${GOT:-none} (expect 200)"
        GOT=$(code "$KEY_CUR" -X POST http://app:3000/api/hub)
        say "app-current-key http=${GOT:-none} (expect 400)"
    fi
    say "record $(recstate)"
}

MODE=${1:-}
case "$MODE" in
    check) check; exit 0 ;;
    rotate) WORD=ROTATE ;;
    rollback) WORD=ROLLBACK ;;
    *) say "Usage: $ME check|rotate|rollback"; exit 2 ;;
esac

# Everything that can refuse comes before the record is written and anything is stopped.
KEY_CUR=$(envkey)
STATE=$(recstate)
if [ "$STATE" = unreadable ]; then
    say "record FAIL: $REC is there but holds no acceptable OLD/NEW or PREVIOUS. Nothing changed."
    exit 1
fi
if [ "$MODE" = rotate ] && [ "$STATE" = in-progress ]; then
    KEY_FROM=$(recval OLD)
    KEY_TO=$(recval NEW)
    say "record in-progress: finishing that change with the same new key"
elif [ "$MODE" = rotate ]; then
    if ! ok_key "$KEY_CUR"; then
        say "env-key FAIL: no acceptable RERUN_ENGINE_API_KEY in .env (see '$ME check'). Nothing changed."
        exit 1
    fi
    KEY_FROM=$KEY_CUR
    KEY_TO=$(openssl rand -hex 32 2>/dev/null) || KEY_TO=''
    case "$KEY_TO" in *[!0-9a-f]*) KEY_TO='' ;; esac
    if [ "${#KEY_TO}" != 64 ]; then
        say "mint FAIL: openssl rand -hex 32 did not give 64 hex characters. Nothing changed."
        exit 1
    fi
    say "mint new key ok"
elif [ "$STATE" = in-progress ]; then
    KEY_FROM=$(recval NEW)
    KEY_TO=$(recval OLD)
    say "record in-progress: undoing that change"
elif [ "$STATE" = finished ]; then
    if ! ok_key "$KEY_CUR"; then
        say "env-key FAIL: no acceptable RERUN_ENGINE_API_KEY in .env (see '$ME check'). Nothing changed."
        exit 1
    fi
    KEY_FROM=$KEY_CUR
    KEY_TO=$(recval PREVIOUS)
    say "record finished: putting the previous key back"
else
    say "rollback REFUSED: no record file $REC, so there is no previous key. Nothing changed."
    exit 1
fi
if [ "$KEY_FROM" = "$KEY_TO" ]; then
    say "FAIL: the old and the new key are the same. Nothing changed."
    exit 1
fi
if ! pick_db; then
    say "db-access FAIL: none of socket, local, password answered. Nothing changed."
    exit 1
fi
say "db-access=$DBM"
# Look before stopping anything: the database step is run and rolled back. The old key must be in exactly
# one row (or the new one already is, when an earlier run got that far); anything else is refused here.
if ! rehearse; then
    say "Nothing changed, nothing was stopped."
    say "Zero rows holding the old key most likely means the key in .env is quoted or written differently from the one in the database."
    exit 1
fi

say "This stops the app and the engine for about a minute; any coworker run in progress fails."
printf 'Type %s to go on: ' "$WORD"
read -r ANSWER || ANSWER=''
if [ "$ANSWER" != "$WORD" ]; then
    say "Not confirmed: nothing changed."
    exit 0
fi
swap
