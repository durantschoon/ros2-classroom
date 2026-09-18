# ROS environment for every shell in this image.
#
# Installed at /etc/bash.bashrc.d/ros-workspace.sh and symlinked into
# /etc/profile.d/.  Both are needed: /etc/bash.bashrc returns early for
# non-interactive shells, so `bash -lc 'ros2 ...'` -- what `compose exec` runs,
# and what the docs tell people to type -- only reaches this file through
# /etc/profile.d.  Interactive shells get here through /etc/bash.bashrc.
#
# Do not edit this in a container: a home volume would preserve the edit across
# image upgrades.

# A login shell reaches this file by both routes; source it only once.
if [ -n "${_ROS_WORKSPACE_SOURCED:-}" ]; then
    return 0 2>/dev/null || true
fi
_ROS_WORKSPACE_SOURCED=1

if [ -n "${ROS_DISTRO}" ] && [ -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]; then
    # shellcheck disable=SC1090
    . "/opt/ros/${ROS_DISTRO}/setup.bash"
fi

if [ -f "${WORKSPACE:-/workspace}/install/setup.bash" ]; then
    # shellcheck disable=SC1090
    . "${WORKSPACE:-/workspace}/install/setup.bash"
fi

# Colcon's own completion is optional; missing it is not an error.
if [ -f /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash ]; then
    # shellcheck disable=SC1091
    . /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash
fi

# `make` exists in here (build-essential), so a student who types a workstation
# target in the wrong window gets "No rule to make target 'turtlesim'", which
# reads like the project is broken.  Explain instead -- but only for our own
# target names, and only where there is no Makefile, so real make use in a
# directory with a Makefile is untouched.
make() {
    if [ ! -f Makefile ] && [ ! -f makefile ] && [ ! -f GNUmakefile ]; then
        case "${1:-}" in
            doctor|image|up|open|turtlesim|turtlesim-teleop|teleop|shell|down|package|build|run|test|\
            engine|logs|selftest|lint|digest|reset|help)
                printf '%s\n' \
                    "\`make $1\` runs on your own computer, not inside the workstation." \
                    'Type it in the terminal where you ran `make up`.' \
                    '' \
                    'In here, use ROS commands directly, e.g.:' \
                    '  ros2 run turtlesim turtlesim_node' \
                    '  pkg new my_pkg --template pubsub     (what `make package` runs)' \
                    '  pkg build my_pkg                     (what `make build` runs)' >&2
                return 2
                ;;
        esac
    fi
    command make "$@"
}
