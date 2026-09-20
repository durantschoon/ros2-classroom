# syntax=docker/dockerfile:1

# The tag stays human readable, but the digest is what actually pins the build.
# `make digest` prints the current digest for a distribution; changing ROS_DISTRO
# requires supplying the matching ROS_BASE_DIGEST.
#
# The registry is spelled out: Podman refuses short names unless the host
# configures unqualified-search-registries, and Docker resolves the canonical
# form identically.
ARG ROS_REGISTRY=docker.io/library
ARG ROS_DISTRO=lyrical
ARG ROS_BASE_DIGEST=sha256:0c19f326a339ed770ef1d4c0646a8b53bdb49dd5ff74b6de41ebdb8ac21e1806
FROM ${ROS_REGISTRY}/ros:${ROS_DISTRO}-ros-base@${ROS_BASE_DIGEST}

ARG ROS_DISTRO
ARG USER_NAME=ros
ARG USER_UID=1000
ARG USER_GID=1000

# Additional packages baked into the image.  This is the reproducible way to
# keep packages that `install-ros-packages` would otherwise install only into a
# container's writable layer.
ARG EXTRA_ROS_PACKAGES=""
ARG EXTRA_APT_PACKAGES=""

LABEL org.opencontainers.image.title="ROS 2 tutorial workstation" \
      org.opencontainers.image.description="ROS 2 turtlesim and tutorial workstation with a browser desktop" \
      org.opencontainers.image.source="https://github.com/durantschoon/ros2-classroom" \
      org.opencontainers.image.licenses="Apache-2.0"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# One apt layer: ROS tutorial tools, a build toolchain, and a minimal desktop
# (Xvfb, Openbox, x11vnc, noVNC).  A full Ubuntu desktop is deliberately avoided.
#
# The upgrade is not optional.  The base image is pinned by digest, but the ROS
# apt repository moves: after a ROS sync it serves packages rebuilt against
# newer core libraries than the pinned base contains.  ROS packages depend on
# each other by name, not by version, so apt installs the new turtlesim on top
# of the old rosidl typesupport without complaint, and turtlesim_node then dies
# at start with "undefined symbol".  Upgrading first brings the base's ROS
# packages to the same sync as everything installed after it.
#
# The package lists are left unquoted on purpose: EXTRA_ROS_PACKAGES and
# EXTRA_APT_PACKAGES are space-separated, and word splitting is how they become
# separate arguments.
# hadolint ignore=SC2086
RUN extra_ros="" \
    && for pkg in ${EXTRA_ROS_PACKAGES}; do extra_ros="${extra_ros} ros-${ROS_DISTRO}-${pkg}"; done \
    && apt-get update \
    && apt-get upgrade --yes --no-install-recommends \
    && apt-get install --yes --no-install-recommends \
        ros-${ROS_DISTRO}-turtlesim \
        ros-${ROS_DISTRO}-rviz2 \
        ros-${ROS_DISTRO}-rqt \
        ros-${ROS_DISTRO}-rqt-common-plugins \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-vcstool \
        python3-flake8 \
        python3-pytest-cov \
        python3-pytest-repeat \
        python3-pytest-rerunfailures \
        clang-format \
        build-essential \
        cmake \
        git \
        curl \
        sudo \
        less \
        nano \
        ca-certificates \
        dbus-x11 \
        fonts-dejavu-core \
        novnc \
        openbox \
        procps \
        supervisor \
        tini \
        websockify \
        x11vnc \
        xterm \
        xvfb \
        ${extra_ros} \
        ${EXTRA_APT_PACKAGES} \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 and later ship a default user at UID 1000; reclaim the id so the
# workspace owner is predictable across hosts.
RUN existing_user="$(getent passwd ${USER_UID} | cut -d: -f1)" \
    && if [ -n "${existing_user}" ] && [ "${existing_user}" != "${USER_NAME}" ]; then \
           userdel --remove "${existing_user}" 2>/dev/null || userdel "${existing_user}"; \
       fi \
    && existing_group="$(getent group ${USER_GID} | cut -d: -f1)" \
    && if [ -n "${existing_group}" ] && [ "${existing_group}" != "${USER_NAME}" ]; then \
           groupdel "${existing_group}" || true; \
       fi \
    && getent group ${USER_GID} >/dev/null || groupadd --gid ${USER_GID} ${USER_NAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} --create-home --shell /bin/bash ${USER_NAME} \
    && printf '%s ALL=(ALL) NOPASSWD:ALL\n' "${USER_NAME}" > /etc/sudoers.d/${USER_NAME} \
    && chmod 0440 /etc/sudoers.d/${USER_NAME}

# Every interactive bash session gets the same ROS environment, without editing
# a mutable per-user .bashrc that a home volume would then pin forever.
#
# The single quotes are on purpose: these lines are written into bash.bashrc
# literally, to be expanded by the shells that source it, not at build time.
# hadolint ignore=SC2016
RUN mkdir -p /etc/bash.bashrc.d \
    && printf '%s\n' \
        '' \
        '# Source drop-ins (added by the ROS tutorial workstation image).' \
        'if [ -d /etc/bash.bashrc.d ]; then' \
        '    for _rc in /etc/bash.bashrc.d/*.sh; do' \
        '        [ -r "$_rc" ] && . "$_rc"' \
        '    done' \
        '    unset _rc' \
        'fi' \
        >> /etc/bash.bashrc

COPY docker/bashrc.d/ros-workspace.sh /etc/bash.bashrc.d/ros-workspace.sh
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
COPY docker/scripts/ /usr/local/bin/
COPY docker/templates/ /usr/share/ros-workstation/templates/
COPY docker/desktop/welcome.txt /usr/share/ros-workstation/welcome.txt
COPY docker/supervisord.conf /etc/supervisor/conf.d/ros-desktop.conf
COPY docker/desktop/openbox-autostart /etc/xdg/openbox/autostart
COPY docker/desktop/menu.xml /etc/xdg/openbox/menu.xml
COPY docker/desktop/app-defaults/ /usr/share/ros-workstation/app-defaults/

# /etc/profile.d covers login shells (bash -lc); the /etc/bash.bashrc.d loop
# covers interactive ones.  One file, both routes, guarded against double use.
RUN ln -s /etc/bash.bashrc.d/ros-workspace.sh /etc/profile.d/ros-workspace.sh

RUN chmod 0755 /usr/local/bin/entrypoint \
        /usr/local/bin/install-ros-packages \
        /usr/local/bin/init-workspace \
        /usr/local/bin/tutorial \
        /usr/local/bin/pkg \
        /usr/local/bin/turtlesim-teleop \
    && mkdir -p /workspace/src /var/log/supervisor \
    && chown -R ${USER_UID}:${USER_GID} /workspace

ENV USER_NAME=${USER_NAME} \
    WORKSPACE=/workspace \
    DISPLAY=:1 \
    XAPPLRESDIR=/usr/share/ros-workstation/app-defaults/ \
    SCREEN_GEOMETRY=1600x900x24 \
    NOVNC_PORT=6080 \
    VNC_PORT=5900 \
    VNC_PASSWORD=""


EXPOSE 6080

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl --fail --silent --output /dev/null http://127.0.0.1:${NOVNC_PORT}/vnc.html || exit 1

WORKDIR /workspace

# Default to the unprivileged workstation user.  The desktop service overrides
# this with `user: root` in compose.yaml because supervisor has to write its own
# socket and logs and to start each graphical program as ${USER_NAME}.
USER ${USER_NAME}

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint"]
CMD ["supervisord", "--nodaemon", "--configuration", "/etc/supervisor/conf.d/ros-desktop.conf"]
