# Stage 12 — Every script knows every distribution; a port and a prompt per distribution

Branch name for this stage: `stage-12-every-script-every-distro`. Base: `multi-distro`.

Read `docs/stages/README.md` first, including "Added after v1.0" and "Plan for
multi-distro", and `docs/stages/stage-11-REPORT.md`, whose resolver this stage
extends. The README's gates, environment facts, and guardrails apply.

**First step, before anything else.** Run `git log --oneline -1` and **put that
line in your report**. If `docs/stages/stage-12-PROMPT.md` is missing, run
`git fetch origin && git merge --ff-only origin/multi-distro` and record it as a
Deviation. If it is still missing, invoke the Blocked protocol.

## Motivation (measured)

Stage 11 made `ROS_DISTRO` choose the image, the base digest and the compose
project. Three scripts still assume one distribution, and the user has asked
for two more things:

- `scripts/compose-up` inspects `…:latest` whatever the distribution, so for
  jazzy it compares the wrong image and never notices a rebuild.
- `scripts/uninstall` and `ros2.ps1 uninstall` find only the current
  project's containers and volumes and the default's image: a student who
  tried jazzy and then uninstalls keeps `ros2-tutorials-jazzy_*` volumes and a
  4 GB image. (Trial images measured on 2026-09-29: humble 3.71 GB, jazzy
  4.03 GB, kilted 4.15 GB.)
- `scripts/smoke-container` inspects `…:latest` for the image-user check, so
  `make selftest ROS_DISTRO=jazzy` would check the default's image.
- **One port per distribution** (the user, 2026-09-29), so several desktops
  run at once. Measured on 2026-09-29: the humble, jazzy and kilted trial images
  ran side by side with the user's lyrical desktop, on host ports
  6091/6092/6093 → 6080 in each container, each answering on its own port.
- **The distribution in the shell prompt** (the user, 2026-09-29): nothing in
  a desktop terminal says which distribution it is, and with several desktops
  open that is the question a student gets wrong.

## The change

### 1. `distros.json` and `scripts/distros`: a port per distribution

Each entry gains `"port"`: lyrical 6080 (the default keeps today's port),
humble 6082, jazzy 6083, kilted 6084. 6081 stays the self-test's.

- Parsing rejects, as a malformed table (stage 11's message shape, exit 1):
  a port that is not an integer in 1024-65535, two distributions sharing a
  port, and any distribution on 6081.
- `env` prints a fifth variable, `NOVNC_PORT`, after the other four; an
  explicit non-empty `NOVNC_PORT` in the environment wins.
- `list` gains a `PORT` column between `UBUNTU` and `IMAGE TAG` (today's
  header: `DISTRO  UBUNTU  IMAGE TAG  COMPOSE PROJECT`).
- `refresh` keeps ports untouched.

- `-h`/`--help`, which stage 11 added beyond its prompt, is kept and gets a
  test (stage 11 Open question; the reviewer flagged it as untested).

### 2. `Makefile`

`NOVNC_PORT ?= 6080` goes; the resolver supplies it, handed over explicitly
like the other four. `URL` and `DESKTOP_URL` are defined after the resolution.
So `make open ROS_DISTRO=jazzy` opens `http://localhost:6083/…`.

### 3. `ros2.ps1`

The same: `NOVNC_PORT` from the table unless set; `$Url` computed after
resolution; `distros` shows the port. Its table check becomes as strict as
`scripts/distros`' (stage 11 Open question 10): digest shape, name shape,
and the port rules above, with the same meaning, so a hand-edited table
cannot be accepted by one and refused by the other. `uninstall` finds, for every
distribution in the table: its project's containers, volumes and network
(`ros2-tutorials` for the default, `ros2-tutorials-<name>` otherwise, plus the
self-test's), its image tag (`latest` for the default, `<name>` otherwise), the
legacy `ros2-tutorials:<name>` tag, and its base `docker.io/library/ros@<digest>`.
The listing, the confirmation and the removal order are unchanged.

### 4. `scripts/compose-up`

- The image it inspects is `${IMAGE_NAME:-default}:${IMAGE_TAG:-latest}`.
- `port_to_suggest` skips 6081 **and every port in the table**, so a busy
  port never suggests another distribution's. It reads the table relative to
  its own location; an unreadable table means "skip 6081 only", as today.

### 5. `scripts/uninstall`

The same survey as `ros2.ps1 uninstall` above, from the table (relative to its
own location). An unreadable table falls back to today's behaviour: the
environment's project and image, the Dockerfile's base. Removal order, the
confirmation word and `YES=1` are unchanged. The docstring says it covers
every distribution.

### 6. `scripts/smoke-container`

The image-user check inspects `${IMAGE_NAME:-default}:${IMAGE_TAG:-latest}`.
Nothing else changes: it keeps its own project and port 6081 whatever the
distribution.

### 7. `docker/bashrc.d/ros-workspace.sh`

- Interactive shells get the distribution in front of the prompt:
  `(jazzy) ros@<host>:/workspace$`, for the default too. Only when
  `ROS_DISTRO` is set and `PS1` is set (interactive); never twice (the file is
  already guarded against double sourcing).
- The `make()` explainer's target list gains `distros` and `uninstall`.

## Ground rules

- **The default distribution is unchanged** apart from the prompt prefix and
  the lines in Verification 3: port 6080, project, volumes, image.
- The existing tests pass unmodified except where they pinned the single
  distribution this stage removes (list each such edit, with the reason, in
  the report).
- Tests never write inside the repository; scripts find the table relative to
  themselves, so tests copy what they run into a temporary tree. No new
  environment variable relocates anything.
- No new make target, no new `pkg` subcommand, no new student-facing variable
  beyond the port the user decided.

## Allowed files

- `distros.json`, `scripts/distros`
- `Makefile`
- `ros2.ps1`
- `scripts/compose-up`, `scripts/uninstall`, `scripts/smoke-container`
- `docker/bashrc.d/ros-workspace.sh`
- `tests/host/test_distros.py`, `tests/host/test_compose_up.py`,
  `tests/host/test_uninstall.py`, `tests/host/test_smoke_container.py`,
  `tests/host/test_ros2_ps1.py` — additions, plus the single-distribution
  edits the ground rules allow
- `tests/host/fakes.py` — additive
- `docs/stages/stage-12-REPORT.md` (new)

## Tests

1. The table: each malformed-port case rejected (not an integer, out of
   range, shared, 6081), one test each.
2. `env` prints five lines, `NOVNC_PORT` last, per distribution; an explicit
   `NOVNC_PORT` wins; `list` shows the port column.
3. Through a temporary Makefile: `make ps ROS_DISTRO=jazzy` gives the fake
   `NOVNC_PORT=6083`; `make -n open ROS_DISTRO=jazzy` names port 6083; the
   default gives 6080.
4. `compose-up` with `IMAGE_TAG=jazzy` inspects `…:jazzy`; unset, `…:latest`.
5. `compose-up`'s busy-port hint from 6082 suggests neither 6083 nor 6084 nor
   6081 (so 6085); from 6080, 6085 as well.
6. `uninstall`, a fake engine holding one of everything for each of the four
   distributions plus the self-test: all listed with sizes, removed in order,
   one engine call per kind. With an unreadable table: today's behaviour.
7. `smoke-container` with `IMAGE_TAG=kilted` inspects `…:kilted`.
8. `ros2.ps1` (skips without `pwsh`): `open`'s URL and the fake's
   `NOVNC_PORT` per distribution; `uninstall` with a fake docker holding each
   distribution's objects lists them all; `distros` shows ports.
9. A shared fixture of malformed tables (the cases in test 1 plus stage 11's:
   bad digest, bad name, default missing), each run through `scripts/distros`
   and through `ros2.ps1` (skips without `pwsh`): both refuse every case.
10. `scripts/distros -h` and `--help`: the usage line, exit 0.
11. The prompt: `bash -ic 'echo "$PS1"'` in a temporary HOME, with
   `ROS_DISTRO=jazzy` and the file sourced, starts with `(jazzy) `; sourced
   twice, still once; non-interactive, `PS1` untouched.

**Mutations**, each caught, reverted by copy-back with a checksum: allow a
shared port; stop exporting `NOVNC_PORT`; `port_to_suggest` forgets the
table; `uninstall` surveys only the current distribution; the prompt prefix
applied twice.

## Verification

1. Python 3.9 for real (the stage 11 command).
2. **Two desktops at once, for real:** `make up` (default) and
   `make up ROS_DISTRO=jazzy` — but **not** as `ros2-tutorials`, which is the
   user's: run both with `COMPOSE_PROJECT_NAME=st12-a` / `st12-b` and
   `NOVNC_PORT=6085` / `6086`, `curl` each `vnc.html`, run
   `ros2 run turtlesim turtlesim_node` in each via `make shell`-style exec, and
   show `ros2 node list` in each; then `make down` both with the same
   variables and show no `st12-*` containers or volumes remain.
3. `make help`, `make -n up`, `make -n open` for the default: diff against the
   base; permitted: nothing.
4. `make selftest` (default) 48/48, then
   `make selftest ROS_DISTRO=jazzy` and report its result. A jazzy failure is
   reported, not fixed: stage 13 owns per-distribution fixes.

## Definition of Done

- Baseline, final `make lint`, `make check` (and with `PWSH=…`), as in stage
  11; report counts and times. The baseline is 251 tests, about 90 s at
  `3e8974d` (skipped=30 without `pwsh`, 7 with).
- Tests and mutations as above; Verification 1-4.
- `git diff multi-distro --stat` shows only allowed files.

## Commit

```
feat: every script knows every distribution, each on its own port and prompt
```

Stage by path; quote the stat excluding the report; push
`stage-12-every-script-every-distro`; never push `multi-distro` or `main`.

## Report requirements

As stage 11's, plus: the list of single-distribution test edits and why, and
the jazzy self-test result verbatim.

## Blocked protocol

As stage 11's. Also STOP if the prompt prefix cannot be applied without
changing non-interactive shells, or if two desktops cannot run at once without
touching the user's `ros2-tutorials` project.
