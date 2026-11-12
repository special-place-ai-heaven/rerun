#!/bin/sh
# Removes what updates and old builds leave behind on this server, for every stack on it, and nothing
# that is in use or holds data: images without a tag that no container uses (what a pull replaced), and
# build cache that no image uses. It never removes a tagged image, a container, a volume or a network.
#   sudo sh deploy/vps/tidy.sh report      disk use and what Docker holds; changes nothing
#   sudo sh deploy/vps/tidy.sh run         removes the two kinds above; shows the disk before and after
#   sudo sh deploy/vps/tidy.sh install     a systemd timer that does `run` every Sunday at 04:30
#   sudo sh deploy/vps/tidy.sh uninstall   takes that timer away again
# The timer runs a copy of this file that belongs to root, not the file in the clone, so changing the
# clone cannot change what root runs. After an update of this file, run install again.
set -eu
SELF=$(cd "$(dirname "$0")" && pwd)/tidy.sh
UNITS=${TIDY_ROOT:-}/etc/systemd/system
BIN=${TIDY_ROOT:-}/usr/local/sbin/rerun-tidy

disk() { df -h / | tail -n 1; }

case "${1:-}" in
    report)
        disk
        docker system df
        ;;
    run)
        echo "before: $(disk)"
        docker image prune -f
        docker builder prune -af
        echo "after:  $(disk)"
        ;;
    install)
        install -m 755 "$SELF" "$BIN"
        printf '%s\n' '[Unit]' 'Description=Remove untagged images and unused build cache (deploy/vps/tidy.sh)' \
            '[Service]' 'Type=oneshot' "ExecStart=$BIN run" > "$UNITS/rerun-tidy.service"
        printf '%s\n' '[Unit]' 'Description=Weekly run of rerun-tidy' '[Timer]' 'OnCalendar=Sun 04:30' \
            'Persistent=true' '[Install]' 'WantedBy=timers.target' > "$UNITS/rerun-tidy.timer"
        systemctl daemon-reload
        systemctl enable --now rerun-tidy.timer
        systemctl list-timers rerun-tidy.timer --no-pager
        ;;
    uninstall)
        systemctl disable --now rerun-tidy.timer || true
        rm -f "$UNITS/rerun-tidy.service" "$UNITS/rerun-tidy.timer" "$BIN"
        systemctl daemon-reload
        echo "timer removed"
        ;;
    *)
        echo "Usage: sudo sh deploy/vps/tidy.sh report|run|install|uninstall"
        exit 2
        ;;
esac
