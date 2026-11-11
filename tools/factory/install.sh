#!/bin/sh
# Install the factory tools: tools/factory/install.sh --prefix DIR
# Writes DIR/bin/<wrappers> and DIR/factory/<sources>. The only edit is the install path:
# the string /data/tools/factory becomes DIR/factory in the copies (wrappers and sources).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PREFIX=
while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX=${2:-}; shift 2 ;;
    -h|--help) echo "usage: install.sh --prefix DIR"; exit 0 ;;
    *) echo "usage: install.sh --prefix DIR" >&2; exit 2 ;;
  esac
done
[ -n "$PREFIX" ] || { echo "usage: install.sh --prefix DIR" >&2; exit 2; }
mkdir -p "$PREFIX/bin" "$PREFIX/factory"
PREFIX=$(cd "$PREFIX" && pwd)
for f in gate.py factory.py jobcost.py; do
  sed "s#/data/tools/factory#$PREFIX/factory#g" "$HERE/$f" > "$PREFIX/factory/$f"
done
for w in "$HERE"/bin/*; do
  n=$(basename "$w")
  sed "s#/data/tools/factory#$PREFIX/factory#g" "$w" > "$PREFIX/bin/$n"
  chmod 755 "$PREFIX/bin/$n"
done
echo "installed $(ls "$PREFIX/bin" | wc -l) wrappers into $PREFIX/bin"
