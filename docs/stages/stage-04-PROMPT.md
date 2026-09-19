# Stage 04 — Port the host scripts to Python

Branch name for this stage: `stage-04-port-host-scripts`. Base: `python-port`.

Read `docs/stages/README.md` first. Its gates, environment facts, and
guardrails apply to this stage and are not repeated here.

**First step, before anything else.** Executor worktrees have twice been
created at a stale commit. Run `git log --oneline -1`; if
`docs/stages/stage-04-PROMPT.md` is missing, run
`git merge --ff-only origin/python-port` (fetch first) and record it as a
Deviation. If the file is still missing, invoke the Blocked protocol.

**This stage runs in parallel with stage 03.** Stage 03 owns everything under
`docker/scripts/`. You own the six scripts named below. Touch nothing of theirs.

## Motivation (measured)

`docs/roadmap.md`, "Language: Python replaces shell", records the decision and
its reasons. Stage 02 made this port checkable: `tests/host/` holds black-box
tests for each of these six scripts (82 of the 104 tests `make check` runs),
and every one of them runs the script as a subprocess, so they cannot tell
shell from Python. They run in under five seconds. That is your oracle.

Stage 02 also found two bugs by pinning them. The user has decided both are
fixed **in this port**, as disclosed behaviour changes, rather than ported
faithfully (see "Two intentional behaviour changes").

## The change

Port these six scripts to Python, in place:

- `scripts/compose-command`
- `scripts/compose-up`
- `scripts/check-host`
- `scripts/run-quiet`
- `scripts/open-url`
- `scripts/base-image-digest`

Same file names, no `.py` extension, `#!/usr/bin/env python3`, executable bit
kept. The Makefile, CI, docs, and `scripts/smoke-container` must need no
change. **Stdlib only, Python 3.9-compatible**: these run on students' own
machines, and macOS's Command Line Tools ship 3.9. `make lint` checks the
grammar; it cannot check the standard library, so do not use APIs newer than
3.9 (no `zip(strict=)`, no `str | None` annotations, no `match`).

**Behaviour is preserved exactly (guardrail 8)**, apart from the two changes
below. The tests pin most of it. Things they pin that are easy to lose:

- **`run-quiet`**: stdout is *inherited*, never piped, so an interactive
  `make run` keeps its terminal. Only stderr passes through the filter, line by
  line as it arrives, not buffered until exit. The wrapped command's exit
  status is returned. `VERBOSE=1` replaces the process with the command
  (`os.execvp`). Two things no test can see and you must get right: Ctrl-C
  during `make run` must stop the child and return its status **without a
  Python traceback**, and a child killed by a signal returns `128 + signal`.
- **`open-url`**: the URL is printed and flushed *before* anything is launched.
  `wslview`, `powershell.exe`, `open`, `xdg-open`, and `$BROWSER` replace the
  process, so their exit status is the script's; `explorer.exe` is run and its
  status ignored. WSL is detected from `WSL_DISTRO_NAME` **or** from
  `/proc/version`. `xdg-open` is never used on WSL.
- **`compose-command`**: any unrecognised argument means the default mode. That
  is pinned; keep it.
- **`compose-up`**: a multi-word `COMPOSE` is split into words; the
  `+ … up -d` line is echoed before running; compose replaces the process.
- **`check-host`**: it calls `scripts/compose-command` next to itself, by path.
  It prints colour escapes unconditionally today; keep that.
- **`base-image-digest`**: it fetches with **`curl`**, as a subprocess. Do not
  switch to `urllib`: the tests' only network seam is a fake `curl` on `PATH`,
  and the exact `curl` arguments are pinned.

**Shape (guardrails 1, 2, 4).** The engine (docker, podman) and
`compose-command`'s output modes are closed sets: `Enum`s, parsed once at the
entry point. Keep decisions in pure functions: the search order, the
stale-image comparison, the line filter, the header parse, WSL detection from
text. Process spawning stays at the edges. Every command is an argv list.
**`shell=True` is forbidden**, and so is `os.system`. An expected failure is a
message and an exit status, never a traceback (guardrail 3), and that includes
a closed output pipe and Ctrl-C.

Each script stays self-contained. Do not add a shared module: every file in
`scripts/` is linted as a script and discovered by shebang.

## Two intentional behaviour changes

These are the **only** places you may edit tests, and only as described.

### 1. `compose-up` finds the desktop of the project actually in use

Today it filters on the hardcoded label
`com.docker.compose.project=ros2-tutorials`. Under any project override it
finds no container and never detects a stale image, which is the failure the
script exists to prevent. `make selftest` runs with
`COMPOSE="podman-compose -p ros2-tutorials-selftest"`, so this is live.

New rule, in this precedence:

1. `-p NAME`, `-p=NAME`, `--project-name NAME`, or `--project-name=NAME` among
   the words of `COMPOSE`;
2. else the environment variable `COMPOSE_PROJECT_NAME`, when non-empty;
3. else `ros2-tutorials`, the `name:` in `compose.yaml`.

`test_it_looks_for_the_desktop_of_this_compose_project` keeps passing
unmodified, since it uses the default. **Add** tests to
`tests/host/test_compose_up.py` for each of the four spellings in rule 1, for
rule 2, for rule 1 beating rule 2, and one showing a stale image *is* detected
under `-p other`.

### 2. `base-image-digest` matches the header name case-insensitively

Today `[Dd]ocker-[Cc]ontent-[Dd]igest` misses `DOCKER-CONTENT-DIGEST`. HTTP
header names are case-insensitive; match them that way.

In `tests/host/test_base_image_digest.py`, **replace**
`test_an_all_uppercase_header_is_not_matched_today` with a test that an
all-uppercase header **is** matched, and add one for a mixed case the old
pattern also missed (`Docker-content-Digest`). Change no other test.

## Ground rules

- Apart from the additions and the one replacement above, **no test changes**.
  If a test fails, the port is wrong, not the test. If you are certain a test
  pins something that *cannot* be preserved in Python, that is a Blocked
  finding.
- `scripts/smoke-container`, `scripts/lint-scripts`, and
  `scripts/workstation-help` are not part of this stage.
- Do not improve behaviour beyond the two changes. Note ideas under Open
  questions.

## Allowed files

- `scripts/compose-command`
- `scripts/compose-up`
- `scripts/check-host`
- `scripts/run-quiet`
- `scripts/open-url`
- `scripts/base-image-digest`
- `tests/host/test_compose_up.py` — additions only
- `tests/host/test_base_image_digest.py` — the one replacement and one addition
- `docs/stages/stage-04-REPORT.md` (new)

Anything else is out of scope. Needing another file is a Blocked finding.

## Running the gates without colliding with stage 03

Every `make selftest` in this stage, baseline included, uses exactly:

```sh
SELFTEST_PROJECT=ros2-tutorials-st04 SELFTEST_NOVNC_PORT=6084 SELFTEST_ROS_DOMAIN_ID=84 IMAGE_NAME=ros2-tutorials-st04 make selftest
```

Never run the bare `make selftest`, never touch the projects
`ros2-tutorials` (the user's), `ros2-tutorials-selftest`, or
`ros2-tutorials-st03`.

Port one script at a time and run `make check` after each. It takes seconds;
use it.

## Tests

Beyond the gates, run each of these and paste the output into the report:

1. **Python 3.9 for real.** Run the fast tests under an actual 3.9
   interpreter, since the local `python3` is newer:
   `podman run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo
   docker.io/library/python:3.9-slim python -m unittest discover -s tests/host`.
   The tests that need `make` will skip there; every other test must pass.
2. **Mutations.** For each of the six ported scripts, make one temporary
   mutation that breaks a pinned behaviour, show a test failing, and revert.
   Use different mutations from the ones in `stage-02-REPORT.md`. Confirm with
   `git status` that none remains.
3. **Ctrl-C through `run-quiet`.** Start `scripts/run-quiet sleep 30`, send it
   SIGINT, and show: no traceback, a prompt return, and the exit status.
4. **A signal-killed child.** `scripts/run-quiet sh -c 'kill -TERM $$'` exits
   143.
5. **Streaming.** `scripts/run-quiet sh -c 'echo one >&2; sleep 2; echo two >&2'`
   shows `one` two seconds before `two`, not both at the end.
6. **Interactive stdout.** `scripts/run-quiet python3 -c
   'import sys; print(sys.stdout.isatty())'` prints `True` when run from a
   terminal. If you have no terminal, use `script -qc` to provide one, and say
   so.
7. **Closed pipe.** `scripts/check-host | head -1` and
   `scripts/compose-command --explain | head -1`: no traceback.
8. **The real thing.** `make doctor`, `make engine`, and `make digest` on this
   host, before and after: identical output.

## Definition of Done

- Baseline on the unmodified base: `make lint`, `make check` (104 tests
  expected), and `make selftest` isolated as above (45/45 expected).
- Final: `make lint` passes, and classifies all six scripts as
  `python, host (3.9 grammar)`.
- Final: `make check` passes. The count rises by exactly the tests this prompt
  adds; report the arithmetic.
- Final: `make selftest`, isolated as above, passes with the same count and the
  same check names as the baseline.
- Tests 1–8 pass, with output in the report.
- `grep -n "shell=True\|os.system"` over the six scripts finds nothing.
- `git diff python-port --stat` shows only allowed files, and the diff of the
  two test files shows only the authorized edits.

## Commit

One commit, containing the change and `docs/stages/stage-04-REPORT.md`, with
exactly this subject line:

```
refactor: port the host scripts from shell to Python
```

Stage files by path; never `git add -A` (agent worktrees live inside this
repository). Then attempt `git push -u origin stage-04-port-host-scripts`.
Never push to `python-port` or `main`.

## Report requirements

`docs/stages/stage-04-REPORT.md` must contain:

1. A checklist echo of "The change", both behaviour changes, and the Definition
   of Done.
2. Baseline and final gate outputs, verbatim and side by side, including the
   list of check names from both self-test runs and their set difference.
3. The outputs of Tests 1–8, with the six mutations tabulated.
4. Line counts before and after, per script.
5. The exact test edits made under "Two intentional behaviour changes".
6. Every place the Python output differs from the shell output by even one
   character, and why that is acceptable.
7. `git diff python-port --stat`.
8. **Deviations**, numbered and honest, including the boring ones.
9. **Open questions**: things you noticed but correctly did not do.

## Blocked protocol

STOP and commit only the report, with a BLOCKED section giving the exact
failing output and why each permitted path is closed, if:

- a gate already fails on the unmodified base;
- a pinned behaviour cannot be preserved in Python;
- the change cannot be made inside the allowed files;
- any guardrail in `docs/stages/README.md` says STOP AND ASK.

A clean block is a successful execution.
