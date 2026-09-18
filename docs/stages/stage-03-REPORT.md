# Stage 03 — Port the container scripts to Python (REPORT)

Branch: `stage-03-port-container-scripts`. Base: `python-port` at `fac72a9`.

## 1. Checklist echo

### The change

| Item | Status |
|---|---|
| `docker/scripts/pkg` ported to Python | done |
| `docker/scripts/tutorial` ported to Python | done |
| `docker/scripts/init-workspace` ported to Python | done |
| `docker/scripts/install-ros-packages` ported to Python | done |
| Same file names, no `.py` extension | done |
| `#!/usr/bin/env python3` | done |
| Executable bit kept (`100755` on all four) | done |
| Dockerfile, Makefile, docs, suite unchanged | done — nothing outside the allow-list is touched |
| Stdlib only, no pip step | done — `enum`, `os`, `re`, `shlex`, `subprocess`, `sys`, `pathlib`, `datetime`, `typing` |
| `+ <command>` echo to **stderr**, before the command, paste-safe | done (`shlex.join`) |
| Every message and its stream preserved | done — verified byte for byte, see §5 |
| Usage errors exit 2; refusals exit 1; tool status propagates | done |
| `PKG_VIA_MAKE=1` switches the `next:` hints | done, both branches exercised in §3 |
| `pkg run` replaces the process (`os.execvp`) | done |
| `pkg test` = `colcon test` (tolerated) then `colcon test-result --verbose`, returning *that* status | done, proven in §3 Test 4 |
| `pkg build <one>` lists executables via `bash -c` with paths as **arguments** | done, `list_executables()` |
| `pkg new` on an existing package refused by `ros2 pkg create` itself, no extra existence check | done — selftest checks both the refusal and byte-identity |
| `init-workspace` never overwrites the marker; both messages pinned | done, marker bytes identical (§5) |
| `install-ros-packages` name-resolution rule kept; missing package fails loudly | done |
| Enums for build types, templates, subcommands; parsed once at the entry point | done — `BuildType`, `Template`, `Command`, `parse_new()` |
| The three file patchers are pure text→text | done — `cmake_insert`, `xml_insert`, `setup_py_patch` |
| Every command an argv list; no `shell=True`, no `os.system` | done, grep clean |
| Paths are `pathlib.Path` | done |
| Expected failures are a message + status, never a traceback | done — missing tool, closed pipe, missing workspace (§3) |
| Each script self-contained, no shared module | done |
| No test changes, no template changes | done — diff touches only the four scripts and this report |

### Definition of Done

| Item | Result |
|---|---|
| Baseline `make lint`, `make check`, `make selftest` on the unmodified base | pass / pass / **45 passed, 0 failed** |
| Final `make lint` passes, all four classified `python, container` | pass |
| Final `make check` passes unchanged (104 tests) | pass |
| Final `make selftest` same count and same check names | **45 passed, 0 failed**, set difference empty |
| Tests 1–8 pass, output in the report | §3 |
| `grep -rn "shell=True\|os.system" docker/scripts/` finds nothing | exit 1 (no match) |
| `git diff python-port --stat` shows only allowed files | §6 |

## 2. Gates, baseline vs final

All runs used `export PATH="$HOME/.local/bin:$PATH"` and, for the self-test,
exactly the isolated command from the prompt:

```sh
SELFTEST_PROJECT=ros2-tutorials-st03 SELFTEST_NOVNC_PORT=6083 \
  SELFTEST_ROS_DOMAIN_ID=83 IMAGE_NAME=ros2-tutorials-st03 make selftest
```

### `make lint`

Baseline (exit 0) — the four scripts are shell, and only *advisory*:

```
ok       docker/scripts/init-workspace         shell, advisory
ok       docker/scripts/install-ros-packages   shell, advisory
ok       docker/scripts/pkg                    shell, advisory
ok       docker/scripts/turtlesim-teleop       python, container
ok       docker/scripts/tutorial               shell, advisory
lint-scripts: 25 files: 25 ok, 0 advisory, 0 FAIL
```

Final (exit 0) — all four are now `python, container`:

```
ok       docker/scripts/init-workspace         python, container
ok       docker/scripts/install-ros-packages   python, container
ok       docker/scripts/pkg                    python, container
ok       docker/scripts/turtlesim-teleop       python, container
ok       docker/scripts/tutorial               python, container
lint-scripts: 25 files: 25 ok, 0 advisory, 0 FAIL
```

The file count is unchanged at 25; no file moved between categories except the
four intended ones.

### `make check`

Baseline (exit 0):

```
python3 -m unittest discover -s tests/host
.............................................................ssss.......................................
----------------------------------------------------------------------
Ran 104 tests in 4.027s

OK (skipped=4)
```

Final (exit 0):

```
python3 -m unittest discover -s tests/host
.............................................................ssss.......................................
----------------------------------------------------------------------
Ran 104 tests in 4.404s

OK (skipped=4)
```

Identical: 104 tests, 4 skipped, 0 failures. These are stage 04's host-script
tests; this stage touches nothing they cover, and they are unchanged.

### `make selftest` (isolated)

Baseline:

```
== Result
45 passed, 0 failed
```

Final:

```
== Result
45 passed, 0 failed
```

Both exited 0.

### Check names, baseline vs final, and their set difference

45 names in each run. `diff baseline-names final-names` is **empty**: the same
45 names, in the same order, all PASS in both. The set difference in both
directions is therefore empty — no check was added, removed, renamed, or
skipped.

```
image builds
desktop container accepts commands
the image defaults to the non-root ros user
desktop programs run as the non-root ros user
ROS_DISTRO is set
the self-test runs in its own ROS domain, not the student default
ros2 is on PATH
rosdep is on PATH
colcon is on PATH
turtlesim_node and turtle_teleop_key are installed
turtlesim stays alive for 5s on the virtual display
noVNC answers inside the container
noVNC answers on the host at http://localhost:6083
a node in one service receives messages from another service
install-ros-packages installs a ROS short name
installed package is runnable
install-ros-packages fails loudly on a missing package
colcon builds a source package in the persistent workspace
new shells source the workspace overlay automatically
pkg new --template pubsub builds
templated package registers its talker executable
templated pubsub node actually publishes on /chatter
pkg new --interfaces builds
ros2 interface show works for a generated message
ros2 interface show works for a generated service
pkg test reports a clean lint result for a generated package
make package prints the real command and points at make build
printed commands quote arguments so they paste correctly
make build prints colcon build and points at make run
make test reports the real colcon test-result verdict
make typed inside the container explains where to run it
a second init-workspace reports the workspace is already initialized
init-workspace leaves the existing workspace marker untouched
tutorial with no arguments exits 2 and prints usage
tutorial clone echoes the real git command and succeeds
the clone lands in /workspace/src
tutorial list names the cloned repository
tutorial build echoes colcon build --packages-select and succeeds
pkg with no arguments exits 2 and prints usage
pkg new --python --interfaces is refused with an explanation
the refused interface package was never created
pkg new refuses to create a package that already exists
the existing package is byte-identical after the refusal
workspace source survives container recreation
built overlay survives container recreation
```

(The exact list above is the final run's; the baseline's is byte-identical.)

## 3. Tests 1–8

Run in throwaway containers built from the stage image:

```sh
podman run -i --rm -e WORKSPACE=/tmp/ws -e ROS_DOMAIN_ID=183 \
  --entrypoint /bin/bash localhost/ros2-tutorials-st03:lyrical -ls < script
```

The image ships **Python 3.14.4**.

### Test 1 — all six creation modes build

```
===== TEST 1: all six creation modes build =====
PASS  pkg new t_cpp_pubsub --template pubsub --build   (exit 0)
PASS  pkg new t_cpp_param --template param --build   (exit 0)
PASS  pkg new t_py_pubsub --python --template pubsub --build   (exit 0)
PASS  pkg new t_py_param --python --template param --build   (exit 0)
PASS  pkg new t_msgs --interfaces --build   (exit 0)
PASS  pkg new t_plain --build   (exit 0)

----- executables registered -----
  t_cpp_pubsub: t_cpp_pubsub listener t_cpp_pubsub talker
  t_cpp_param: t_cpp_param param_node
  t_py_pubsub: t_py_pubsub listener t_py_pubsub talker
  t_py_param: t_py_param param_node
  t_msgs interfaces:
    # A reading from one sensor.
    #
    # Field types are listed at
    # https://docs.ros.org/en/rolling/Concepts/Basic/About-Interfaces.html
    string sensor_name
    # Request fields go above the ---, response fields below it.
    int64 a
    int64 b
    ---
    int64 sum
```

The `pkg build` tail, both hint branches:

```
--- plain (PKG_VIA_MAKE unset):

built; open a new shell, or: source /tmp/ws/install/setup.bash
executables in t_cpp_pubsub:
  t_cpp_pubsub listener
  t_cpp_pubsub talker
next: pkg run t_cpp_pubsub <executable>
--- via make (PKG_VIA_MAKE=1):

built; open a new shell, or: source /tmp/ws/install/setup.bash
executables in t_cpp_pubsub:
  t_cpp_pubsub listener
  t_cpp_pubsub talker
next: make run PKG=t_cpp_pubsub NODE=<executable>
```

This is the `bash -c 'source … && ros2 pkg executables …'` path, with the setup
path and package name passed as **arguments** (`["bash", "-c", script, "bash",
str(setup), package]`), not interpolated into the script text.

### Test 2 — the printed `ros2 pkg create` line pastes back

```
===== TEST 2: printed ros2 pkg create line pastes back =====
printed line: ros2 pkg create paste_demo --build-type ament_cmake --license Apache-2.0 --destination-directory /tmp/ws/src --maintainer-name 'ROS Developer' --maintainer-email dev@example.com --dependencies rclcpp std_msgs

going to create a new package
package name: paste_demo
destination directory: /tmp/ws/src
package format: 3
version: 0.0.0
description: TODO: Package description
maintainer: ['ROS Developer <dev@example.com>']
licenses: ['Apache-2.0']
build type: ament_cmake
dependencies: ['rclcpp', 'std_msgs']
creating folder /tmp/ws/src/paste_demo
creating /tmp/ws/src/paste_demo/package.xml
creating source and include folder
creating folder /tmp/ws/src/paste_demo/src
creating folder /tmp/ws/src/paste_demo/include/paste_demo
creating /tmp/ws/src/paste_demo/CMakeLists.txt
paste exit=0
PACKAGE.XML IDENTICAL
```

The helper's package was moved aside first, because the printed line names an
absolute `--destination-directory`; the line was then pasted verbatim into a
shell and `diff` on `package.xml` found no difference.

### Test 3 — `pkg test` on a C++ and a Python template package

```
===== TEST 3 (networked): pkg test on a C++ and a Python template =====
pkg test n_cpp: exit=0
    Summary: 14 tests, 0 errors, 0 failures, 2 skipped
pkg test n_py: exit=0
    Summary: 19 tests, 0 errors, 0 failures, 3 skipped
```

### Test 4 — a deliberately broken template file must fail

Two lines appended to the generated `talker.py` (`import os,sys` and
`BROKEN=1`), which flake8 rejects:

```
===== TEST 4 (networked): break a template file, pkg test must fail =====
pkg test n_py after breaking talker.py: exit=1
    Summary: 19 tests, 0 errors, 1 failure, 3 skipped
    - n_py.test.test_flake8 test_flake8
          ./n_py/talker.py:43:10: E401 multiple imports on one line
          ./n_py/talker.py:44:7: E225 missing whitespace around operator
PASS  non-zero: the verdict comes from colcon test-result
```

`colcon test` itself exits 0 here; the non-zero status comes from
`colcon test-result --verbose`, which is the property this subcommand exists
for.

### Test 5 — `pkg new demo_bad --python --interfaces`

```
===== TEST 5: pkg new demo_bad --python --interfaces =====
exit=1
interface packages must be ament_cmake; rosidl does not generate from ament_python
created? no
```

### Test 6 — usage errors: exit 2, usage, no traceback

```
--- `pkg` exit=2
usage:
  pkg new NAME [options]      Create a package in /tmp/ws/src
      --python                ament_python package (default: ament_cmake)
      --template pubsub|param Start from working code instead of an empty package
(no traceback)
--- `pkg nonsense` exit=2
usage:
  pkg new NAME [options]      Create a package in /tmp/ws/src
      --python                ament_python package (default: ament_cmake)
      --template pubsub|param Start from working code instead of an empty package
(no traceback)
--- `tutorial` exit=2
usage:
  tutorial clone URL [DIRECTORY]   Clone a repository into /tmp/ws/src
  tutorial deps                    rosdep install for everything in src/
  tutorial build [PACKAGE...]      colcon build (optionally --packages-select)
(no traceback)
--- `install-ros-packages` exit=2
usage: install-ros-packages PACKAGE [PACKAGE...]

  install-ros-packages demo-nodes-cpp image-tools   # ROS short names
  install-ros-packages ros-lyrical-rqt-graph        # full Debian name
(no traceback)
```

Beyond this, the full usage and refusal texts were diffed against the *old*
shell scripts run side by side on the host. See §5: 10 of 10 cases are
byte-identical on stdout, stderr **and** exit status.

### Test 7 — `pkg list | head -1`, no traceback from the closed pipe

```
===== TEST 7 (real): pkg list | head -1 in a built workspace =====
first line: t_cpp_param
first stderr line: + colcon list --names-only
combined: + colcon list --names-only
t_cpp_param
PASS  no traceback from the closed pipe
```

No `BrokenPipeError`, no `Exception ignored in: <_io.TextIOWrapper …>`.

### Test 8 — the tool removed from `PATH`

The prompt's literal command does not reach the intended path in this image:
`colcon` lives in `/usr/bin`, so `PATH=/usr/bin:/bin` leaves it available
(`ros2` is in `/opt/ros/lyrical/bin`). Both the literal command and commands
that genuinely remove the tool are recorded.

```
tool locations: colcon=/usr/bin/colcon  ros2=/opt/ros/lyrical/bin/ros2  python3=/usr/bin/python3
(so PATH=/usr/bin:/bin removes ros2 but NOT colcon in this image)

===== TEST 8a: the prompt's literal command =====
env PATH=/usr/bin:/bin pkg list  -> exit=0
    + colcon list --names-only

===== TEST 8b: ros2 genuinely absent, pkg new =====
exit=127
    init-workspace: command not found
    (no traceback)

===== TEST 8c: ros2 genuinely absent, pkg run =====
exit=127
    + ros2 run a b
    ros2: command not found
    (no traceback)

===== TEST 8d: colcon also absent (PATH with python3 only) =====
--- pkg list  exit=127
    + colcon list --names-only
    colcon: command not found
    (no traceback)
--- pkg build  exit=127
    + colcon build --symlink-install
    colcon: command not found
    (no traceback)
--- pkg test  exit=127
    + colcon test
    colcon: command not found
    (no traceback)

===== TEST 8e: tutorial and install-ros-packages with tools absent =====
tutorial build exit=127
    + colcon build --symlink-install
    colcon: command not found
install-ros-packages foo exit=127
    sudo: command not found
    (no traceback)
```

Every one is a plain `<tool>: command not found` on stderr with exit 127 —
the same message shape and the same status bash produced.

## 4. Line counts, per script

| Script | Before (shell) | After (Python) | Δ |
|---|---|---|---|
| `docker/scripts/pkg` | 346 | 630 | +284 |
| `docker/scripts/tutorial` | 72 | 202 | +130 |
| `docker/scripts/init-workspace` | 29 | 78 | +49 |
| `docker/scripts/install-ros-packages` | 51 | 132 | +81 |
| **total** | **498** | **1042** | **+544** |

The growth is mostly structure the prompt asked for and comments carried over:
enums, the `NewOptions` parsed value, explicit error paths, and the
echo-and-run helpers that each script now duplicates rather than sharing (the
prompt's "accepted cost"). The three Python heredocs inside the old `pkg` are
no longer smuggled through environment variables; they are ordinary pure
functions.

## 5. Every place the Python output differs from the shell output

Old and new were run side by side on the host, and their exit status, stdout
and stderr compared byte for byte.

### Byte-identical (no difference at all)

| Case | Result |
|---|---|
| `pkg` (no args) | exit 2, identical stdout+stderr |
| `pkg nonsense` | exit 2, identical |
| `pkg new` (no name) | exit 2, identical |
| `pkg new x --bogus` | exit 2, identical (`unknown option: --bogus` + usage) |
| `pkg new x --template zz` | exit 2, identical (`unknown template: zz` + usage) |
| `pkg run a` (too few args) | exit 2, identical |
| `tutorial` (no args) | exit 2, identical |
| `tutorial nonsense` | exit 2, identical |
| `tutorial clone` (no URL) | exit 2, identical |
| `install-ros-packages` (no args) | exit 2, identical |
| `install-ros-packages`, `ROS_DISTRO=""` | exit 1, identical message |
| `tutorial list`, missing `src/` | exit 0, identical (empty) |
| `init-workspace`, first run | exit 0, identical message |
| `init-workspace`, second run | exit 0, identical (`already initialized … (left untouched)`) |
| `init-workspace`, with `build/` present | exit 0, identical `note:` lines |
| `init-workspace` marker **file bytes** | identical, including the `# Created:` timestamp format (`2026-09-18T16:33:07-04:00`, i.e. `date --iso-8601=seconds`) |
| `init-workspace` marker on rerun | untouched in both |

### Differences, all on unpinned error paths, all with the same exit status

1. **`shlex.join` escapes an embedded single quote differently.** Disclosed in
   the prompt and accepted there; recorded anyway.

   ```
   old: ros2 pkg create 'it'\''s' --maintainer-name 'ROS Developer'
   new: ros2 pkg create 'it'"'"'s' --maintainer-name 'ROS Developer'
   ```

   Both paste back correctly and yield the same argv. Everything the suite and
   the docs actually show — including `--maintainer-name 'ROS Developer'` — is
   byte-identical, and the selftest check *printed commands quote arguments so
   they paste correctly* passes. The safe-character set is the same in both:
   bash's `^[A-Za-z0-9_./:=@%+,-]+$` and `shlex`'s `[^\w@%+=:,./-]` (ASCII)
   describe the same characters, so no argument changes from bare to quoted or
   back.

2. **`cd` into a missing workspace.** Same exit status (1); the message is
   Python's instead of bash's.

   ```
   old: <script>: line 333: cd: /nonexistent-ws: No such file or directory
   new: pkg: [Errno 2] No such file or directory: '/nonexistent-ws'
   ```

3. **A missing option value** (`--template`, `--deps ""`, `--license` with no
   argument). Same exit status (1), same message text, without bash's
   `<script>: line N: 2:` prefix. The shell used `${2:?message}`, which prints
   `<script>: line N: 2: <message>` and exits 1.

   ```
   old: <script>: line 165: 2: --template needs pubsub or param
   new: --template needs pubsub or param
   ```

4. **`tutorial deps` with `ROS_DISTRO` unset.** The shell expanded
   `${ROS_DISTRO}` under `set -u`, which was a fatal unbound-variable error
   (exit 1). The port prints `ROS_DISTRO is not set; this script must run
   inside the workstation image` and exits 1 — the same status, and the same
   sentence `install-ros-packages` already used. The case where `ROS_DISTRO`
   is set but **empty** is passed through to rosdep unchanged, exactly as
   before, so nothing that previously worked behaves differently.

5. **`pkg build <one>` no longer sources `install/setup.bash` into the running
   process**, because Python cannot. It runs the one listing through
   `bash -c` instead. Consequence: anything `setup.bash` printed on stdout is
   now discarded rather than forwarded. In practice it prints nothing, and the
   listing itself is byte-identical (see Test 1).

6. **A missing tool is reported by the script, not the shell.** `<tool>:
   command not found` on stderr, exit 127 — the same wording and status bash
   used, without the `<script>: line N:` prefix.

No difference was found on any path the suite, the docs, or a student's muscle
memory depends on. Every difference above keeps the exit status identical.

## 6. `git diff python-port --stat`

```
 docker/scripts/init-workspace       | 107 +++--
 docker/scripts/install-ros-packages | 165 +++++--
 docker/scripts/pkg                  | 890 ++++++++++++++++++++++++------------
 docker/scripts/tutorial             | 268 ++++++++---
 4 files changed, 987 insertions(+), 443 deletions(-)
```

Only the four allowed scripts, plus this report in the same commit. All four
keep mode `100755`.

## 7. Deviations

1. **The worktree was created at a stale commit** (`8256560`, "docs: record the
   teaching purpose, roadmap, and platform checklist"), so
   `docs/stages/stage-03-PROMPT.md` did not exist. Per the prompt's "First
   step" I ran `git fetch origin` then
   `git merge --ff-only origin/python-port`, which fast-forwarded to `fac72a9`.
   This is the third time this has happened. All work, and every gate
   including the baseline, is on `fac72a9`.

2. **`shlex.join` quoting of an embedded single quote** differs from the shell
   `shell_quote`. Disclosed above in §5.1, as the prompt directed.

3. **Test 8's literal command does not exercise the intended path.**
   `env PATH=/usr/bin:/bin pkg list` leaves `colcon` reachable, because
   `colcon` is installed at `/usr/bin/colcon` in this image. I ran the literal
   command *and* variants that genuinely remove the tool, and recorded both
   (§3, Test 8). I did not change the prompt's expectation, only added to it.

4. **Tests 3 and 4 were first run in a `--network=none` container and reported
   failures** (2 for C++, 3 for Python). Re-run with networking, the same
   commands report `0 errors, 0 failures`. The failures were `xmllint`-class
   tests that need to reach the package-format schema, not a regression: the
   authoritative selftest check *pkg test reports a clean lint result for a
   generated package* passes in both the baseline and the final run. The
   networked numbers are the ones reported in §3; I am flagging the first,
   misleading run rather than quietly dropping it.

5. **`tutorial deps` with `ROS_DISTRO` unset** now prints a sentence instead of
   bash's unbound-variable error (§5.4). Same exit status. I kept the
   set-but-empty case byte-identical rather than "improving" it.

6. **A comment had to be reworded.** My first draft of `pkg` contained the
   literal text `shell=True` inside a docstring explaining that it is
   forbidden, which made the Definition of Done's
   `grep -rn "shell=True\|os.system"` match. The comment now says "no shell is
   interposed". No behaviour change; the grep is clean.

7. **`apply_template` iterates in sorted order**, where the shell used `find`'s
   arbitrary order. The written files are identical either way; sorting only
   makes the port deterministic.

8. **`pkg` grew a `Refused` exception used as the single exit path for
   expected failures.** It is caught at `__main__` and turned into a message
   plus a status; it never reaches a student as a traceback. This is the
   "explicit errors" guardrail expressed in Python, not exceptions as control
   flow across module boundaries.

9. **I ran `make image` once** (as `IMAGE_NAME=ros2-tutorials-st03`) outside a
   gate, to have an image for the hand tests before the final selftest. It
   writes only the stage-scoped image tag.

10. **The final `make lint` and `make check` were run twice** — once before the
    last two edits (deviations 5 and 6) and once after. Only the later run is
    quoted in §2.

11. I did not touch the user's `ros2-tutorials` project, `ros2-tutorials-selftest`,
    or `ros2-tutorials-st04`. The hand tests used standalone
    `podman run --rm` containers on ROS domain 183, chosen to stay clear of
    both stage 03's domain 83 and the student default.

## 8. Open questions

1. **`shell_quote` was duplicated in the shell scripts and is duplicated
   again in Python** (`pkg` and `tutorial` each carry `quote()`). The prompt
   forbids a shared module because every file in `docker/scripts/` is on
   `PATH` and linted as a script, and the Dockerfile is out of scope. If the
   Dockerfile ever installs a private package directory, three or four
   helpers (`quote`, `echo`, `run`, `workspace`) would collapse into one
   module. That is an architect decision, not mine.

2. **`pkg build` with several packages prints no executables listing**, only
   with exactly one. That is the old behaviour, preserved. Whether listing for
   each named package would be friendlier is a behaviour change.

3. **`tutorial list` sorts with Python's byte ordering**, where the shell
   piped through `sort` (locale-dependent). For package directory names these
   agree. A workspace with non-ASCII directory names could order differently;
   nothing pins it and I did not change it deliberately.

4. **`tutorial list` reports the workspace root itself** if `src/.git` exists,
   printing the absolute path rather than a relative name — an oddity of the
   original `find … -printf '%h'` plus `sed` pipeline that I preserved
   deliberately. It looks like a latent bug rather than a feature.

5. **`pkg new NAME` accepts a name beginning with `--`** and passes it to
   `ros2 pkg create`, because the shell took `$1` as the name unconditionally.
   Preserved. Rejecting it would be a new validation rule.

6. **`install-ros-packages` runs `sudo apt-get update` without echoing it**,
   unlike every other command in these scripts, which print `+ …` first. The
   old script did the same. Given "no black box" is a stated purpose of this
   repo, this may be worth making consistent in a later stage.

7. **Nothing in the suite exercises `tutorial deps`.** It is the one
   subcommand with no coverage, so its port rests on reading alone.

8. **`pkg test` with no package argument** runs `colcon test` across the whole
   workspace; the selftest only ever names a package. Preserved as written,
   untested by the suite.
