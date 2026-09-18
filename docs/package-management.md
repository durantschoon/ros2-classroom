# Installing packages

There are two ways to add software, and the difference matters because a
container's writable layer is not persistent storage.

## 1. Exploratory: install into the running container

```sh
install-ros-packages demo-nodes-cpp image-tools   # ROS short names
install-ros-packages python3-pytest gdb           # plain Ubuntu packages
```

The helper updates apt once, expands ROS short names to
`ros-$ROS_DISTRO-<name>` (underscores become hyphens), and fails loudly if a
package does not exist.

These packages live in the container's writable layer. They survive
`docker compose stop` / `start`, but they are discarded whenever the container
is recreated — `docker compose down`, `up --force-recreate`, or any image
rebuild.

## 2. Reproducible: bake them into the image

Add them to `.env`:

```sh
EXTRA_ROS_PACKAGES=demo-nodes-cpp image-tools
EXTRA_APT_PACKAGES=python3-pytest gdb
```

Then rebuild:

```sh
make build
make up
```

This is the recommended way to keep anything you rely on. The package list is
committed with the rest of the configuration, so a colleague who clones the
repository gets the same environment.

## Why not persist the whole root filesystem?

Mounting a volume over `/` (or over `/usr`, `/opt/ros`, and friends) would make
apt changes survive, and would also make the image meaningless: upgrades would
merge unpredictably with whatever the volume happened to contain, and no two
machines would agree on what "the environment" is. The image is the
reproducible part; volumes hold *your* work.

## What is persistent

| Path | Volume | Contents |
|---|---|---|
| `/workspace` | `ros-workspace` | `src/`, `build/`, `install/`, `log/` |
| `/home/ros` | `ros-home` | shell history, rosdep cache, RViz/rqt settings |

Everything else belongs to the image.

## Building source tutorials

The standard ROS flow works unchanged:

```sh
cd /workspace/src
git clone https://github.com/ros/ros_tutorials.git -b $ROS_DISTRO
cd /workspace
rosdep install --from-paths src --ignore-src --rosdistro "$ROS_DISTRO" -r -y
colcon build --symlink-install
source install/setup.bash
```

The `tutorial` helper wraps those four steps and echoes each command it runs, so
the underlying workflow stays visible:

```sh
tutorial clone https://github.com/ros/ros_tutorials.git
tutorial deps
tutorial build
tutorial list
```

New shells source `/workspace/install/setup.bash` automatically once it exists,
so a rebuilt package is available in the next terminal without extra steps.

`init-workspace` creates `/workspace/src` and a marker file. It never overwrites
existing work; running it twice is harmless.

## Creating your own packages

For starting a new package from scratch — templates, custom interfaces, and
the build/test loop — see [creating-packages.md](creating-packages.md).
