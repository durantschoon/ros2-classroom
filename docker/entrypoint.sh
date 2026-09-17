#!/bin/bash
# Entrypoint for the ROS tutorial workstation.
#
# Runs as PID 1's child under tini, so signals and exit codes pass through the
# final exec.  Every container in compose.yaml shares this entrypoint, whether
# it starts the desktop supervisor or a one-off shell.
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
USER_NAME="${USER_NAME:-ros}"

log() { printf '[entrypoint] %s\n' "$*" >&2; }

# 1. Workspace layout.  Named volumes start empty on a fresh project, so the
#    directories and their ownership are re-established on every start.
if [ -w "$(dirname "${WORKSPACE}")" ] || [ -d "${WORKSPACE}" ]; then
    mkdir -p "${WORKSPACE}/src"
    if [ "$(id -u)" = "0" ] && id "${USER_NAME}" >/dev/null 2>&1; then
        # Only fix the top level and src: chowning a large build tree on every
        # start is slow and would fight colcon's own bookkeeping.
        chown "${USER_NAME}:${USER_NAME}" "${WORKSPACE}" "${WORKSPACE}/src" 2>/dev/null || true
        if [ -d "/home/${USER_NAME}" ] && [ "$(stat -c '%U' "/home/${USER_NAME}")" != "${USER_NAME}" ]; then
            chown -R "${USER_NAME}:${USER_NAME}" "/home/${USER_NAME}" || true
        fi
    fi
fi

# 2. rosdep.  The base image usually ships an initialized database; initialize
#    only when it is genuinely absent and never fail because it already exists.
if [ "$(id -u)" = "0" ] && [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    log 'initializing rosdep sources'
    rosdep init >/dev/null 2>&1 || log 'rosdep init skipped (already initialized or offline)'
fi

# 3. ROS environment for non-interactive commands.  Interactive shells get the
#    same thing from /etc/bash.bashrc.d/ros-workspace.sh.
if [ -n "${ROS_DISTRO:-}" ] && [ -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]; then
    set +u
    # shellcheck disable=SC1090
    . "/opt/ros/${ROS_DISTRO}/setup.bash"
    set -u
fi

if [ -f "${WORKSPACE}/install/setup.bash" ]; then
    set +u
    # shellcheck disable=SC1090
    . "${WORKSPACE}/install/setup.bash"
    set -u
fi

exec "$@"
