# ros2-classroom: a ROS 2 tutorial workstation for a room of mixed laptops

Built for teaching: every student gets the same ROS 2 desktop in their browser,
whatever they brought, with nothing to install but a container engine.
`make doctor` says what a machine is missing and how to fix it, `make selftest`
proves the workstation works before class does, and `make uninstall` gives the
disk space back afterwards.

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
make image     # first time; downloads and builds the image
make up        # start the desktop
make open      # open http://localhost:6080 (or just open it yourself)
```

`make engine` prints which container engine was detected, or explains what is
missing if none was.

**Two terminals, two jobs.** Every `make` command runs in a terminal on your own
computer — the one where you typed `make up`. The terminal that opens *inside*
the browser desktop is for ROS commands (`ros2`, `colcon`, `pkg`); `make`
targets don't work in there, and it will tell you so if you try.

**If the page says "Disconnected"**, that's normal after sleep or a network
blip — it reconnects by itself and nothing in the desktop stops. The small tab
on the page's left edge opens a panel whose **Clipboard** button puts text
into the desktop; press **Ctrl+Shift+V** in a desktop terminal to paste it
(Ctrl, not Cmd, on a Mac).

Once turtlesim runs, move on to your own code:

```sh
make package PKG=my_robot TEMPLATE=pubsub   # prints the ros2 pkg create it runs
make build PKG=my_robot                     # prints the colcon build it runs
make run PKG=my_robot NODE=talker           # Ctrl-C to stop
make test PKG=my_robot
```

Several targets explain themselves: `make shell help`, `make package examples`,
and likewise for `build`, `run`, and `test`. `make help` shows those targets in
bold. The examples are real ROS commands, each one run against this image.

Each prints the real command before running it, so you can see what you would
have typed on a native ROS install — see
[docs/creating-packages.md](docs/creating-packages.md).

Then, in the browser desktop:

- right-click the background → **turtlesim_node**
- right-click again → **turtle_teleop_key**, click that window, and use the
  arrow keys.

**On Windows:** Double-click `ros2.bat` to launch the desktop and open the browser automatically. 
To run commands from PowerShell, use `.\ros2.ps1`:

```powershell
.\ros2.ps1 package -Pkg my_robot -Template pubsub
.\ros2.ps1 build -Pkg my_robot
.\ros2.ps1 run -Pkg my_robot -Node talker
.\ros2.ps1 test -Pkg my_robot
```

## Commands

| Command | What it does |
|---|---|
| `make image` | Build the image for the current architecture |
| `make up` | Start the browser desktop |
| `make open` | Open, or print, the desktop URL |
| `make shell` | A sourced ROS shell in a throwaway container |
| `make <target> help` | What `shell`, `package`, `build`, `run` or `test` does, its options, what it runs |
| `make <target> examples` | Things to try with that target, ready to copy |
| `make turtlesim` | Launch turtlesim on the running desktop |
| `make turtlesim-teleop` | Drive turtlesim with the arrow keys (turtlesim only) |
| `make logs` | Follow container logs |
| `make down` | Stop containers, keep your work |
| `make reset` | Delete containers **and volumes** (asks first) |
| `make uninstall` | Delete all of that **and the images**, freeing the disk (asks first) |
| `make selftest` | Check the workstation itself with the automated smoke tests |
| `make package PKG=name` | Create a ROS package, optionally from a template |
| `make build [PKG=name]` | `colcon build` your packages |
| `make run PKG=name NODE=exe` | `ros2 run` a node in the foreground |
| `make test [PKG=name]` | Run your packages' tests and report the real verdict |
| `make check` | Fast tests for the host scripts (seconds, no containers) |
| `make lint` | Validate compose.yaml and lint every script (shellcheck, Python 3.9) |
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
- [Creating your own packages, templates, and custom interfaces](docs/creating-packages.md)
- [GPU, USB, cameras, and other optional extensions](docs/hardware-and-gpu.md)
- [Purpose and roadmap: why this exists and what comes next](docs/roadmap.md)
- [Platform test checklist](docs/platform-test-matrix.md)
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
