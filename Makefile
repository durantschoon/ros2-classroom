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
# reconnect=true: noVNC drops the connection after laptop sleep or a network
# blip.  Nothing in the desktop stops when that happens, so reconnect on our own
# rather than leaving a student staring at "Disconnected".
DESKTOP_URL := $(URL)/vnc.html?autoconnect=1&resize=remote&reconnect=true

# Run a command in the running desktop container as the workstation user, with
# a login shell so the ROS environment is sourced exactly as documented.
# Short flags and -T keep this working across docker compose, podman compose,
# and podman-compose; long-running programs are backgrounded inside the
# container rather than with `exec --detach`, which podman-compose lacks.
DESKTOP_EXEC = $(QUIET) $(COMPOSE) exec -T -u ros -e DISPLAY=:1 $(SERVICE) bash -lc

# The student package targets run the `pkg` helper inside the desktop, which
# prints every real ros2/colcon command before running it.  PKG_VIA_MAKE makes
# its "next:" hints name make targets instead of pkg subcommands.
PKG_EXEC = $(QUIET) $(COMPOSE) exec -T -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $(SERVICE) bash -lc

# --- `make <target> help` and `make <target> examples` ------------------------
# make has no subcommands: `make shell help` means "run shell, then run help".
# So when help or examples is named alongside another goal, no real target may
# run at all -- `make up help` must not start containers.  Every goal on the
# command line is replaced: the first prints the help, the rest do nothing.
# Word order does not matter, and scripts/workstation-help refuses, loudly,
# any target it has nothing to say about.
HELP_WORDS := $(filter help examples,$(MAKECMDGOALS))
HELP_TOPICS := $(filter-out help examples,$(MAKECMDGOALS))

ifneq ($(and $(HELP_WORDS),$(HELP_TOPICS)),)

.PHONY: $(MAKECMDGOALS)
$(firstword $(MAKECMDGOALS)):
	@./scripts/workstation-help --compose '$(COMPOSE)' --url '$(URL)' $(MAKECMDGOALS)
$(wordlist 2,99,$(MAKECMDGOALS)):
	@:

else

.PHONY: help examples engine doctor require-engine require-desktop image up open shell turtlesim \
	turtlesim-teleop teleop \
	package build run test logs ps down reset uninstall selftest check lint digest

# All help text lives in scripts/workstation-help, which prints targets that
# have their own `help` and `examples` in bold on a terminal, or marked with
# a * when piped.
help:
	@./scripts/workstation-help --compose '$(if $(COMPOSE),$(COMPOSE),none detected - run "make engine")' --url '$(URL)'

# `make examples` alone: say which targets have them.
examples:
	@./scripts/workstation-help examples

engine:
	@./scripts/compose-command --explain

doctor:
	@./scripts/check-host

# Targets that exec into the desktop need it running; say so plainly rather than
# surfacing the engine's "no such container" error.
require-desktop: require-engine
	@$(QUIET) $(COMPOSE) exec -T $(SERVICE) true >/dev/null 2>&1 \
	    || { echo 'The desktop is not running. Start it first:  make up'; exit 1; }

# Every target that talks to containers depends on this, so a missing engine
# produces an explanation instead of an empty command line.
require-engine:
	@./scripts/compose-command >/dev/null 2>&1 \
	    || { ./scripts/compose-command --explain; exit 1; }

# No --pull: the base image is pinned by digest, so there is nothing newer to
# fetch for a given ROS_BASE_DIGEST, and podman-compose translates --pull into
# a flag that Podman 3.x rejects.  Refresh the pin with `make digest` instead.
image: require-engine
	$(COMPOSE) build

# compose-up recreates the desktop when `make image` has produced a newer image,
# which podman-compose would otherwise silently skip.
up: require-engine
	@COMPOSE='$(COMPOSE)' ENGINE='$(ENGINE)' $(QUIET) ./scripts/compose-up
	@echo
	@echo 'The desktop is starting. Next:  make open'

# Waits for noVNC first: straight after `make up` the desktop is still starting,
# and opening early shows "failed to connect".  The instructions come after the
# browser opens, because only then is there anything to right-click.
open:
	@if command -v curl >/dev/null 2>&1; then \
	    i=0; until curl -fsS -o /dev/null --max-time 2 '$(URL)/vnc.html' 2>/dev/null; do \
	        i=$$((i + 1)); \
	        if [ "$$i" -eq 1 ]; then printf 'Waiting for the desktop to start'; fi; \
	        if [ "$$i" -ge 30 ]; then \
	            echo; echo 'The desktop did not answer after 60s. Is it running?  make up'; \
	            echo 'Details:  make logs'; exit 1; \
	        fi; \
	        printf '.'; sleep 2; \
	    done; \
	    [ "$$i" -gt 0 ] && echo; \
	fi; true
	@./scripts/open-url '$(DESKTOP_URL)'
	@echo
	@echo 'Two terminals, two jobs:'
	@echo '  - THIS terminal, on your computer: every make command.'
	@echo '      make turtlesim   then   make turtlesim-teleop'
	@echo '  - The terminal INSIDE the browser desktop: ROS commands'
	@echo '    (ros2, colcon, pkg). make does not work in there.'
	@echo
	@echo 'In the browser desktop:'
	@echo '  - Right-click the background for a menu: turtlesim_node,'
	@echo '    turtle_teleop_key, rqt, RViz.'
	@echo '  - To drive the turtle, click inside the white teleop window'
	@echo '    first, then use the arrow keys. Keys go to whichever window'
	@echo '    has focus.'
	@echo
	@echo 'About the browser page:'
	@echo '  - It may say "Disconnected" after sleep or a network blip. That is'
	@echo '    normal: it reconnects by itself within a few seconds, and'
	@echo '    everything in the desktop keeps running. Reloading works too.'
	@echo '  - The small tab on the left edge of the page opens a panel.'
	@echo '    Clipboard pastes text INTO the desktop, e.g. a command printed'
	@echo '    in this terminal. Extra keys sends Ctrl, Alt, Tab and Esc, which'
	@echo '    your browser would otherwise keep for itself.'

# A one-off container, so it works whether or not the desktop is running.
shell: require-engine
	@echo 'Entering a ROS shell. Type exit to come back.'
	@echo 'Not sure what to type? exit, then:  make shell examples'
	@echo
	$(COMPOSE) run --rm shell

turtlesim: require-engine
	$(DESKTOP_EXEC) 'nohup ros2 run turtlesim turtlesim_node >/tmp/turtlesim.log 2>&1 &'
	@echo 'turtlesim started on the browser desktop ($(URL)).'
	@echo
	@echo 'Next, to drive the turtle:  make turtlesim-teleop'
	@echo '  That opens a white window titled "turtlesim teleop (arrow keys)".'
	@echo '  1. Click inside that white window first. Keys only reach the'
	@echo '     window that has focus.'
	@echo '  2. Then press the arrow keys  ← ↑ ↓ →  before trying the letter'
	@echo '     keys: arrows drive and turn, letters snap to fixed headings.'

# Named for turtlesim on purpose: "teleop" alone reads as generic robot
# teleoperation, but turtle_teleop_key only ever drives turtlesim.  The colours
# are pinned because the instructions tell students to click "the white
# window"; xterm's default would otherwise depend on which X resources load.
turtlesim-teleop: require-engine
	$(DESKTOP_EXEC) "nohup xterm -title 'turtlesim teleop (arrow keys)' -bg white -fg black -u8 -fa 'DejaVu Sans Mono' -fs 11 -e bash -lc turtlesim-teleop >/tmp/teleop.log 2>&1 &"
	@echo 'turtlesim teleop opened on the browser desktop.'
	@echo
	@echo '  1. Click inside the WHITE window titled "turtlesim teleop (arrow'
	@echo '     keys)". Keys only reach the window that has focus: typing in'
	@echo '     the blue turtlesim window, or in this terminal, does nothing.'
	@echo '  2. Then press the arrow keys. Start there:'
	@echo
	@echo '                ↑             ↑  drive forward'
	@echo '            ←   ↓   →         ↓  back up'
	@echo '                              ←  turn left      →  turn right'
	@echo
	@echo '     The same picture is at the top of the white window.'
	@echo '     The lowercase letter keys (g b v c d e r t)'
	@echo '     snap the turtle to fixed headings, which makes more sense once'
	@echo '     you have driven it with the arrows. f cancels a turn; q quits.'

# The old name, kept only to point at the new one rather than failing with
# make's "No rule to make target".
teleop:
	@echo '`make teleop` is now `make turtlesim-teleop` -- it only drives turtlesim.'
	@exit 2

# --- Your own packages --------------------------------------------------------
# Thin wrappers over `pkg`, which prints each real command before running it:
# a student can see they could have typed `ros2 pkg create` or `colcon build`
# themselves.  See docs/creating-packages.md.

package: require-desktop
	@[ -n "$(PKG)" ] || { \
	    echo 'usage: make package PKG=name [TEMPLATE=pubsub|param] [PYTHON=1] [INTERFACES=1]'; \
	    echo 'e.g.   make package PKG=my_robot TEMPLATE=pubsub'; exit 2; }
	$(PKG_EXEC) 'pkg new $(PKG)$(if $(PYTHON), --python)$(if $(TEMPLATE), --template $(TEMPLATE))$(if $(INTERFACES), --interfaces)'

build: require-desktop
	$(PKG_EXEC) 'pkg build $(PKG)'

# Foreground, so Ctrl-C stops the node.  A TTY is requested only when there is
# one to give; without that check the engine refuses to run from scripts or CI.
run: require-desktop
	@[ -n "$(PKG)" ] && [ -n "$(NODE)" ] || { \
	    echo 'usage: make run PKG=name NODE=executable'; \
	    echo 'make build PKG=name  lists the executables it built.'; exit 2; }
	@if [ -t 0 ]; then tty=''; else tty='-T'; fi; \
	$(QUIET) $(COMPOSE) exec $$tty -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $(SERVICE) \
	    bash -lc 'pkg run $(PKG) $(NODE)'

test: require-desktop
	$(PKG_EXEC) 'pkg test $(PKG)'

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

# Everything reset removes, plus the images, for both the student's project and
# the self-test's.  Shows what it found, with sizes, and asks unless YES=1.
uninstall: require-engine
	@ENGINE='$(ENGINE)' YES='$(YES)' ./scripts/uninstall

# The workstation's own smoke suite, not the student's tests: builds the image,
# exercises every documented workflow, then removes its containers and volumes.
# It runs as a separate compose project on port 6081, so those are its OWN
# volumes -- safe to run while a student's desktop is up, with work in it.
selftest:
	./scripts/smoke-container

# Black-box tests for the host scripts: each one runs as a subprocess against
# fake executables on a throwaway PATH.  No engine, no containers, no network,
# so this deliberately does NOT depend on require-engine.
check:
	python3 -m unittest discover -s tests/host

lint: require-engine
	$(COMPOSE) config --quiet && echo 'compose config: ok'
	./scripts/lint-scripts

# Prints the multi-arch index digest for the configured distribution, for
# pasting into .env / compose.yaml as ROS_BASE_DIGEST.
digest:
	@if [ "$(ENGINE)" = 'docker' ] && docker buildx version >/dev/null 2>&1; then \
	    docker buildx imagetools inspect docker.io/library/ros:$(ROS_DISTRO)-ros-base \
	        | awk '/^Digest:/ {print $$2; found=1} END {if (!found) exit 1}'; \
	else \
	    ./scripts/base-image-digest $(ROS_DISTRO); \
	fi

endif  # topic-help mode, opened near the top of this file
