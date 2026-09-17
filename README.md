# ROS 2 cross-platform tutorial workstation

One Docker image that runs ROS 2 tutorials on Linux, macOS, and Windows. The
graphical desktop is rendered inside the container and served to your browser
over noVNC, so no host X server, XQuartz, or socket forwarding is involved.

turtlesim is installed and ready; the same container is a persistent ROS
development workstation where you can install more packages or clone and build
tutorial repositories.

Docker and rootless Podman both work; the Make targets detect whichever is
installed, preferring Docker. Run `make doctor` to check your host, and see
[docs/host-requirements.md](docs/host-requirements.md) — with older Podman you
also need `pip install --user -r requirements-host.txt`.

## Quick start

```sh
make build     # first time; downloads and builds the image
make up        # start the desktop
make open      # open http://localhost:6080 (or just open it yourself)
```

`make engine` prints which container engine was detected, or explains what is
missing if none was.

Then, in the browser desktop:

- right-click the background → **turtlesim_node**
- right-click again → **turtle_teleop_key**, click that window, and use the
  arrow keys.

Without Make (for example on Windows PowerShell; substitute `podman compose`
for `docker compose` if that is what you have):

```powershell
docker compose build
docker compose up -d
# browse to http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

## Commands

| Command | What it does |
|---|---|
| `make build` | Build the image for the current architecture |
| `make up` | Start the browser desktop |
| `make open` | Open, or print, the desktop URL |
| `make shell` | A sourced ROS shell in a throwaway container |
| `make turtlesim` | Launch turtlesim on the running desktop |
| `make teleop` | Launch keyboard teleop on the running desktop |
| `make logs` | Follow container logs |
| `make down` | Stop containers, keep your work |
| `make reset` | Delete containers **and volumes** (asks first) |
| `make test` | Run the automated smoke tests |
| `make lint` | Validate the compose file and shell scripts |
| `make digest` | Print the base-image digest to pin in `.env` |
| `make engine` | Show which container engine was detected |
| `make doctor` | Check host prerequisites and how to fix them |

## What is in the image

ROS 2 Lyrical Luth (`ros:lyrical-ros-base`, pinned by digest) plus turtlesim,
`rqt`, RViz 2, rosdep, colcon, vcstool, a C++ toolchain, git, and a small
Openbox desktop driven by Xvfb, x11vnc, and noVNC under supervisor.

The container runs as the non-root user `ros`, which has passwordless `sudo`:
this is a development environment, not a security sandbox.

## What persists

`/workspace` and `/home/ros` are named volumes, so cloned sources, colcon
builds, shell history, and tool settings survive `make down` and image rebuilds.
Packages installed with `apt` inside a running container do **not** — see
[docs/package-management.md](docs/package-management.md) for the two supported
installation modes.

## Configuration

Copy `.env.example` to `.env` to change the ROS distribution, published port,
screen size, `ROS_DOMAIN_ID`, VNC password, or the extra packages baked into the
image. Every value has a working default, so `.env` is optional.

Changing `ROS_DISTRO` also requires the matching base digest
(`make digest ROS_DISTRO=<name>`), and only distributions covered by CI are
supported.

## Documentation

- [Host requirements and how to check them](docs/host-requirements.md)
- [Cross-platform notes, security model, and troubleshooting](docs/cross-platform.md)
- [Installing packages and building source tutorials](docs/package-management.md)
- [GPU, USB, cameras, and other optional extensions](docs/hardware-and-gpu.md)
- [The implementation plan this branch follows](docs/cross-platform-tutorial-workstation.md)
- [Why the distribution choice differs from `main`](docs/ros-distributions.md)

## Related branches

This is the default branch because it is the one that works on any laptop with
a container engine. The other branches are more specialised:

- `guix` — ROS 2 Jazzy built as native Guix packages, with every source and
  toolchain input pinned by hash. No containers, no `apt`; Guix only. Stronger
  reproducibility, much narrower audience.
- `podman` — an earlier Ubuntu/Podman image that forwards the host X11 socket.
  Linux-only, superseded by this branch.
