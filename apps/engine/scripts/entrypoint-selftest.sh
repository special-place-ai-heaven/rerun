#!/bin/sh
# Image build self-test of the entrypoint chain, run as a build step through the real entrypoint, so
# tini is PID 1 here and this script is its child holding the key descriptor. The dummy key is
# compared, never printed.
set -eu
fail() { echo "SELFTEST FAIL: $*" >&2; exit 1; }
here=$(dirname "$0")

[ "$(cat /proc/1/comm)" = tini ] || fail "PID 1 is not tini"
case "$(readlink /proc/1/fd/3)" in
    pipe:*) ;;
    *) fail "fd 3 held by tini is not a pipe: the design changes" ;;
esac
[ "$(tr '\0' '\n' </proc/1/environ | grep -c '^RERUN_API_KEY=')" = 0 ] || fail "tini environment has the key variable"
[ "$(tr '\0' '\n' </proc/self/environ | grep -c '^RERUN_API_KEY=')" = 0 ] || fail "child environment has the key variable"
[ "${RERUN_KEY_FD:-}" = 3 ] || fail "RERUN_KEY_FD is not 3"

# The child reads the descriptor once, as the engine does, then closes it.
key=$(cat <&3)
exec 3<&-
[ "$key" = dummy ] || fail "key read from fd 3 is wrong"
# tini still holds its own copy of the descriptor: it must now be empty.
left=$(timeout 2 dd if=/proc/1/fd/3 iflag=nonblock 2>/dev/null | wc -c)
[ "$left" -eq 0 ] || fail "fd 3 of tini still holds $left byte(s)"
echo "selftest: pid1 tini, fd 3 pipe, key drained, key variable in no environment"

[ ! -f "$here/entrypoint-selftest-signals.sh" ] || sh "$here/entrypoint-selftest-signals.sh"
