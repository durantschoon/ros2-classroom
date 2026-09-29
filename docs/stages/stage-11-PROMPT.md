# Stage 11 — Choose the ROS distribution with ROS_DISTRO, from one table

Branch name for this stage: `stage-11-distro-table`. Base: `multi-distro`.

Read `docs/stages/README.md` first, including "Added after v1.0" and "Plan for
multi-distro". Its gates, environment facts, and guardrails apply and are not
repeated here.

**First step, before anything else.** Run `git log --oneline -1` and **put that
line in your report**. If `docs/stages/stage-11-PROMPT.md` is missing, run
`git fetch origin && git merge --ff-only origin/multi-distro` and record it as a
Deviation. If it is still missing, invoke the Blocked protocol.

## Motivation (measured)

The user wants all four current ROS 2 distributions available: humble, jazzy,
kilted, and lyrical, which stays the default. Today one distribution is
hard-wired in five places (the Dockerfile's `ARG`s, `compose.yaml`'s defaults,
`.env.example`, `scripts/uninstall`, `ros2.ps1`), and choosing another means
running `make digest ROS_DISTRO=<name>` and pasting a digest into `.env` by
hand (`Dockerfile` lines 3-5, `.env.example` lines 5-8). Getting the pair wrong
builds one distribution's base under another's packages.

The user's decisions, recorded in the coordinator's session on 2026-09-29:

- One knob, `ROS_DISTRO`. No per-distribution command names.
- Each distribution's names carry its name; the default's are aliases that do
  not: image tag `latest` and compose project `ros2-tutorials`, which is what
  existing students already have, so none of them loses a volume.

The coordinator prototyped this on `spike/multi-distro` (local, `02ada84`; do
not merge or cherry-pick it, it is evidence). Measured there:

- The four digests, from `docker buildx imagetools inspect
  docker.io/library/ros:<distro>-ros-base` on 2026-09-29, and the Ubuntu each
  base reports in `/etc/os-release`:

  | distro | Ubuntu | digest |
  |---|---|---|
  | humble | 22.04 | `sha256:1813d3c85d7f96ff7d3012d865204583255740182db5d0065f8f8cd029a83138` |
  | jazzy | 24.04 | `sha256:c3706ef0a0aa45413c07803cf433602f543b22e45b4855f6fca955c2d8ecc4e8` |
  | kilted | 24.04 | `sha256:8e7b828a8f24416dd29fde258d81ad49c87fb9becc1289cf69c9d28d36fa78f9` |
  | lyrical | 26.04 | `sha256:0c19f326a339ed770ef1d4c0646a8b53bdb49dd5ff74b6de41ebdb8ac21e1806` (today's pin) |

- The unchanged Dockerfile builds for humble and for jazzy with those digests
  (`docker build --build-arg ROS_DISTRO=… --build-arg ROS_BASE_DIGEST=…`, exit
  0 each). Kilted's trial was still running when this was written; stage 13
  owns the builds, so do not re-run them here.
- GNU make does not pass command-line variables to `$(shell)` (make 4.3 here),
  so the Makefile must hand `ROS_DISTRO`, `ROS_BASE_DIGEST`, `IMAGE_TAG` and
  `COMPOSE_PROJECT_NAME` to the resolver explicitly. With that done,
  `$(foreach s,$(RESOLVED),$(eval export $(s)))` put all four in every
  recipe's environment, from the command line, the environment, or `.env`.
- `$(error …)` at parse time stopped every target on an unsupported name with
  the resolver's own message. Measured: `make up ROS_DISTRO=foxy` printed
  `ROS_DISTRO=foxy is not supported. Choose one of: humble jazzy kilted lyrical`.
- In Windows PowerShell 5.1, `ConvertFrom-Json` reads the table; `.env`
  parsing needs `-split '=', 2` and `Contains([string]$c)`, because .NET
  Framework has neither `String.Split(string, int)` nor `Contains(char)`.

## The change

### 1. `distros.json` (new, repository root)

```json
{
  "_comment": ["…what this is, and that `make digest` refreshes it…"],
  "default": "lyrical",
  "distros": {
    "humble":  {"ubuntu": "22.04", "digest": "sha256:1813…"},
    "jazzy":   {"ubuntu": "24.04", "digest": "sha256:c370…"},
    "kilted":  {"ubuntu": "24.04", "digest": "sha256:8e7b…"},
    "lyrical": {"ubuntu": "26.04", "digest": "sha256:0c19…"}
  }
}
```

Full digests from the table above. JSON because the host scripts are stdlib
Python 3.9, which has no TOML parser.

### 2. `scripts/distros` (new, host Python, stdlib, 3.9)

Finds the table and `.env` relative to its own location (`../distros.json`,
`../.env`). Three subcommands, a closed set:

- `distros env` prints `export NAME=value`, one per line, for a shell to eval;
  `distros env --make` prints bare `NAME=value` lines for the Makefile. The four
  names, in this order: `ROS_DISTRO`, `ROS_BASE_DIGEST`, `IMAGE_TAG`,
  `COMPOSE_PROJECT_NAME`.
  - `ROS_DISTRO` comes from the environment, else `.env` (compose's rules:
    comments and blank lines skipped, one pair of matching quotes stripped),
    else the table's default. An empty value counts as unset.
  - The name is parsed once into a table entry. An unsupported name exits 2
    with `ROS_DISTRO=<name> is not supported. Choose one of: <names, sorted>`
    on stderr and nothing on stdout.
  - Default distribution: `IMAGE_TAG=latest`, `COMPOSE_PROJECT_NAME=ros2-tutorials`.
    Any other: `IMAGE_TAG=<name>`, `COMPOSE_PROJECT_NAME=ros2-tutorials-<name>`.
  - `ROS_BASE_DIGEST`, `IMAGE_TAG` or `COMPOSE_PROJECT_NAME` already set to a
    non-empty value in the environment is passed through unchanged.
- `distros list` prints a header and one row per distribution: name, Ubuntu,
  image tag, project, and `(default)` on the default's row.
- `distros refresh` asks `scripts/base-image-digest <name>` (its sibling) for
  each distribution's current digest and prints one line each: `unchanged`,
  `<old> -> <new>`, or `kept <old> (could not fetch)`. It rewrites the table
  only when a digest changed, keeping `_comment` and a stable layout (sorted
  names, two-space indent, trailing newline), then says to rebuild. Any fetch
  failure exits 1.
- An unreadable or malformed table (bad JSON, missing key, a default not in
  the table) is one line naming the file, exit 1, no traceback. Usage errors
  exit 2. A closed stdout pipe is not an error.

### 3. `Makefile`

- Replace `ROS_DISTRO ?= lyrical` with the resolution measured above: call
  `./scripts/distros env --make` with the four variables handed over
  explicitly, stop with `$(error)` carrying the resolver's message when it
  prints nothing, and `export` each resulting `NAME=value`. Comment it.
- New target `distros`: `./scripts/distros list`, a blank line, then
  `Choose one with ROS_DISTRO=<name>, e.g.  make up ROS_DISTRO=jazzy`.
- `digest` becomes `./scripts/distros refresh`, echoed as make echoes recipes.
  Its comment says what it does now.
- `reset`'s three echo lines name `$(COMPOSE_PROJECT_NAME)` and
  `$(ROS_DISTRO)` instead of the literal `ros2-tutorials`.
- Add `distros` to `.PHONY`.

### 4. `compose.yaml`

`image: ${IMAGE_NAME:-ghcr.io/durantschoon/ros2-classroom}:${IMAGE_TAG:-latest}`,
with a one-line comment. The `ROS_DISTRO` and `ROS_BASE_DIGEST` build-arg
defaults stay as they are (lyrical and its digest): plain `docker compose`
without make keeps working exactly as today.

### 5. `Dockerfile` (comment only) and `.env.example`

The Dockerfile's header comment says the table pairs each distribution with
its digest, make and `ros2.ps1` pass the matching one, `make digest` refreshes
them, and these `ARG` defaults are the table's default. No instruction changes.

`.env.example`: `ROS_DISTRO=lyrical` stays; `ROS_BASE_DIGEST` becomes a
commented-out override; the comment names `make distros`, says each
distribution gets its own `/workspace`, and that plain `docker compose` needs
`eval "$(./scripts/distros env)"` first.

### 6. `scripts/workstation-help`

In "Start here", after `make image`: `make distros` — "List the ROS 2
distributions; pick one with ROS_DISTRO=name". `make digest`'s description
becomes "Refresh every distribution's base-image digest".

### 7. `ros2.ps1`

The same resolution, before `$Url` is computed: read `distros.json` with
`ConvertFrom-Json` and `.env` with the rules above; `ROS_DISTRO` from the
environment or a `ROS_DISTRO=` argument (the existing `NAME=value` handling
already sets `$env:`), else `.env`, else the default; unsupported ⇒ the same
message, exit 2; set the four `$env:` values the same way, keeping explicit
ones. A `distros` command prints the same table and the hint with
`.\ros2.ps1`. `help` lists `distros` and its last line names the distribution
and project. `reset`'s message names the project, like the Makefile's.
ASCII only; Windows PowerShell 5.1 compatible (see Motivation).

`ros2.ps1 uninstall` and every other script's distribution awareness are
stage 12. Leave them.

### 8. `.github/workflows/docker-image.yml`

Add `multi-distro` to `on.push.branches`. Nothing else in the file.

### 9. `README.md`

In "Configuration", a short paragraph: `ROS_DISTRO` picks one of four
distributions (`make distros`), lyrical is the default, each gets its own
`/workspace`, and a non-default one is built locally the first time. Stage 13
writes the fuller docs.

## Ground rules

- **The default is byte-for-byte unchanged**, apart from the lines named in
  Verification 3. A student with no `ROS_DISTRO` and no `.env` gets the same
  image, project, volumes and commands as today.
- The existing 209 tests pass unmodified, except: `tests/host/fakes.py`'s
  `COMPOSE_IMAGE` expression must match the new `image:` line (change only
  that expression and its error message), and the additions listed below.
- **Tests never write inside the repository.** `scripts/distros` finds its
  files from its own location, so tests copy it, `distros.json`, and (for
  `refresh`) a fake `base-image-digest` into a temporary tree. Makefile tests
  use a temporary copy of the `Makefile` and the scripts it calls; `ros2.ps1`
  tests that need a `.env` use a temporary copy of `ros2.ps1` and
  `distros.json`. Do **not** add an environment variable to relocate the table.
  If copying cannot work, that is a Blocked finding.
- This prompt authorizes exactly these additions to the student-facing surface:
  the `distros` make target and `ros2.ps1` command, the `distros` script, and
  the `IMAGE_TAG` compose variable. `ROS_DISTRO` already existed.
- Argv lists only; no `shell=True`, no `os.system`.

## Allowed files

- `distros.json` (new)
- `scripts/distros` (new)
- `Makefile`
- `compose.yaml`
- `Dockerfile` — the header comment only
- `.env.example`
- `scripts/workstation-help`
- `ros2.ps1`
- `.github/workflows/docker-image.yml` — the push branches only
- `README.md`
- `tests/host/test_distros.py` (new)
- `tests/host/test_ros2_ps1.py` — additions only
- `tests/host/test_workstation_help.py` — additions only
- `tests/host/fakes.py` — the `COMPOSE_IMAGE` expression only, plus additive helpers
- `docs/stages/stage-11-REPORT.md` (new)

Anything else is out of scope. Needing another file is a Blocked finding.

## Tests

Black-box, like every test here. Pin at least these; add any observable
behaviour this list misses.

`tests/host/test_distros.py`, the script through a temporary copy:

1. `env`, nothing set, no `.env`: lyrical, its digest, `latest`, `ros2-tutorials`.
2. `ROS_DISTRO=jazzy`: jazzy's digest, `jazzy`, `ros2-tutorials-jazzy`.
3. `ROS_DISTRO=lyrical` given explicitly: the default's aliases, as in 1.
4. `.env` with `ROS_DISTRO=kilted`, once bare and once quoted, and with a
   comment line: kilted. The environment beats `.env`. `ROS_DISTRO=` (empty)
   falls through to `.env`.
5. Explicit `ROS_BASE_DIGEST`, `IMAGE_TAG`, `COMPOSE_PROJECT_NAME` survive.
6. Unsupported, from the environment and from `.env`: exit 2, the exact
   message listing all four sorted names, nothing on stdout.
7. `--make`: exactly four `NAME=value` lines, no spaces, no `export`.
8. `list`: the header, four rows, `(default)` on lyrical's only.
9. `refresh`, fake sibling answering the same digests: every line `unchanged`,
   the table file byte-identical, exit 0.
10. `refresh`, one digest changed: that line shows old and new, only that
    entry changes in the file, `_comment` survives, the rebuild hint prints.
11. `refresh`, one fetch failing: `kept … (could not fetch)`, that entry
    unchanged, exit 1.
12. A malformed table, one case each (not JSON; no `distros`; default not in
    the table): one line naming the file, exit 1, no traceback.
13. No subcommand, an unknown one: exit 2, usage.
14. `list | head -0`: no traceback.

`tests/host/test_distros.py`, through a temporary copy of the `Makefile` with
`COMPOSE` naming a fake that records its environment:

15. `make ps ROS_DISTRO=jazzy`: the fake sees all four variables with jazzy's
    values.
16. `make ps` with nothing set: the default's values.
17. `ROS_DISTRO=jazzy make ps` (environment, not command line): the same as 15.
18. `make ps ROS_DISTRO=foxy`: non-zero, the resolver's message, the fake never
    called.
19. `make distros`: the table and the hint.
20. `make digest`: runs the refresh (fake sibling), echoing the command.
21. `make reset ROS_DISTRO=jazzy </dev/null`: the message names
    `ros2-tutorials-jazzy` and `jazzy`; nothing is removed.

`tests/host/test_distros.py`, consistency (reading files, not running them):

22. The Dockerfile's `ARG ROS_DISTRO` and `ARG ROS_BASE_DIGEST` defaults,
    `compose.yaml`'s `${ROS_DISTRO:-…}` and `${ROS_BASE_DIGEST:-…}` defaults,
    and `.env.example`'s `ROS_DISTRO` all equal the table's default and its
    digest.

`tests/host/test_workstation_help.py`, additions only:

23. The overview lists `make distros` in "Start here", after `make image`.

`tests/host/test_ros2_ps1.py`, additions only (they skip without `pwsh`, like
the rest of that module):

24. `ps ROS_DISTRO=jazzy`: the fake docker sees jazzy's four values.
25. `ps` with nothing set: the default's four values.
26. `ps ROS_DISTRO=foxy`: exit 2, the message, docker never called.
27. A temporary copy with a `.env` naming kilted: kilted's values; the
    environment still beats it.
28. `distros`: the table and the `.\ros2.ps1` hint.

The existing parity test then covers `make distros` ⇔ `.\ros2.ps1 distros`.

**Prove the tests have teeth.** Five temporary mutations, one at a time, each
caught, each reverted by copy-out and copy-back with a checksum:
`scripts/distros` gives the default distribution its own name as tag; lets
`.env` beat the environment; falls back to the default on an unsupported name;
rewrites the table when nothing changed. `Makefile` stops exporting `IMAGE_TAG`.

## Verification

Paste each output into the report.

1. **Python 3.9 for real**: `docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v
   "$PWD":/repo:ro -w /repo docker.io/library/python:3.9-slim python -m
   unittest discover -s tests/host`. Say which tests skip there and why.
2. **What compose actually sees.** For jazzy and for the default:
   `eval "$(./scripts/distros env)" && docker compose config --images` and
   `docker compose config | grep -E 'ROS_DISTRO|ROS_BASE_DIGEST'`, each in a
   fresh `bash -c` so nothing leaks between them.
3. **Nothing changed for the default.** With stdin from `/dev/null` and no
   `.env`: `make help`, `make engine`, and `make -n` of `up`, `shell`,
   `turtlesim`, `package PKG=x`, `build`, `run PKG=x NODE=y`, `test`, on the
   unmodified base and on your branch; `diff` them. Permitted differences: the
   `make distros` row and the `make digest` description in `make help`.
4. **Windows PowerShell 5.1**, if `powershell.exe` is reachable (this host is
   WSL): run `help`, `distros`, and `ps ROS_DISTRO=jazzy` through it against
   your worktree's `ros2.ps1` (a `\\wsl.localhost\…` path works), and paste the
   output. If it is not reachable, say so; do not block on it.
5. **The real suite**: one `make selftest` at the end, default distribution,
   48/48. `git status` clean afterwards.

## Definition of Done

- Baseline on the unmodified base: `make lint`; `make check` (209 tests; the
  coordinator measured 53 s, 15 skipped without `pwsh`). The coordinator
  measured `make selftest` on this base; do not re-measure it.
- Final: `make lint` passes, `scripts/distros` classified
  `python, host (3.9 grammar)`.
- Final: `make check` passes; report the count. Then
  `PWSH=/tmp/claude-1001/-home-durant-Repos-ds-ros2-turtlesim/fb2a37b5-5f7f-486f-8bc4-b59166072fa4/scratchpad/pwsh/pwsh make check`
  passes with the `ros2.ps1` tests running (PowerShell 7.6.6, installed by the
  coordinator; if that path is gone, say so and rely on CI). **Budget:**
  `test_distros.py` alone under 15 s.
- Tests 1-28 present; the five mutations caught; Verification 1-5 pass.
- `grep -n "shell=True\|os.system" scripts/distros` finds nothing.
- `git diff multi-distro --stat` shows only allowed files.

No other stage is running, so `make selftest` may use its defaults. Never touch
the project `ros2-tutorials`; it is the user's, and it is running.

## Commit

One commit, the change plus `docs/stages/stage-11-REPORT.md`, with exactly this
subject line (a `Co-Authored-By:` trailer is expected):

```
feat: choose the ROS distribution with ROS_DISTRO, from one table
```

Stage files by path; never `git add -A`. Quote the stat excluding the report:
`git diff multi-distro --stat -- . ':!docs/stages/stage-11-REPORT.md'`. Then
`git push -u origin stage-11-distro-table`. Never push to `multi-distro` or
`main`.

## Report requirements

`docs/stages/stage-11-REPORT.md` must contain:

1. The `git log --oneline -1` line from the first step.
2. A checklist echo of "The change" and the Definition of Done.
3. Baseline and final gate outputs, verbatim.
4. Tests 1-28 mapped to test names; the mutations tabulated with checksums;
   Verification 1-5 outputs.
5. Every message `scripts/distros` can print, verbatim.
6. The stat excluding the report.
7. **Deviations**, numbered and honest, including the boring ones.
8. **Open questions**: what you noticed and correctly did not do (for example,
   `compose-up` still inspects `:latest` for a non-default distribution; that
   is stage 12), and anything in this prompt you believe is wrong.

## Blocked protocol

STOP and commit only the report, with a BLOCKED section giving the exact failing
output and why each permitted path is closed, if:

- a gate already fails on the unmodified base;
- the default distribution's behaviour cannot be kept unchanged;
- the tests cannot avoid writing inside the repository without a new
  environment variable;
- the change cannot be made inside the allowed files;
- any guardrail in `docs/stages/README.md` says STOP AND ASK, other than the
  additions this prompt authorizes.

A clean block is a successful execution.
