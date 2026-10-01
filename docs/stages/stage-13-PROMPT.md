# Stage 13 — Four distributions in CI, published, and documented

Branch name for this stage: `stage-13-four-distros-ci`. Base: `multi-distro`.

Read `docs/stages/README.md` first, including "Plan for multi-distro" and the
user's decisions recorded under it, and the reports of stages 11 and 12. The
README's gates, environment facts, and guardrails apply.

**First step, before anything else.** Run `git log --oneline -1` and **put that
line in your report**. If `docs/stages/stage-13-PROMPT.md` is missing, run
`git fetch origin && git merge --ff-only origin/multi-distro` and record it as a
Deviation. If it is still missing, invoke the Blocked protocol.

## Motivation (measured)

- Nothing in CI publishes an image. `ghcr.io/durantschoon/ros2-classroom:latest`
  was pushed by hand (`gh`/workflow history, 2026-09-29: no job with
  `packages: write`). A student choosing jazzy builds it locally, 10+ minutes.
- CI builds and smoke-tests only the default distribution.
- The unchanged Dockerfile built for humble, jazzy and kilted on 2026-09-29
  (trial builds, exit 0 each), and a humble trial desktop served noVNC in about
  6 s and ran `turtlesim_node` (`ros2 node list` showed `/turtlesim`). Nothing
  yet shows the *self-test* passing on those three; stage 12 reports jazzy's.
- The user's decisions (2026-09-29): CI publishes `:latest`, `:lyrical`,
  `:humble`, `:jazzy`, `:kilted` on pushes to `main`, for amd64 and arm64; the
  default distribution is smoke-tested on every push and all four nightly and
  on manual dispatch.
- Stage 11 rewrote the README's "Configuration" paragraph; it now says "Only
  the default is published prebuilt; a non-default one is built locally the
  first time", which this stage makes untrue. `docs/ros-distributions.md`
  still describes a two-branch choice that predates the table, and the
  README's "What is in the image" names only Lyrical.

## The change

### 0. `make check` on macOS (added 2026-10-01)

Measured by the coordinator on this host (macOS, see the README's environment
facts) at `7700c8e`: `make check` fails, 27 failures, all in
`tests/host/test_distros.py`, all the same assertion: the script names the
table by its resolved path (`scripts/distros` uses `Path(__file__).resolve()`),
`/private/tmp/ros2-host-test-…/tree/distros.json`, and the test expects the
unresolved `/tmp/ros2-host-test-…`. CI (Linux, no symlink) is green. The
coordinator's trial: comparing against `self.table_path.resolve()` at the
three `run.err.startswith(str(self.table_path) + ": ")` sites took the module
to 54/54 on this host. The script's behaviour is right (a student is told the
real path); fix the tests, nothing else. Record your own before-and-after
counts; do not copy these.

### 1. Per-distribution fixes, only if the self-test demands them

Run the isolated self-test (see "Running alongside stage 14") for humble,
jazzy and kilted (the default passed in stage 12). If one fails, fix the cause in the Dockerfile or
the image's scripts with the smallest distribution-conditional change, and say
in the report which package or behaviour differed. If none fails, change
nothing here and say so.

**Known failure to start from.** Stage 12 ran `make selftest ROS_DISTRO=jazzy`:
47/48, `FAIL no message crossed between compose services` (Cross-service DDS
discovery; the talker service started, nothing reached
`ros2 topic echo --once /chatter` in 30 s). Unexamined hypotheses from its
report: a `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` difference on jazzy, or the
talker starting slower than the suite's fixed wait. Find the cause before
fixing; a longer sleep is not a fix unless the evidence says timing.

### 1b. Follow-ups from stage 12's Open questions

- The busy-port hint in `scripts/compose-up` suggests
  `make up NOVNC_PORT=<p> && make open NOVNC_PORT=<p>`; for a non-default
  distribution it must carry `ROS_DISTRO=<name>` too, or it starts the
  default. (Its text is pinned by tests; changing it is authorized here.)
- `.env.example` has an uncommented `NOVNC_PORT=6080`, which since stage 12 is
  overridden by the table for make and `ros2.ps1`, and which would put every
  distribution on 6080 if it were not. Comment it out as an override, and
  document the precedence (command line, then environment, then the table;
  `.env`'s `NOVNC_PORT` only for plain `docker compose`).

### 2. `.github/workflows/docker-image.yml`

- `on:` gains `schedule` (one nightly cron) and a `workflow_dispatch` input
  `distros` (default `all`).
- **smoke**: on push and pull request, the default distribution as today. On
  schedule and dispatch, a matrix over the four names from `distros.json`
  (read in a first job, not hard-coded), each running
  `eval "$(./scripts/distros env)"` with `ROS_DISTRO` set, then the self-test.
  `fail-fast: false`.
- **build-arm64**: the same split: default on push, all four nightly.
- **smoke-podman** and **scan**: default only, unchanged.
- No publish job here: publishing lives in its own workflow, below.

### 2a. `.github/workflows/publish.yml` (new)

The user started this file (2026-09-29) and pushed a fuller version to
branch `publish-for-stage13` (`ec05ba2`, based on `main`). Its triggers and
first job are intact, but its `publish` job was truncated by a terminal copy
(lines cut at a fixed width, not valid YAML), so it is a reference for intent,
not a base: do not merge that branch. Write the file to this design, which the
coordinator sketched and the user accepted:

- **Triggers.** `workflow_run` on the "Docker image" workflow, `completed`,
  branches `[main]`, acting only when its conclusion is `success` (nothing
  untested is published); `workflow_dispatch` for a manual re-publish;
  `pull_request` for a **build-only dry run** (push nothing). Note, and say in
  the report: `workflow_run` fires only for workflow files on the default
  branch, so this workflow publishes for the first time after the
  multi-distro pull request merges; the pull request itself is where the dry
  run proves it.
- **Checkout** `github.event.workflow_run.head_sha` when present, else
  `github.sha`, so the tested commit is the one published.
- **A first job** reads the names and the default from `distros.json` with
  `jq` into outputs; **a matrix job** over those names, `fail-fast: false`.
- **Per distribution:** `./scripts/distros env --make >> "$GITHUB_OUTPUT"`
  with `ROS_DISTRO` set (its `NAME=value` lines are `$GITHUB_OUTPUT`'s
  format), then `docker/build-push-action` with `ROS_DISTRO` and
  `ROS_BASE_DIGEST` as build args, platforms `linux/amd64,linux/arm64`, tags
  `:<name>` and, for the default only, `:latest`; `push` true only for
  `workflow_run` and `workflow_dispatch`; GHA cache scoped per distribution.
- **arm64** by QEMU first. If a leg exceeds 90 minutes, report the time and
  stop: native per-architecture runners merged with
  `docker buildx imagetools create` is the alternative, and choosing it is the
  coordinator's call.
- Only `GITHUB_TOKEN`. The ghcr package was first pushed from the user's
  account, so the user may have to grant this repository write access in the
  package's settings ("Manage Actions access"); if a push is refused for
  that, it is the user's, not a Blocked finding about the code.

### 3. Docs

- `README.md` "Configuration" and the prose around `ROS_DISTRO`: the four
  distributions, `make distros`, the port each uses, each its own
  `/workspace`, and that published images make any of them a pull, not a
  build. Remove the "requires the matching base digest" instruction.
- `docs/ros-distributions.md`: rewrite around the table: why these four, what
  the default is and why, how to refresh digests (`make digest`), and keep the
  `guix` branch section, which is still true.
- `docs/cross-platform.md`: the same for `ros2.ps1`, one short paragraph.

## Running alongside stage 07

Revised 2026-10-01: stage 14 is not running. Stage 07 (the first-run question)
runs at the same time on another integration branch, `native-recipes`. Do not
touch `Makefile`, `scripts/workstation-help`, `ros2.ps1`, `.gitignore`,
`docs/roadmap.md`, `tests/host/fakes.py`, `tests/host/test_workstation_help.py`
or `tests/host/test_ros2_ps1.py`; none is in your allowed files anyway. Both
stages edit `README.md`, in different sections: keep your README edits to the
sections item 3 names. Your self-tests must not collide with stage 07's
(6097), the user's desktop (6080), or the distributions' ports (6082-6084).
Use exactly, per distribution:

```sh
SELFTEST_PROJECT=ros2-tutorials-st13 SELFTEST_NOVNC_PORT=6096 SELFTEST_ROS_DOMAIN_ID=13 IMAGE_NAME=ros2-tutorials-st13 make selftest ROS_DISTRO=<name>
```

one at a time, and remove the `ros2-tutorials-st13:*` images at the end.
**Never run `make selftest` without `IMAGE_NAME`** (README, "Every self-test,
by anyone, sets IMAGE_NAME").

**Pushing works on this host** (revised 2026-10-01; the old WSL host's SSH
agent refused to sign). Verification 3 is expected to run. If a push is
refused anyway, record "not run: push refused" with the error; that is not
Blocked. Use `actionlint` (a portable binary in your scratchpad; see the
README's environment facts) so the workflows are also checked locally.

**This host is arm64.** Local self-tests build `linux/arm64` images natively;
the amd64 side of each distribution is proved only by CI (the `smoke` job and
the publish dry run). Say so in the report rather than emulating amd64 here.

## Ground rules

- No behaviour change for the default distribution on a student's machine.
- The workflow never pushes from a pull request or a non-`main` push; a dry
  run is the only way it runs `publish` elsewhere.
- No secrets beyond `GITHUB_TOKEN`.

## Allowed files

- `.github/workflows/docker-image.yml`
- `.github/workflows/publish.yml` (new)
- `Dockerfile` and `docker/**` — only for fixes item 1 proves necessary
- `README.md`, `docs/ros-distributions.md`, `docs/cross-platform.md`, `.env.example`
- `scripts/compose-up`, `tests/host/test_compose_up.py` — the busy-port hint only
- `scripts/smoke-container`, `tests/host/test_smoke_container.py` — only if the jazzy cause is in the suite
- `tests/host/test_distros.py` — item 0's path comparison only
- `tests/host/**` — only for tests pinning an item-1 fix
- `docs/stages/stage-13-REPORT.md` (new)

## Tests and verification

1. The isolated self-test above for all four, one at a time; paste each
   summary line.
2. `actionlint` (or the lint job's own checks) passes on the workflow; paste
   the output. If `actionlint` is unavailable, say so.
3. Push the stage branch and open a draft pull request into `multi-distro`
   so `publish.yml`'s `pull_request` dry run runs; paste its job list with
   conclusions: every matrix leg green, both architectures built, nothing
   pushed (show the log line). Run `gh workflow run docker-image.yml --ref
   stage-13-four-distros-ci -f distros=all` for the four-distribution smoke
   matrix and paste that too. Close the draft pull request afterwards; the
   coordinator merges by the usual route.
4. `make lint`, `make check` as the gates.

## Definition of Done

- Baseline on the unmodified base: `make lint` and `make check`. Item 0's
  failures in `tests/host/test_distros.py` are expected there and are not a
  "gate already fails" block; any *other* baseline failure is.
- The gates; all four local self-tests pass; `actionlint` clean; the dry-run
  CI run green, or recorded as "not run: push refused".
- `git diff multi-distro --stat` shows only allowed files.

## Commit

```
ci: test all four distributions nightly and publish their images from main
```

Stage by path; quote the stat excluding the report; try to push
`stage-13-four-distros-ci` once (see above); never push `multi-distro` or
`main`.

## Report requirements

As stage 11's, plus each distribution's self-test summary, the dry-run CI
run's URL and job conclusions, and any item-1 fix with its evidence.

## Blocked protocol

As stage 11's. Also STOP if publishing needs a secret other than
`GITHUB_TOKEN`, a package-visibility change on ghcr, or anything only the
repository owner can grant: that is the user's.
