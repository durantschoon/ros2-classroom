# Stage 05 — Tests before the last port: pin the self-test itself

Branch name for this stage: `stage-05-test-the-selftest`. Base: `python-port`.

Read `docs/stages/README.md` first, including "Added by the retro before stage
05". Its gates, environment facts, and guardrails apply and are not repeated
here.

**First step, before anything else.** Executor worktrees have been created at a
stale commit in every stage so far. Run `git log --oneline -1`; if
`docs/stages/stage-05-PROMPT.md` is missing, run
`git fetch origin && git merge --ff-only origin/python-port` and record it as a
Deviation. If the file is still missing, invoke the Blocked protocol.

## Motivation (measured)

`scripts/smoke-container` is the last shell script slated for the port, and it
is the oracle every other port was judged by. Nothing judges *it*. Stage 06
will rewrite it in Python; today a rewrite could silently stop counting
failures, stop cleaning up, or stop isolating itself, and `make selftest` would
still print a cheerful summary.

Two of its behaviours exist because of real incidents, and neither is pinned:

- **It once deleted a student's workspace.** Its cleanup runs `down -v`, and it
  shared the student's compose project. It now prefixes every compose call with
  `-p ros2-tutorials-selftest`.
- **It once leaked its ROS graph into a student's workstation**, and theirs into
  its own. It now exports its own `ROS_DOMAIN_ID`.

The coordinator prototyped this stage's approach before writing this prompt,
as the retro now requires. Run with a fake compose command, a fake `podman` and
`podman-compose` for engine detection, and fake `sleep` and `curl`, the whole
suite ran in **0.9 seconds**, accounted for all 48 checks (21 passed, 27 failed,
since the fakes printed nothing), exited 1, made 60 compose calls of which
**0** lacked the project flag, ended with `down -v --remove-orphans`, and with
`--keep` made no `down` call at all. So everything below is observable from
outside the script.

The prototype also showed a trap: the suite passes multi-line scripts as single
arguments, and a fake that logs one call per *line* splits those into phantom
calls (it reported 48 "violations" that did not exist). `tests/host/fakes.py`
records calls that way today.

## The change

This stage changes no script. It adds tests that pass against the current shell
`scripts/smoke-container`, so that stage 06 can prove its port equivalent.

### 1. Extend the harness: `tests/host/fakes.py`

Additively, keeping its public API and every existing test passing:

- **Record calls robustly.** One JSON array per line instead of NUL-joined
  text, so arguments containing newlines survive. `Sandbox.argv()` and
  `last_argv()` keep their signatures and results.
- **Record chosen environment variables** with each call, opt-in per fake (for
  example `record_env=("ROS_DOMAIN_ID", "NOVNC_PORT")`), with an accessor to
  read them back.
- **A `contains` match mode** for rules, which fires when a given substring
  appears in any argument. The suite sends whole shell snippets as one
  argument (`bash -lc '<script>'`), which the existing `prefix` and `all` modes
  cannot address.

### 2. `tests/host/test_smoke_container.py`

Black-box, like every test here: run `scripts/smoke-container` as a
subprocess, on a sandbox `PATH`, with `COMPOSE` naming a fake. It also needs a
fake `podman` (answering `compose version`, and `image inspect` with `ros`), a
fake `podman-compose`, fake `sleep` and `curl`, and the real `make`, `bash`,
`grep`, `sed`, `tail`, `seq`, and whatever else the script itself calls. Find
that list by running it, not by reading it. The suite's `make package`-style
checks run the real Makefile, which must reach the same fake through the
exported `COMPOSE`.

Pin at least these. Add any observable behaviour this list misses.

- **Isolation of the project.** Every compose call starts with
  `-p ros2-tutorials-selftest`. `SELFTEST_PROJECT=other` changes that prefix on
  every call. No call ever names the bare project `ros2-tutorials`. This must
  hold for the calls made through `make` too.
- **Isolation of the port.** The banner names host port 6081 by default and
  `SELFTEST_NOVNC_PORT` overrides it; the host-side `curl` targets that port,
  while the in-container check targets 6080 regardless.
- **Isolation of the ROS graph.** Compose runs with `ROS_DOMAIN_ID=99` in its
  environment by default; `SELFTEST_ROS_DOMAIN_ID` overrides it. Never 42.
- **Accounting.** With fakes that print nothing: exit status 1; a
  `N passed, M failed` line; `N + M` equals the number of `PASS` and `FAIL`
  lines; a `failed checks:` list naming each failed check once.
- **The happy path.** A scenario of canned replies under which **every check
  passes**: exit status 0, `M` is 0, and no `failed checks:` list. This is the
  transcript stage 06 must reproduce exactly, so also pin the **ordered list of
  step titles and check names**. Build the scenario as data (a table of
  `contains` rules), not as code per check.
- **Cleanup.** The last compose call is `down -v --remove-orphans`, on the
  all-pass run, on the all-fail run, and when the suite aborts early.
- **`--keep`.** No `down` call is made, and the hint printed names the project
  in the removal command.
- **Readiness.** When `exec` fails a few times and then succeeds, the suite
  proceeds. When it never succeeds, the suite records the failure, exits 1, and
  still cleans up. The fake `sleep` keeps both fast.
- **Engine detection failing mid-suite.** With `COMPOSE` set but no engine for
  `scripts/compose-command --engine` to find, the suite today aborts under
  `set -e` with no summary line at all. Pin what happens today and raise it
  under Open questions; do not fix it.

**Prove the tests have teeth.** Make at least these five temporary mutations to
`scripts/smoke-container`, one at a time, show a test failing for each, and
revert by copy-out and copy-back with a checksum (never `git checkout --`):
drop the `-p` project from `COMPOSE`; make `bad` stop counting; exit 0
unconditionally at the end; ignore `--keep`; stop exporting `ROS_DOMAIN_ID`.

### 3. `tests/host/README.md`

Document the new fake features and how the smoke-container scenario is built.

## Ground rules

- **No script changes**: nothing under `scripts/` or `docker/` changes, apart
  from the temporary, reverted mutations.
- Pin what the suite does **today**, even where it looks wrong. Raise it under
  Open questions.
- Do not pin the *number* of checks; it grows. Pin relationships (`N + M`
  equals the lines printed) and the ordered names.
- The tests must not need docker, podman, the network, or a container, and
  `make check` as a whole must stay under 30 seconds.
- Tests must not write outside their temporary directories. Note that
  `smoke-container` changes directory to the repository root: confirm with
  `git status` that a test run leaves nothing behind in the repository.

## Allowed files

- `tests/host/test_smoke_container.py` (new)
- `tests/host/fakes.py` — additive, API-preserving
- `tests/host/README.md`
- `docs/stages/stage-05-REPORT.md` (new)

Anything else is out of scope. Needing another file is a Blocked finding.

## Definition of Done

- Baseline on the unmodified base: `make lint` and `make check` (114 tests
  expected). The coordinator measured `make selftest` at 48/48 on this base;
  this stage touches nothing it runs, so do not spend ten minutes re-measuring
  the baseline.
- Final: `make lint` passes.
- Final: `make check` passes, in under 30 seconds, with the new test count
  reported.
- Final: `make check` passes under real Python 3.9:
  `podman run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo
  docker.io/library/python:3.9-slim python -m unittest discover -s tests/host`.
  The tests that need `make` or `bash` may skip there; say which and why.
- Final: `make selftest` once, at the end, still 48/48. It must be untouched by
  this stage, and this proves it.
- The five mutations, each caught, each reverted with a matching checksum.
- `git status` clean after a `make check` run; `git diff python-port --stat`
  shows only allowed files.

## Commit

One commit, containing the change and `docs/stages/stage-05-REPORT.md`, with
exactly this subject line (a `Co-Authored-By:` trailer is expected):

```
test: pin the self-test's isolation, accounting, and cleanup
```

Stage files by path; never `git add -A`. Then
`git push -u origin stage-05-test-the-selftest`. Never push to `python-port` or
`main`.

## Report requirements

`docs/stages/stage-05-REPORT.md` must contain:

1. A checklist echo of "The change" and the Definition of Done.
2. Baseline and final gate outputs, verbatim.
3. The `make check` output with per-module test counts, and the 3.9 run.
4. The five mutations, tabulated: change, failing test, checksum before and
   after.
5. The ordered list of step titles and check names from the happy-path run.
6. Every behaviour of `smoke-container` you found that this prompt's list
   missed, and whether you pinned it.
7. `git diff python-port --stat`.
8. **Deviations**, numbered and honest, including the boring ones.
9. **Open questions**, including anything you pinned but believe is wrong.

## Blocked protocol

STOP and commit only the report, with a BLOCKED section giving the exact
failing output and why each permitted path is closed, if:

- a gate already fails on the unmodified base;
- a listed behaviour cannot be observed from outside the script without
  changing the script (say which, and what seam would be needed);
- an all-pass scenario cannot be built from canned replies;
- the change cannot be made inside the allowed files;
- any guardrail in `docs/stages/README.md` says STOP AND ASK.

A clean block is a successful execution.
