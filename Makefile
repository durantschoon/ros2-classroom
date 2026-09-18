# Host interface for the cross-platform ROS 2 tutorial workstation.
#
# Every target is a thin wrapper around one `docker compose` command, so a user
# without Make (common on Windows) can copy the equivalent command out of the
# README.  Nothing here requires a host X server.

SHELL := /bin/sh

# Container engine.  Docker is preferred when present; rootless Podman is a
# supported fallback.  Override either from the command line, e.g.
#   make up COMPOSE='podman-compose'
DETECTED := $(shell ./scripts/compose-command --make 2>/dev/null)
ENGINE ?= $(firstword $(DETECTED))
COMPOSE ?= $(wordlist 2,99,$(DETECTED))

# Two Podman 3.x warnings are false alarms for this project; run-quiet drops
# exactly those and passes everything else through.  VERBOSE=1 disables it.
QUIET := ./scripts/run-quiet

SERVICE ?= desktop
ROS_DISTRO ?= lyrical
NOVNC_PORT ?= 6080
URL := http://localhost:$(NOVNC_PORT)

# Run a command in the running desktop container as the workstation user, with
# a login shell so the ROS environment is sourced exactly as documented.
# Short flags and -T keep this working across docker compose, podman compose,
# and podman-compose; long-running programs are backgrounded inside the
# container rather than with `exec --detach`, which podman-compose lacks.
DESKTOP_EXEC = $(QUIET) $(COMPOSE) exec -T -u ros -e DISPLAY=:1 $(SERVICE) bash -lc

.PHONY: help engine doctor require-engine build up open shell turtlesim teleop logs ps down reset test lint digest

help:
	@echo 'ROS 2 tutorial workstation'
	@echo
	@echo '  Targets are listed in the order you would first use them, not'
	@echo '  alphabetically: reading top to bottom is the path from a fresh'
	@echo '  machine to a turtle you can drive. The later groups are for when'
	@echo '  something looks wrong, or for working on the project itself.'
	@echo
	@echo 'Start here -- once per machine'
	@echo '  make doctor      Check this machine can build and run the workstation'
	@echo '  make build       Build the image (slow the first time, cached after)'
	@echo
	@echo 'Every session'
	@echo '  make up          Start the browser desktop'
	@echo '  make open        Open it in your browser ($(URL))'
	@echo '  make turtlesim   Launch turtlesim on that desktop'
	@echo '  make teleop      Launch teleop; click its window, then the arrow keys'
	@echo '  make shell       A sourced ROS shell, for tutorials and your own packages'
	@echo '  make down        Stop the containers, keeping your workspace'
	@echo
	@echo 'When something looks wrong'
	@echo '  make engine      Show which container engine was detected'
	@echo '  make logs        Follow the container logs'
	@echo '  make test        Run the automated smoke tests'
	@echo
	@echo 'Working on this project'
	@echo '  make lint        Validate the compose file and shell scripts'
	@echo '  make digest      Print the base-image digest to pin'
	@echo '  make reset       Delete containers AND volumes -- destructive, asks first'
	@echo
	@echo 'Container engine: $(if $(COMPOSE),$(COMPOSE),none detected - run "make engine")'

engine:
	@./scripts/compose-command --explain

doctor:
	@./scripts/check-host

# Every target that talks to containers depends on this, so a missing engine
# produces an explanation instead of an empty command line.
require-engine:
	@./scripts/compose-command >/dev/null 2>&1 \
	    || { ./scripts/compose-command --explain; exit 1; }

# No --pull: the base image is pinned by digest, so there is nothing newer to
# fetch for a given ROS_BASE_DIGEST, and podman-compose translates --pull into
# a flag that Podman 3.x rejects.  Refresh the pin with `make digest` instead.
build: require-engine
	$(COMPOSE) build

up: require-engine
	$(QUIET) $(COMPOSE) up -d
	@echo
	@echo "Desktop starting. Open $(URL)/vnc.html?autoconnect=1&resize=remote"
	@echo 'Right-click the desktop for the turtlesim menu, or run "make turtlesim".'

open:
	@./scripts/open-url '$(URL)/vnc.html?autoconnect=1&resize=remote'

# A one-off container, so it works whether or not the desktop is running.
shell: require-engine
	$(COMPOSE) run --rm shell

turtlesim: require-engine
	$(DESKTOP_EXEC) 'nohup ros2 run turtlesim turtlesim_node >/tmp/turtlesim.log 2>&1 &'
	@echo 'turtlesim started on the browser desktop ($(URL)).'

teleop: require-engine
	$(DESKTOP_EXEC) "nohup xterm -title 'teleop (arrow keys)' -fa 'DejaVu Sans Mono' -fs 11 -e bash -lc 'ros2 run turtlesim turtle_teleop_key' >/tmp/teleop.log 2>&1 &"
	@echo 'teleop window opened on the browser desktop; click it, then use the arrow keys.'

# podman-compose passes --color to `podman logs`, which Podman 3.x rejects, so
# fall back to naming the container for the engine directly.
logs: require-engine
	@$(COMPOSE) logs -f || { \
	    echo; \
	    echo 'compose logs failed (known with podman-compose on Podman < 4).'; \
	    echo 'Try:  $(ENGINE) logs -f $$($(ENGINE) ps --format "{{.Names}}" | grep desktop | head -1)'; \
	    exit 1; }

ps: require-engine
	$(QUIET) $(COMPOSE) ps

down: require-engine
	$(QUIET) $(COMPOSE) down

# Destructive: prints exactly what will be removed and requires confirmation.
reset: require-engine
	@echo 'This removes the ros2-tutorials containers and these volumes:'
	@echo '  ros2-tutorials_ros-workspace   (src/, build/, install/, log/)'
	@echo '  ros2-tutorials_ros-home        (shell history, rosdep cache, settings)'
	@if [ "$(YES)" = "1" ]; then \
	    $(QUIET) $(COMPOSE) down -v --remove-orphans; \
	else \
	    printf 'Type "delete" to confirm: '; read answer; \
	    if [ "$$answer" = "delete" ]; then $(QUIET) $(COMPOSE) down -v --remove-orphans; \
	    else echo 'aborted; nothing was removed'; exit 1; fi; \
	fi

test:
	./scripts/smoke-container

lint: require-engine
	$(COMPOSE) config --quiet && echo 'compose config: ok'
	@if command -v shellcheck >/dev/null 2>&1; then \
	    shellcheck docker/entrypoint.sh docker/scripts/* docker/bashrc.d/*.sh scripts/smoke-container scripts/compose-command scripts/base-image-digest scripts/check-host scripts/open-url scripts/run-quiet && echo 'shellcheck: ok'; \
	else echo 'shellcheck not installed; skipping script lint'; fi

# Prints the multi-arch index digest for the configured distribution, for
# pasting into .env / compose.yaml as ROS_BASE_DIGEST.
digest:
	@if [ "$(ENGINE)" = 'docker' ] && docker buildx version >/dev/null 2>&1; then \
	    docker buildx imagetools inspect docker.io/library/ros:$(ROS_DISTRO)-ros-base \
	        | awk '/^Digest:/ {print $$2; found=1} END {if (!found) exit 1}'; \
	else \
	    ./scripts/base-image-digest $(ROS_DISTRO); \
	fi
