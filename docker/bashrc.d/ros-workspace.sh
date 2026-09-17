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
