# ROS 2 turtlesim in a Guix container

This branch runs ROS 2 Jazzy and turtlesim as native Guix packages. It does not
use Docker, Podman, Ubuntu, or `apt`.

Versioning is controlled by three committed layers:

- `channels.scm` pins Guix and Nonguix by commit.
- The `vendor/guix-systole` git submodule pins the ROS package collection by
  commit without loading its unrelated channel dependencies.
- `manifest.scm` creates a small union of turtlesim and `ros2 run`; Systole
  pins turtlesim 1.8.3 and every source dependency by version, source commit,
  and hash.

The former OCI/Podman implementation remains available on the `podman` branch.

The environment package is a symlink union: Guix sees one ROS profile entry
instead of repeatedly traversing ROS's dense propagated-input graph. It
contains only turtlesim, `ros2 run`, and their runtime dependencies; the
launcher uses turtlesim's known executable paths.

## First build

```sh
make build
```

Most ROS packages currently lack binary substitutes, so the first build
compiles a substantial dependency graph. Guix caches successful results in
`/gnu/store`, making later runs cheap.

Initialize the pinned package checkout after cloning:

```sh
git submodule update --init
```

## Run

Start the graphical simulator and leave the terminal open:

```sh
make turtlesim
```

In a second terminal, start keyboard control:

```sh
make teleop
```

Use the arrow keys in the teleop terminal. Both isolated environments share
the host network namespace so ROS DDS discovery works between them.

For an interactive environment or to inspect exact channel revisions:

```sh
make shell
make describe
```

The launcher temporarily authorizes the current local user with XWayland and
revokes that authorization when the process exits.
