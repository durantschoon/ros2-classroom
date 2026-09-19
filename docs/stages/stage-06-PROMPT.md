# Stage 06 — Port the self-test to Python

Branch name for this stage: `stage-06-port-the-selftest`. Base: `python-port`.

Read `docs/stages/README.md` first, including "Added by the retro before stage
05". Its gates, environment facts, and guardrails apply and are not repeated
here.

**First step, before anything else.** Executor worktrees have been created at a
stale commit in every stage so far. Run `git log --oneline -1`; if
`docs/stages/stage-06-PROMPT.md` is missing, run
`git fetch origin && git merge --ff-only origin/python-port` and record it as a
Deviation. If the file is still missing, invoke the Blocked protocol.

## Motivation (measured)

`scripts/smoke-container` is the last script slated for the Python port
(`docs/roadmap.md`, "Language: Python replaces shell"). `make lint` lists it as
the only `shell, advisory` file left. It is 507 lines of bash that builds
multi-line shell snippets inside quoted strings, which is where its one known
quoting slip lives (behaviour change 2 below).

It could not be ported safely until stage 05, because it was the oracle for
every other port and nothing judged it. Now
`tests/host/test_smoke_container.py` runs it as a black box against fakes: 48
tests, run in seconds, pinning its isolation, its accounting, its cleanup,
`--keep`, readiness, and `HAPPY_TRANSCRIPT`, the ordered list of 13 step titles
and 48 check names, which stage 05 compared entry by entry against a real
48/48 run and found identical. **That transcript is your contract.**

The coordinator ran this stage's real-system negative control before writing
this prompt, as the retro requires: with the C++ talker template's greeting
changed from `hello from` to `greetings from`, the current suite reported
**47 passed, 1 failed**, the one failure being `templated pubsub node did not
publish on /chatter`. Verification item 3 asks the ported suite to reproduce that.

## The change

Port `scripts/smoke-container` to Python, in place: same file name, no `.py`
extension, `#!/usr/bin/env python3`, executable bit kept. `make selftest`, CI,
and the docs must need no change. It is a host script: **stdlib only, Python
3.9-compatible**.

**Behaviour is preserved exactly (guardrail 8)**, apart from the two changes
below. The tests pin most of it. What is easy to lose:

- **The output, byte for byte**: the `using: …` banner; `== <step>` titles; the
  `  PASS <name>` and `  FAIL <name>` lines with their colour escapes; the
  `N passed, M failed` line; the `failed checks:` list; `== cleaning up`; the
  `--keep` hint. Step titles and check names must match `HAPPY_TRANSCRIPT`
  exactly, in order.
- **The environment it sets up**: `COMPOSE` gains `-p <project>` and is
  exported, so the `make package`-style checks reach the same project;
  `NOVNC_PORT` and `ROS_DOMAIN_ID` are exported with their `SELFTEST_*`
  overrides; `IMAGE_NAME` and `ROS_DISTRO` name the image.
- **Cleanup on every way out**: success, failure, an early abort, Ctrl-C, and
  SIGTERM all end with `down -v --remove-orphans` on the self-test's own
  project, and `--keep` suppresses it on all of them. Use `try`/`finally` plus
  handlers that turn SIGTERM and SIGHUP into an orderly exit.
- **The exit status**: 0 only when every check passed.
- **Time and the network stay external commands.** Every wait runs the
  `sleep` command and every HTTP probe runs `curl`, as subprocesses. Do **not**
  use `time.sleep` or `urllib`: the tests' only seams for time and network are
  a fake `sleep` and a fake `curl` on `PATH`, and with `time.sleep` the 48
  tests would really sleep through every readiness loop.
- **Child output order.** `compose build` and friends stream to the terminal
  today. Flush Python's own stdout before starting any child, or the log
  interleaves wrongly.
- The Xvfb ownership check waits for Xvfb to exist first (up to 30 tries). Keep
  that; it fixed a real one-in-three flake.

**Shape (guardrails 1, 2, 4).** Each check's verdict is a pure function from
the command's result (status, stdout, stderr) to pass or fail, separate from
running the command. Commands are argv lists, including the multi-line snippets
sent to `bash -lc` inside the container, which become single, ordinary
arguments. **`shell=True` is forbidden**, and so is `os.system`. An expected
failure is a FAIL line or a message, never a traceback (guardrail 3), and that
includes a closed output pipe.

Keep it one self-contained file, and keep it a script, not a `unittest` suite:
its output format is its interface.

## Two intentional behaviour changes

The user has decided both are fixed in this port, as disclosed changes. These
are the **only** places you may edit a test, and only as described.

### 1. A missing engine is a failed check, not a silent death

Today, when `scripts/compose-command --engine` finds nothing, the suite dies
under `set -e` inside the "Image and environment" step: exit 1, a message on
stderr, and **no `N passed, M failed` line and no `failed checks:` list**. That
is the "silently stops counting" failure stage 05 exists to guard against.

New behaviour: the check `the image defaults to the non-root ros user` FAILs
with the name `no container engine found to inspect the image`, the suite
carries on with the remaining checks, and the summary, the `failed checks:`
list, exit status 1, and cleanup all happen as for any other failure.

In `tests/host/test_smoke_container.py`, class `EngineDetection`: **replace**
`test_a_missing_engine_aborts_the_suite_with_no_summary` with a test of the new
behaviour (exit 1; the summary line present; the new FAIL name listed under
`failed checks:`; later steps such as `== Turtlesim` still ran), and update the
class docstring. `test_a_missing_engine_still_cleans_up` and
`test_the_engine_is_used_to_inspect_the_image_by_name` stay as they are.

### 2. Nothing is written to the host's `/tmp`

Two redirections, `>/tmp/pkg-smoke-pubsub.log` and `>/tmp/pkg-smoke-msgs.log`,
sit outside the quoted container command, unlike every sibling in the file. So
the suite discards the container's output into two files in the **host's**
`/tmp`. It was a quoting slip.

New behaviour: capture that output in memory. When the check fails, print its
last five lines, indented, under the FAIL line. Write nothing on the host.

In class `Housekeeping`: **replace**
`test_it_writes_two_log_files_into_the_hosts_own_tmp` with two tests: a run
creates neither file (remove them first, then assert they do not exist
afterwards), and a failing `pkg new --template pubsub` check shows the tail of
the command's output under its FAIL line. Change no other test.

## Ground rules

- Apart from those two replacements, **no test changes**, and no change to
  `tests/host/fakes.py`. If a test fails, the port is wrong. If you are certain
  a test pins something Python cannot preserve, that is a Blocked finding.
- Nothing under `docker/` changes, and no other script changes.
- Do not add checks, remove checks, rename checks, or reorder them. Ideas go
  under Open questions.

## Allowed files

- `scripts/smoke-container`
- `tests/host/test_smoke_container.py` — the two replacements described above
- `docs/stages/stage-06-REPORT.md` (new)

Anything else is out of scope. Needing another file is a Blocked finding.

## Verification

Run each of these and paste the output into the report.

1. **The transcript, against the real system.** Save the `== ` and
   `PASS`/`FAIL` lines of a real `make selftest` from the unmodified base and
   from your port, colour stripped, and `diff` them: no difference.
2. **Python 3.9 for real**:
   `podman run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo
   docker.io/library/python:3.9-slim python -m unittest discover -s tests/host`.
   State which tests skip there and why.
3. **The suite still catches a real break.** In
   `docker/templates/cpp/pubsub/src/talker.cpp`, change `hello from` to
   `greetings from`, run your ported `make selftest`, and show that it reports
   47 passed, 1 failed, failing exactly `templated pubsub node did not publish
   on /chatter`, the same as the shell suite did. Revert by copy-out and
   copy-back with a checksum.
4. **Mutations of the port.** Five temporary mutations to your Python suite,
   different from stage 05's five, each caught by a test, each reverted by
   copy-back with a checksum.
5. **Ctrl-C cleans up.** Start the suite against the fakes with a fake `sleep`
   that really sleeps, send SIGINT mid-run, and show the fake compose received
   `down -v --remove-orphans` and that no traceback was printed. Then the same
   with SIGTERM.
6. **A closed pipe.** `scripts/smoke-container --keep | head -3` against the
   fakes: no traceback.
7. `make lint` now reports no `shell, advisory` file at all.

## Definition of Done

- Baseline on the unmodified base: `make lint`, `make check` (162 tests
  expected), and one real `make selftest` (48/48 expected), whose transcript is
  the left-hand side of Verification 1.
- Final: `make lint` passes, with `scripts/smoke-container` classified
  `python, host (3.9 grammar)`.
- Final: `make check` passes in under 30 seconds. The count is 162, minus the
  two tests replaced, plus the three that replace them: report the arithmetic.
- Final: real `make selftest` passes 48/48.
- Verification 1–7 pass, with output in the report.
- `grep -n "shell=True\|os.system\|time.sleep\|urllib" scripts/smoke-container`
  finds nothing.
- `git diff python-port --stat` shows only allowed files, and the test file's
  diff shows only the two authorized replacements.

No other stage is running, so `make selftest` may use its defaults. Never touch
the project `ros2-tutorials`; it is the user's.

## Commit

One commit, containing the change and `docs/stages/stage-06-REPORT.md`, with
exactly this subject line (a `Co-Authored-By:` trailer is expected):

```
refactor: port the self-test from shell to Python
```

Stage files by path; never `git add -A`. Then
`git push -u origin stage-06-port-the-selftest`. Never push to `python-port` or
`main`.

## Report requirements

`docs/stages/stage-06-REPORT.md` must contain:

1. A checklist echo of "The change", both behaviour changes, and the Definition
   of Done.
2. Baseline and final gate outputs, verbatim and side by side.
3. The outputs of Verification 1–7, with the five mutations tabulated.
4. Line counts before and after.
5. The exact test edits made under "Two intentional behaviour changes".
6. Every place the Python suite's output differs from the shell suite's by even
   one character, and why that is acceptable.
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
