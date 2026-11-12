#!/bin/sh
# Entrypoint of the engine image. The engine's key is handed to the engine on an inherited file
# descriptor and never sits in the environment of the engine process: copy it to a shell variable
# that is not exported, drop it from the environment, open the descriptor, then exec the engine.
# The engine reads the descriptor once at start and closes it (src/config/env.ts).
set -e
if [ -n "${RERUN_API_KEY:-}" ]; then
    rerun_key="$RERUN_API_KEY"
    unset RERUN_API_KEY
    RERUN_KEY_FD=3
    export RERUN_KEY_FD
    exec 3<<RERUN_KEY_END
$rerun_key
RERUN_KEY_END
    unset rerun_key
else
    unset RERUN_API_KEY
fi
exec "$@"
