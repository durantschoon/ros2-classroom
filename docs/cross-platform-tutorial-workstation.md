# Cross-platform ROS tutorial workstation: implementation plan

> **Status: implemented.** This document is kept as the record of what was
> planned. Two things changed during implementation: this work became the
> default branch (the native Guix implementation moved to the `guix` branch),
> and Podman was added as a supported engine alongside Docker. Deviations from
> the plan are noted in the README and the docs it links.

## Objective

Build one Linux container image that works through Docker Desktop or Docker
Engine on Linux, macOS, and Windows. It must start with turtlesim already
installed, while also acting as a persistent ROS development workstation from
which a learner can install binary ROS packages or clone and build arbitrary
tutorial repositories.

The default graphical interface will be a desktop rendered inside the
container and exposed through noVNC at `http://localhost:6080`. This avoids
requiring XQuartz on macOS, an X server on Windows, or X11/Wayland socket
forwarding on Linux. The same documented startup command should work on every
host.

## Scope

The first implementation will provide:

- One multi-architecture Dockerfile for `linux/amd64` and `linux/arm64`.
- ROS 2 Lyrical by default, with the distribution supplied as a build argument.
- Turtlesim, `rqt`, RViz, the ROS CLI, rosdep, colcon, Git, compilers, and a
  small graphical desktop.
- A browser-accessible desktop and terminal.
- A non-root development user with passwordless sudo inside the disposable
  development container.
- Persistent source, build, install, log, and user configuration data.
- Helpers for installing additional binary packages and source dependencies.
- A Compose configuration and small Make interface with identical primary
  commands on all hosts.
- Automated smoke tests and a documented manual platform test matrix.

It will not promise that every hardware-oriented tutorial is portable.
Direct USB, serial, camera, GPU, multicast, and real-time access varies by
host. Those capabilities will be documented as optional extensions rather
than hidden in the base workflow.

## Proposed branch and relationship to existing work

Implementation should continue on a new branch created from this plan branch,
for example `docker/cross-platform-tutorials`. The existing `podman` branch is
a useful reference but should not be merged wholesale: its host-X11 and Linux
network assumptions are exactly what the browser desktop is intended to
remove. Native Guix work remains on `main` and is unaffected.

## Repository layout

The implementation is expected to add the following files:

```text
Dockerfile
compose.yaml
.dockerignore
.env.example
Makefile
docker/
  entrypoint.sh
  supervisord.conf
  desktop/
    openbox-autostart
    menu.xml
  scripts/
    install-ros-packages
    init-workspace
    tutorial
scripts/
  smoke-container
docs/
  cross-platform.md
  package-management.md
  hardware-and-gpu.md
```

Keep Docker-specific files at the repository root so `docker build .` and
`docker compose up` work without special context paths.

## Image design

### Base and versioning

Use an official OSRF ROS image rather than installing ROS repositories and
keys manually. Start with:

```dockerfile
ARG ROS_DISTRO=lyrical
FROM ros:${ROS_DISTRO}-ros-base
```

Before merging the implementation, pin the base by digest for reproducible
builds while retaining the human-readable tag in the `FROM` line. Dependabot
or a documented manual command can propose digest refreshes. Confirm that the
selected tag publishes both amd64 and arm64 manifests.

`ROS_DISTRO` remains a build argument, but only distributions verified by CI
are supported. Do not imply that changing the word to an arbitrary ROS release
will work when Ubuntu releases and package names differ.

### Installed packages

Install packages in a single apt layer with `--no-install-recommends`, then
delete `/var/lib/apt/lists`:

- `ros-${ROS_DISTRO}-turtlesim`
- `ros-${ROS_DISTRO}-rviz2`
- `ros-${ROS_DISTRO}-rqt`
- `ros-${ROS_DISTRO}-rqt-common-plugins`
- `python3-colcon-common-extensions`
- `python3-rosdep`
- `python3-vcstool`
- `build-essential`, `cmake`, `git`, `curl`, and `sudo`
- Openbox, a small terminal emulator, Xvfb, x11vnc, noVNC, websockify, and
  minimal fonts
- `supervisor` or an equally small process supervisor
- `tini` as PID 1 if it is not already supplied by the base

Avoid a full Ubuntu desktop and large recommended-package trees. Record image
size before and after the GUI layer so growth is intentional.

### Runtime user

Create a `ros` user in the image and run the desktop and tutorials as that
user. The user owns `/workspace` and its home directory. Passwordless sudo is
acceptable here because this is explicitly a local development environment,
not a production isolation boundary. State that security model in the README.

Host UID/GID mapping is not essential when source lives in named volumes. Add
optional `HOST_UID` and `HOST_GID` handling only if a bind-mounted workflow is
implemented and tested on Linux; Docker Desktop file sharing does not behave
identically.

### Entrypoint and environment

The entrypoint must:

1. Source `/opt/ros/$ROS_DISTRO/setup.bash`.
2. Source `/workspace/install/setup.bash` when present.
3. Initialize rosdep only when its system database is absent; tolerate an
   already-initialized database.
4. Create expected workspace directories with correct ownership.
5. Execute the requested command through `tini`, preserving signals and exit
   codes.

Put the sourcing logic in `/etc/bash.bashrc.d/ros-workspace.sh` as well, so
every interactive terminal has the same environment. Do not bake `source`
commands repeatedly into a mutable user `.bashrc`.

## Browser desktop

Supervisor should manage these long-running processes:

1. Xvfb on display `:1`, defaulting to 1600x900x24.
2. Openbox on that display.
3. x11vnc bound only inside the container.
4. websockify/noVNC listening on container port 6080.

The Openbox autostart file should open a terminal and may launch turtlesim on
first start. Prefer a desktop shortcut or menu item over forcing turtlesim to
restart whenever it exits.

Compose publishes noVNC to loopback only:

```yaml
ports:
  - "127.0.0.1:${NOVNC_PORT:-6080}:6080"
```

The default local environment may run without a VNC password because it is
loopback-bound. Documentation must require authentication or an SSH tunnel
before binding to a non-loopback address. Add a health check against the noVNC
HTTP endpoint.

## Persistent data

Use named volumes by default:

```yaml
volumes:
  ros-workspace:
  ros-home:
  ros-apt-cache:
```

Mount them as:

- `ros-workspace:/workspace`
- `ros-home:/home/ros`
- optionally `ros-apt-cache:/var/cache/apt`

The workspace volume preserves `src`, `build`, `install`, and `log`. The home
volume preserves shell history, rosdep metadata, and application settings.
Persisting APT's cache speeds reinstalls but does not preserve installed
packages, because a container replacement discards its writable layer.

Support two installation modes and explain the distinction:

1. **Exploratory:** `sudo apt install` in the running container. Quick, but
   lost after `docker compose down` followed by container recreation.
2. **Reproducible:** add packages to a build argument or package-list file and
   rebuild the image. This is the recommended way to retain them.

Do not mount the entire container root as a volume to preserve apt changes;
that makes upgrades and image reproducibility much harder to understand.

## Tutorial workflows

### Included turtlesim workflow

From the desktop terminal:

```sh
ros2 run turtlesim turtlesim_node
```

In a second terminal:

```sh
ros2 run turtlesim turtle_teleop_key
```

Both run in one container initially, avoiding cross-VM DDS discovery issues.
The image must also support separate Compose services on the same user-defined
network for tutorials that specifically teach distributed nodes.

### Installing binary packages

Provide `install-ros-packages` so users can write either short ROS package
names or full Debian package names:

```sh
install-ros-packages demo-nodes-cpp image-tools
```

The helper should update apt once, expand short names to
`ros-${ROS_DISTRO}-<name>`, install them, and print a reminder that an image
rebuild is required for permanent installation. It must not silently ignore
missing packages.

### Building source tutorials

The documented standard flow is:

```sh
cd /workspace/src
git clone URL
cd /workspace
rosdep install --from-paths src --ignore-src --rosdistro "$ROS_DISTRO" -r -y
colcon build --symlink-install
source install/setup.bash
```

`init-workspace` should create `/workspace/src` and a marker file but must not
overwrite existing work. A `tutorial` helper may provide named examples later,
but it should be a thin convenience layer rather than a hard-coded catalog
that prevents normal ROS commands.

## Compose services and networking

Start with two services from the same image:

- `desktop`: supervisor, Xvfb, noVNC, and the interactive desktop.
- `shell`: an on-demand interactive shell using the same named volumes and
  Compose network.

Set `ROS_DOMAIN_ID` through `.env`, with a documented default such as 42, so
the environment does not accidentally join unrelated ROS sessions. Set
`ROS_LOCALHOST_ONLY=0` within the Compose network.

Do not depend on `network_mode: host`: it behaves differently across native
Linux and Docker Desktop, and multicast discovery remains sensitive to host
and VPN configuration. Nodes in services on the same Compose bridge should be
the supported default. If DDS multicast proves unreliable, add a documented
CycloneDDS unicast configuration as a later compatibility option.

## Host interface

Expose a minimal, shell-portable Make interface:

```text
make build       Build the image for the current architecture
make up          Start the browser desktop
make open        Print/open http://localhost:6080
make shell       Enter a sourced ROS shell
make turtlesim   Launch turtlesim in the running desktop
make logs        Follow supervisor/container logs
make down        Stop containers without deleting volumes
make reset       Explicitly delete project containers and volumes
make test        Run automated smoke tests
```

`reset` is destructive and must print what it removes and require explicit
confirmation unless `YES=1` is supplied. Keep core commands as direct
`docker compose` operations so Windows users without Make can copy equivalent
commands from the README.

Do not automatically open a browser from the container. A host-side `make
open` can use `xdg-open`, `open`, or PowerShell when available, but printing
the URL is the universal fallback.

## Optional capabilities

Implement these only after the base matrix passes:

- **GPU acceleration:** a Linux/NVIDIA Compose override using the NVIDIA
  Container Toolkit. Retain software rendering as the portable default.
- **USB/serial:** Linux `devices` examples; explain that Docker Desktop places
  Linux containers inside a VM and may require USB/IP or platform tooling.
- **Host source bind mounts:** optional override for editor integration,
  including UID and filesystem-performance notes.
- **VS Code dev container:** point at the same Dockerfile and workspace rather
  than creating a second environment definition.
- **Simulation bundles:** separate image targets or Compose profiles for
  Gazebo, Nav2, and MoveIt so the default image stays approachable.

## Verification strategy

### Automated image tests

Run these in CI for both amd64 and arm64 where runners are available:

1. Build from a clean cache.
2. Assert the runtime user is non-root.
3. Assert `ROS_DISTRO`, `ros2`, `rosdep`, and `colcon` are available.
4. Assert `ros2 pkg executables turtlesim` lists both expected programs.
5. Start turtlesim under Xvfb and require it to remain alive for five seconds.
6. Start a talker and listener and verify messages cross between two Compose
   services.
7. Clone or copy a tiny example package, resolve dependencies, build it with
   colcon, and run it from the overlay.
8. Confirm the noVNC health endpoint responds.
9. Stop and recreate the container, then confirm a workspace file persists.
10. Run ShellCheck on scripts and validate the Compose configuration.

### Manual release matrix

Before calling the branch complete, test:

| Host | Architecture | Required checks |
|---|---|---|
| Linux Docker Engine | amd64 | Build, noVNC, turtlesim/teleop, persistence |
| Linux Docker Engine | arm64 | Build and headless ROS smoke tests |
| macOS Docker Desktop | Apple Silicon | Pull/build, noVNC input, persistence |
| macOS Docker Desktop | Intel, if available | Pull and basic startup |
| Windows Docker Desktop + WSL 2 | amd64 | PowerShell startup, noVNC input, persistence |

Record Docker version, available memory, image digest, and observed result.
Windows paths must be tested from both PowerShell documentation and a WSL
shell if both are advertised.

## Implementation sequence and acceptance criteria

### Phase 1: minimal image

- Add Dockerfile, entrypoint, non-root user, ROS tools, and turtlesim.
- Build on amd64 and run a headless turtlesim smoke test.
- Acceptance: turtlesim is installed and the image exits cleanly on signals.

### Phase 2: portable desktop

- Add Xvfb, Openbox, x11vnc, noVNC, supervisor, and loopback port publishing.
- Acceptance: a fresh user opens the browser and controls turtlesim without
  installing host GUI software.

### Phase 3: persistent tutorial workspace

- Add named volumes, sourcing, rosdep/colcon workflow, package helper, and
  documented reproducible package extension.
- Acceptance: a source package remains after container recreation and runs
  from the automatically sourced overlay.

### Phase 4: cross-platform hardening

- Test Apple Silicon and Windows/WSL 2, remove Linux-only assumptions, publish
  troubleshooting, and verify both architectures.
- Acceptance: `docker compose up --build` plus opening one URL is sufficient
  on each primary host platform.

### Phase 5: release hygiene

- Pin the base digest, add CI, vulnerability scanning, image labels, and an
  upgrade procedure.
- Acceptance: a clean checkout has repeatable build/test instructions and CI
  guards the promised workflows.

## Key risks and mitigations

- **Large image:** use a minimal window manager, no recommended packages, and
  optional heavyweight targets.
- **Software-rendered RViz performance:** document expectations; add optional
  Linux GPU support without making it the default.
- **DDS discovery differences:** keep beginner nodes in one container and test
  multi-service discovery on the Compose bridge.
- **Apple Silicon package gaps:** require arm64 image builds and make unsupported
  tutorial dependencies explicit rather than silently emulating amd64.
- **Mutable apt installs confuse persistence:** clearly separate exploratory
  installs from reproducible image extensions.
- **Exposed unauthenticated desktop:** bind to loopback by default and document
  authentication before any remote exposure.
- **Upstream tag drift:** pin image digests and update them deliberately.

## Definition of done

The implementation is complete when a new user on Linux, macOS, or Windows can
clone the repository, run the documented Docker Compose command, open a local
browser, immediately use turtlesim and teleop, install another ROS binary
package, clone and build a source tutorial in a persistent workspace, and
repeat the workflow after recreating the container. The automated tests and
manual matrix must demonstrate those claims without platform-specific X-server
setup.
