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

# Interactive shells name the distribution in front of the prompt,
# `(jazzy) ros@host:/workspace$`, the default's too: with several desktops open,
# which one a terminal belongs to is the question a student gets wrong.  Only
# when ROS_DISTRO and PS1 are both set in an interactive shell; scripts and
# `bash -lc` never see it.  ~/.bashrc (from /etc/skel) runs after this file and
# sets PS1 again, so the prefix is also put back before each prompt.  Either
# way it is added only when the prompt does not already start with it.
case $- in
    *i*)
        if [ -n "${ROS_DISTRO:-}" ] && [ -n "${PS1:-}" ]; then
            _ros_distro_prompt() {
                case "${PS1:-}" in
                    "(${ROS_DISTRO}) "*) ;;
                    *) PS1="(${ROS_DISTRO}) ${PS1:-}" ;;
                esac
            }
            _ros_distro_prompt
            case "${PROMPT_COMMAND:-}" in
                *_ros_distro_prompt*) ;;
                *) PROMPT_COMMAND="_ros_distro_prompt${PROMPT_COMMAND:+;${PROMPT_COMMAND}}" ;;
            esac
        fi
        ;;
esac

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
            engine|logs|selftest|lint|digest|reset|help|distros|uninstall)
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
