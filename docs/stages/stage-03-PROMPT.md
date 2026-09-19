# Stage 03 — Port the container scripts to Python

Branch name for this stage: `stage-03-port-container-scripts`. Base: `python-port`.

Read `docs/stages/README.md` first. Its gates, environment facts, and
guardrails apply to this stage and are not repeated here.

**First step, before anything else.** Executor worktrees have twice been
created at a stale commit. Run `git log --oneline -1`; if
`docs/stages/stage-03-PROMPT.md` is missing, run
`git merge --ff-only origin/python-port` (fetch first) and record it as a
Deviation. If the file is still missing, invoke the Blocked protocol.

**This stage runs in parallel with stage 04.** Stage 04 owns everything under
`scripts/`. You own `docker/scripts/`. Touch nothing of theirs.

## Motivation (measured)

`docs/roadmap.md`, "Language: Python replaces shell", records the decision and
its reasons. The measured part: `docker/scripts/pkg` is 300 lines of bash of
which three functions are already Python heredocs (`cmake_insert`,
`xml_insert`, `setup_py_patch`), passed their inputs through environment
variables because bash cannot hand them structured data. The one
shell-language bug found in this project lived here: `"$*"` printed
`--maintainer-name ROS Developer`, which re-parses as two arguments.

Stage 02 made this port checkable: `make selftest` now has 27 checks that
exercise these four scripts (the `pkg helper`, `Student make targets`,
`Container helpers`, and `Package installation helper` steps).

## The change

Port these four scripts to Python, in place:

- `docker/scripts/pkg`
- `docker/scripts/tutorial`
- `docker/scripts/init-workspace`
- `docker/scripts/install-ros-packages`

Same file names, no `.py` extension, `#!/usr/bin/env python3`, executable bit
kept. The Dockerfile, Makefile, docs, and the suite must need no change. They
run inside the image, on Ubuntu Resolute's Python (3.14 at the time of
writing), stdlib only: there is no pip step and there must not be one.

**Behaviour is preserved exactly (guardrail 8).** In particular:

- Every `+ <command>` echo line goes to **stderr**, before the command runs,
  quoted so it pastes back into a shell. `shlex.join` produces the same text as
  the current `shell_quote` for everything the suite and docs show (for example
  `--maintainer-name 'ROS Developer'`). It differs only in how an embedded
  single quote is escaped; both forms paste correctly, so that difference is
  accepted. Disclose it as a Deviation anyway.
- Every message, and which stream it goes to. `note()` writes to stderr.
- Every exit status: usage errors exit 2; refusals exit 1; a failed `ros2`,
  `colcon`, `git`, `rosdep`, or `apt-get` propagates its status.
- `PKG_VIA_MAKE=1` switches the `next:` hints to name make targets.
- `pkg run` replaces the process (`os.execvp`), so Ctrl-C and the exit status
  reach `ros2` directly.
- `pkg test` runs `colcon test`, tolerates its status, then runs
  `colcon test-result --verbose` and returns *that* status.
- `pkg build <one package>` lists that package's executables afterwards. Today
  it does so by sourcing `install/setup.bash` into the running shell. Python
  cannot source a shell file: run that one listing through
  `bash -c 'source … && ros2 pkg executables …'` with the paths passed as
  arguments, not interpolated into the string. This is the one place a shell
  is involved, and it is still an argv list, not `shell=True`.
- `pkg new` on an existing package is refused by `ros2 pkg create` itself, with
  its message and exit status. Keep relying on that; do not add a separate
  existence check, which would change what the student sees.
- `init-workspace` never overwrites the marker, and its two messages are
  pinned by the suite.
- `install-ros-packages` keeps its name-resolution rule: names starting with
  `ros-`, `python3-`, or `lib` are literal; otherwise try
  `ros-$ROS_DISTRO-<name with _ as ->` and fall back to the literal name when
  apt does not know it. A missing package fails loudly.

**Shape (guardrails 1, 2, 4).** Build types, templates, and subcommands are
closed sets: `Enum`s, parsed once at the entry point. The three file patchers
become pure functions from text to text, with the file I/O around them. Every
command is an argv list. **`shell=True` is forbidden**, and so is `os.system`.
Paths are `pathlib.Path`. An expected failure is a message and an exit status,
never a traceback (guardrail 3): in particular a missing `ros2` on `PATH`, and
a closed output pipe.

Each script stays self-contained. Do not add a shared module: every file in
`docker/scripts/` is installed on `PATH` and linted as a script, and the
Dockerfile is outside this stage. A dozen duplicated lines of echo-and-run is
the accepted cost.

## Ground rules

- **No test changes.** `scripts/smoke-container` and `tests/` are the oracle
  and are not yours to edit. If a check fails, the port is wrong, not the check.
  If you are certain a check pins something that *cannot* be preserved, that is
  a Blocked finding.
- Do not improve behaviour while porting. Note ideas under Open questions.
- The templates under `docker/templates/` do not change.

## Allowed files

- `docker/scripts/pkg`
- `docker/scripts/tutorial`
- `docker/scripts/init-workspace`
- `docker/scripts/install-ros-packages`
- `docs/stages/stage-03-REPORT.md` (new)

Anything else is out of scope. Needing another file is a Blocked finding.

## Running the gates without colliding with stage 04

Every `make selftest` in this stage, baseline included, uses exactly:

```sh
SELFTEST_PROJECT=ros2-tutorials-st03 SELFTEST_NOVNC_PORT=6083 SELFTEST_ROS_DOMAIN_ID=83 IMAGE_NAME=ros2-tutorials-st03 make selftest
```

Never run the bare `make selftest`, never touch the projects
`ros2-tutorials` (the user's), `ros2-tutorials-selftest`, or
`ros2-tutorials-st04`.

## Tests

Beyond the gates, run each of these by hand in a throwaway container built from
your image (`podman run --rm -e WORKSPACE=/tmp/ws -e ROS_DOMAIN_ID=83 …`), and
paste the output into the report:

1. All six creation modes build: C++ and Python, each with `pubsub` and
   `param`; `--interfaces`; and a plain package.
2. The printed `ros2 pkg create` line, pasted back verbatim into a shell in a
   fresh workspace, creates the same package (compare `package.xml`).
3. `pkg test` on a C++ and a Python template package: 0 errors, 0 failures.
4. A deliberately failing test (break the formatting of one template file):
   `pkg test` exits non-zero. This proves the verdict comes from
   `colcon test-result`, not from `colcon test`.
5. `pkg new demo_bad --python --interfaces`: exit 1 and the explanation.
6. `pkg`, `pkg nonsense`, `tutorial`, `install-ros-packages` with no
   arguments: exit 2 and usage, no traceback.
7. `pkg list | head -1`: no traceback from the closed pipe.
8. With `ros2` removed from `PATH` (`env PATH=/usr/bin:/bin pkg list`): a
   plain message, no traceback.

## Definition of Done

- Baseline on the unmodified base, using the isolated command above:
  `make lint`, `make check`, and `make selftest` (45/45 expected).
- Final: `make lint` passes, and now classifies all four scripts as
  `python, container`.
- Final: `make check` passes unchanged (104 tests expected).
- Final: `make selftest`, isolated as above, passes with the same count and the
  same check names as the baseline.
- Tests 1–8 pass, with output in the report.
- `grep -rn "shell=True\|os.system" docker/scripts/` finds nothing.
- `git diff python-port --stat` shows only allowed files.

## Commit

One commit, containing the change and `docs/stages/stage-03-REPORT.md`, with
exactly this subject line:

```
refactor: port the container scripts from shell to Python
```

Stage files by path; never `git add -A` (agent worktrees live inside this
repository). Then attempt `git push -u origin stage-03-port-container-scripts`.
Never push to `python-port` or `main`.

## Report requirements

`docs/stages/stage-03-REPORT.md` must contain:

1. A checklist echo of "The change" and the Definition of Done.
2. Baseline and final gate outputs, verbatim and side by side, including the
   list of check names from both self-test runs and their set difference.
3. The outputs of Tests 1–8.
4. Line counts before and after, per script.
5. Every place the Python output differs from the shell output by even one
   character, and why that is acceptable.
6. `git diff python-port --stat`.
7. **Deviations**, numbered and honest, including the boring ones.
8. **Open questions**: things you noticed but correctly did not do.

## Blocked protocol

STOP and commit only the report, with a BLOCKED section giving the exact
failing output and why each permitted path is closed, if:

- a gate already fails on the unmodified base;
- a pinned behaviour cannot be preserved in Python;
- the change cannot be made inside the allowed files;
- any guardrail in `docs/stages/README.md` says STOP AND ASK.

A clean block is a successful execution.
