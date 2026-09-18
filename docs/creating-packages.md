# Creating packages

`pkg` is a thin wrapper around `ros2 pkg create` and `colcon` that fills in
the parts of a new ROS 2 package that are the same every time: a working
publisher/subscriber or parameter node, the CMake or `setup.py` wiring to
build it, and (for messages) the rosidl plumbing. Every underlying command it
runs is echoed with a `+` prefix, so you can see exactly what it did and stop
using the helper whenever you like — it produces an ordinary package, not
something that depends on itself.

```sh
pkg new my_bot --template pubsub --build
```

## The two build types

ROS 2 packages are either `ament_cmake` (C++) or `ament_python`. `pkg new`
defaults to `ament_cmake`; pass `--python` for the other:

```sh
pkg new my_bot           --template pubsub --build   # C++
pkg new my_bot_py --python --template pubsub --build  # Python
```

Both produce a talker and a listener that actually publish and subscribe on
`/chatter`, plus a launch file that starts both:

```sh
ros2 run my_bot talker      # in one shell
ros2 run my_bot listener    # in another
ros2 launch my_bot demo.launch.py   # or both at once
```

## Templates

`--template pubsub` and `--template param` are the two starting points:

- **pubsub** — a publisher and a subscriber talking over `std_msgs/String`,
  plus a launch file. This is the "hello world" of ROS 2 nodes and the
  fastest way to confirm two processes can actually reach each other over
  DDS.
- **param** — a single node with one declared parameter (`greeting`), so you
  can see the declare/get/set cycle:

  ```sh
  ros2 run my_bot_param param_node
  ros2 param list
  ros2 param set /param_node greeting "good evening"
  ```

  Declaring a parameter (`declare_parameter`) is what makes it visible to
  `ros2 param` at all — a plain member variable would not show up.

Leave `--template` off for an empty package from `ros2 pkg create`, with
nothing added.

## Custom interfaces, and why they need their own package

`pkg new my_bot_msgs --interfaces --build` creates a package with a custom
message (`msg/Temperature.msg`) and a custom service
(`srv/AddTwoInts.srv`), wired into `rosidl_generate_interfaces()` in
CMakeLists.txt and the matching `<buildtool_depend>`/`<depend>`/
`<exec_depend>`/`<member_of_group>` elements in package.xml.

Interface packages are `ament_cmake` even when everything that *uses* them is
Python: `rosidl` generates the message/service bindings during the CMake
build, and there is no `ament_python` equivalent. That is also why
`--interfaces` and `--template` are mutually exclusive here — a package
either declares interfaces or contains node code, not both. In a larger
project this is standard practice anyway (`my_robot_msgs` alongside
`my_robot`), because it lets other packages depend on the messages without
pulling in your node implementation.

Two things about package.xml are easy to get wrong by hand and are exactly
what `--interfaces` gets right:

1. The package_format3 schema requires `<export>` to be the **last** child
   of `<package>`. `ros2 pkg create` always emits an `<export>` block (it
   records the build type), so any dependency you add afterwards has to be
   inserted *before* it, not appended at the end of the file — appending
   after `<export>` builds fine with colcon but fails `ament_xmllint`.
2. `ros2 pkg create --dependencies builtin_interfaces` and `rosidl`'s own
   `<depend>`/`<buildtool_depend>`/`<exec_depend>` split both want to
   declare the same package; declaring it both ways trips catkin_pkg's
   "redundant dependency" check. `pkg new --interfaces` only emits the
   specific set rosidl actually needs.

Verify a new interface package with `ros2 interface show`, not just a build:

```sh
ros2 interface show my_bot_msgs/msg/Temperature
ros2 interface show my_bot_msgs/srv/AddTwoInts
```

A green `colcon build` only proves the `.msg`/`.srv` files parsed; it does
not prove another package can find the generated type.

## The build/test loop

```sh
pkg build my_bot          # colcon build --symlink-install --packages-select my_bot
pkg build                 # everything in the workspace
pkg test my_bot           # colcon test, then the real verdict
pkg list                  # colcon list --names-only
```

`--symlink-install` is what `pkg build` always uses, so editing a Python node
or a launch file and re-running `ros2 run`/`ros2 launch` picks up the change
without a rebuild. C++ sources still need a rebuild.

## Why `colcon test` alone is misleading

`colcon test` exits `0` even when every test inside a package failed — it
only reports whether the *test runner itself* crashed, not whether the tests
passed. The actual pass/fail verdict lives in `colcon test-result`, which
reads the xunit files colcon just wrote. `pkg test` runs both, in order, and
labels the second one so the distinction stays visible:

```
+ colcon test --packages-select my_bot
Finished <<< my_bot [1.2s]	[ with test failures ]

colcon test always exits 0; the real verdict comes from test-result:
+ colcon test-result --verbose
...
Summary: 6 tests, 0 errors, 1 failure, 0 skipped
```

If you only ever ran `colcon test` and checked `$?`, this package would look
like a pass.

Every package `pkg new` generates — `ament_cmake` or `ament_python`, with or
without a template — is expected to *pass* its default `ament_lint_auto`
tests out of the box: cpplint/cppcheck/uncrustify and xmllint for C++,
flake8/pep257/xmllint for Python. `python3-flake8`,
`python3-pytest-cov`, `python3-pytest-repeat`, `python3-pytest-rerunfailures`,
and `clang-format` are in the image specifically so those tests can run and
pass rather than error out for lack of a tool. If `pkg test` reports a
failure on a freshly generated package, that is a bug in the template, not
something to route around — the templates in `docker/templates/` are meant
to model code that is actually clean by the project's own lint tests, not
just code that happens to compile.

## Adding dependencies

`--deps "pkg_a pkg_b"` adds extra ROS or system dependencies to package.xml
(and to the `--dependencies` list passed to `ros2 pkg create`) at creation
time. To add one later, edit package.xml by hand and then resolve it the
normal way:

```sh
rosdep install --from-paths src --ignore-src --rosdistro "$ROS_DISTRO" -r -y
```

`rosdep` reads every package.xml under `src/`, maps each `<depend>` to the
distribution's package name, and installs whatever is missing — the same
step [package-management.md](package-management.md) uses for cloned source
tutorials. It is safe to run repeatedly; already-installed dependencies are
skipped.

## What's persistent

Packages created with `pkg new` live under `/workspace/src`, in the
`ros-workspace` volume, so they survive `docker compose stop`/`start` and
container recreation the same way anything else in `/workspace` does — see
[package-management.md](package-management.md#what-is-persistent) for the
full picture of what is and is not.
