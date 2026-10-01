# ROS 2 distributions

This branch offers four ROS 2 distributions from one table, `distros.json`.
The `guix` branch makes a different choice, for reasons explained at the end.

## The table

`make distros` (or `.\ros2.ps1 distros`) prints it:

```
DISTRO   UBUNTU  PORT  IMAGE TAG  COMPOSE PROJECT
humble   22.04   6082  humble     ros2-tutorials-humble
jazzy    24.04   6083  jazzy      ros2-tutorials-jazzy
kilted   24.04   6084  kilted     ros2-tutorials-kilted
lyrical  26.04   6080  latest     ros2-tutorials         (default)
```

Each entry pairs a distribution with the Ubuntu release its official image is
built on, a noVNC host port of its own, and the digest of
`docker.io/library/ros:<distro>-ros-base`, the multi-architecture image its
workstation image builds `FROM`. `ROS_DISTRO=<name>` chooses one, on the
command line (`make up ROS_DISTRO=jazzy`), in the environment, or in `.env`;
make and `ros2.ps1` then resolve it to the digest, the image tag, the compose
project, and the port. Because each distribution is its own compose project,
it has its own `/workspace` and `/home/ros` volumes: switching never touches
another distribution's work, and several desktops can run at once. Port 6081
is left to `make selftest`.

Plain `docker compose`, without make or `ros2.ps1`, needs the same resolution
first: `eval "$(./scripts/distros env)" && docker compose up -d`.

## Why these four

All four are installed from the official `packages.ros.org` apt repository
through the official `ros` images, on both amd64 and arm64, so nothing has to
be ported:

- **lyrical** (Lyrical Luth, Ubuntu 26.04): the newest release and an LTS,
  supported through May 2031.
- **kilted** (Kilted Kaiju, Ubuntu 24.04): the previous, non-LTS release, for
  courses that started on it.
- **jazzy** (Jazzy Jalisco, Ubuntu 24.04): the previous LTS, supported through
  May 2029, and widely used by current tutorials and courses.
- **humble** (Humble Hawksbill, Ubuntu 22.04): the oldest LTS still supported,
  through May 2027, still common in courses and on robots.

## The default: lyrical

The default is the newest LTS, so a class that does not choose gets the
release supported longest. It keeps the names the workstation had before there
was a choice: image tag `:latest`, compose project `ros2-tutorials`, port 6080.
A student who never sets `ROS_DISTRO` sees no difference, and their existing
`/workspace` is the default's.

## Published images

CI publishes every distribution to `ghcr.io/durantschoon/ros2-classroom` after
the tests pass on `main`: `:humble`, `:jazzy`, `:kilted`, `:lyrical`, and
`:latest` for the default, each for linux/amd64 and linux/arm64. Choosing a
non-default distribution is therefore a download, as the default always was;
`make image ROS_DISTRO=<name>` still builds one locally. The default is
smoke-tested on every push; all four are smoke-tested nightly.

## Refreshing the digests

The base images are pinned by digest, so nothing changes under a student until
the table does. To pick up new base images (security fixes, a sync of the ROS
apt repository):

```sh
make digest
```

It fetches the current digest of every `ros:<distro>-ros-base`, prints which
changed, rewrites `distros.json` only if one did, and names the
`make image ROS_DISTRO=<name>` to rebuild each changed one. If the default's
digest changed, also update its copies in the `Dockerfile` (`ARG
ROS_BASE_DIGEST`) and `compose.yaml` (`${ROS_BASE_DIGEST:-…}`); `make check`
fails until they match.

The table always wins over an old `.env`: make and `ros2.ps1` pass the
table's digest unless `ROS_BASE_DIGEST` is set on the command line or in the
environment.

A digest pins the base layers, not the apt layer above them, which resolves
against a moving repository. That is a weaker reproducibility guarantee than
the `guix` branch's, and the right trade for a tutorial environment.

## The `guix` branch: Jazzy

That branch uses ROS 2 Jazzy Jalisco. It is an LTS release supported through
May 2029, is newer than Humble, and is the ROS distribution packaged by the
pinned SystoleOS Guix source. For turtlesim, Jazzy provides the familiar ROS 2
tutorial workflow while keeping every source and toolchain input under Guix.

### Why that branch cannot simply move to Lyrical

ROS 2 Lyrical Luth is the latest ROS 2 release as of September 2026 and is an
LTS supported through May 2031. The pinned SystoleOS checkout does not package
Lyrical, however. A name change in `manifest.scm` cannot supply it: the ROS
packages, dependency versions, patches, source commits, hashes, and build
results must first be ported and tested in Guix.

Moving that branch to Lyrical should therefore be a deliberate packaging
upgrade:

1. Add a Lyrical distribution definition and package set to SystoleOS.
2. Port the minimal turtlesim and `ros2 run` dependency closure.
3. Build it with the pinned Guix channels and run the headless smoke test.
4. Test two graphical containers for DDS discovery and keyboard control.
5. Update the SystoleOS submodule pin and this manifest in one reviewable
   dependency-upgrade commit.

Until that work exists upstream or is completed locally, Jazzy is the newest
native Guix option available there.

### Why the two branches disagree

They answer different questions. The `guix` branch asks "what can be built
reproducibly from source under Guix?" This branch asks "what can a learner run
on any laptop today?"
