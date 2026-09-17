# Manual platform test matrix

CI covers amd64 end to end and arm64 as a build plus headless checks. The
browser desktop, keyboard input, and Docker Desktop's VM behaviour still need a
human on each host before the branch is called complete.

A row is only complete when a human has done the browser steps; an automated
`make test` pass covers steps 4-7 but cannot confirm that the desktop renders
or that the arrow keys move the turtle.

Record the result of each run below: Docker version, available memory, the
image digest (`docker image inspect --format '{{index .RepoDigests 0}}'` or the
build's `sha256`), and what you observed.

## Procedure per host

```sh
git clone <repo> && cd ros2_turtlesim
git checkout docker/cross-platform-tutorials
make build
make up
make open
```

1. **Desktop** — the noVNC page loads and shows an Openbox desktop with a
   terminal already open.
2. **turtlesim** — right-click → turtlesim_node; the window appears.
3. **teleop** — right-click → turtle_teleop_key, click that window, arrow keys
   move the turtle.
4. **Install** — `install-ros-packages demo-nodes-cpp` succeeds in the desktop
   terminal.
5. **Build** — `tutorial clone https://github.com/ros/ros_tutorials.git`,
   `tutorial deps`, `tutorial build` succeed.
6. **Persistence** — `make down && make up`, then confirm `/workspace/src` still
   has the clone and a new shell finds the built package.
7. **Shutdown** — `make down` stops cleanly within the grace period.

## Results

| Host | Arch | Docker | RAM | Image digest | Date | Result | Notes |
|---|---|---|---|---|---|---|---|
| Linux Docker Engine | amd64 | | | | | ☐ | |
| Linux Docker Engine | arm64 | | | | | ☐ | build + headless only |
| macOS Docker Desktop | Apple Silicon | | | | | ☐ | |
| macOS Docker Desktop | Intel | | | | | ☐ | if hardware available |
| Windows Docker Desktop (WSL 2) | amd64 | | | | | ☐ | test from PowerShell |
| Windows Docker Desktop (WSL 2) | amd64 | | | | | ☐ | test from a WSL shell |
| WSL 2 Ubuntu 22.04, rootless Podman | amd64 | podman 3.4.4 + podman-compose 1.6.0 | 15 GB | ros2-tutorials:lyrical (3.1 GB) | 2026-09-17 | automated ☑ / manual ☐ | `make test` 20/20; steps 1-3 below not human-verified |
| Linux rootless Podman | amd64 | | | | | ☐ | `make engine` shows podman |

Both Windows rows matter because the README advertises both entry points, and
the Podman row matters because the README advertises Podman as a fallback:
record the `podman-compose` version alongside the Docker version.
