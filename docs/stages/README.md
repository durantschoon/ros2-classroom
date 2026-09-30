# Stages

Delegated implementation happens here as numbered stages. A coordinator writes
each stage prompt and reviews the result; a `stage-executor` agent implements it
in an isolated git worktree. Executors never review themselves.

## This pipeline's branches

Stages run on an integration branch, never on `main`. Prompts are committed to
the integration branch, executors branch from it, and verified stages merge
back into it. The whole branch is promoted to `main` only when it is complete
and verified end to end, and that promotion is the user's call.

| Integration branch | Work | Stages | State |
|---|---|---|---|
| `python-port` | Shell scripts to Python | 01-06 | merged to `main` (`a24571d` before the v1.0 rewrite, `6533659` after), branch deleted |
| `native-commands` | Roadmap Stage 2, "What you would have run" | 07-10 | in progress; still on the pre-v1.0 history (see below) |
| `multi-distro` | Four ROS 2 distributions from one table | 11-13 | in progress |
| `pkg-helpers` | Student helpers inside the container (`pkg build --changed` first) | 14- | in progress; branched from `multi-distro` at stage 12, promoted after it |

**v1.0 and the redaction.** At the v1.0 release `main` was rewritten without
`docs/stages/`, and its commits got new hashes. The records of stages 01-07
survive on `native-commands`, which still carries the old history; what
happens to that branch is the user's decision, pending. `multi-distro` branches
from the rewritten `main`, so it starts `docs/stages/` again with this README
and its own stages. Process records live here until the next release (v1.1),
which redacts them again.

`native-commands` is a branch for a reason particular to it: stage 07 adds a
question whose second answer shows nothing until the recipes of stages 08 and
09 exist. `main` must never offer a student a choice that does nothing.

## Numbering

One global sequence: `stage-01`, `stage-02`, and so on, never reused. Each stage
has exactly two files:

- `stage-NN-PROMPT.md` — written by the coordinator, committed to the integration
  branch *before* the executor launches. Committing first reserves the number and makes
  the committed text canonical.
- `stage-NN-REPORT.md` — written by the executor, in the same single commit as
  its change.

## Gates

Every stage's Definition of Done uses these commands verbatim. This host now
has Docker Desktop (docker 29.8, compose 5.5.1) as well as rootless Podman, and
the Makefile prefers Docker. To exercise Podman instead, put its compose on
PATH first and pass `COMPOSE=podman-compose`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

| Gate | Command | Notes |
|---|---|---|
| Static | `make lint` | Validates `compose.yaml`, and lints every script by its shebang (Python 3.9 grammar for host scripts) |
| Fast tests | `make check` | Black-box tests against fakes; no engine needed. 251 tests, about 90 s, at `3e8974d` (209 and 53 s at `a072bec`). The 15 tests of `ros2.ps1` skip without PowerShell 7; `PWSH=/path/to/pwsh make check` runs them (about 79 s). CI's runners have `pwsh` |
| Full suite (end to end) | `make selftest` | Builds the image and exercises every documented workflow, about 10 minutes. 48/48 at `a24571d` |

`make selftest` runs as its own compose project so it can never touch real
work. Stages that may run at the same time must isolate it further, because
they would otherwise share the project, host port, and image tag:

```sh
SELFTEST_PROJECT=ros2-tutorials-stNN SELFTEST_NOVNC_PORT=60NN SELFTEST_ROS_DOMAIN_ID=NN IMAGE_NAME=ros2-tutorials-stNN make selftest
```

CI runs all of these on every push to the integration branch and on pull
requests: `lint` (with `make check`), `smoke`, `smoke-podman`, `build-arm64`,
and `scan`. The first fully green run was on `90998fd`.

## Environment facts executors need

- Rootless Podman 3.4.4 with podman-compose 1.6.0 (host: WSL 2, Ubuntu 22.04).
- zsh prints a harmless `add_to_front_of_path: no matches found` line on every
  command. Ignore it.
- The user may have their own workstation running as compose project
  `ros2-tutorials` on host port 6080. **Never stop, recreate, or exec
  destructively into it, and never touch its volumes.**
- podman-compose quirks are listed in `docs/host-requirements.md`. The ones that
  bite: `ps` takes no service argument; `logs` passes `--color`, which Podman 3
  rejects; services in a profile need `--profile` on every subcommand; `run`
  prints a container id rather than the command's output.

## Guardrails

The unifying principle: **information, once obtained, is never silently
discarded or degraded.** Each rule ends in STOP AND ASK: record the question in
the report's Blocked section instead of improvising an answer.

1. **Make illegal states unrepresentable.** Closed choices are enums or fixed
   sets, not free strings passed around and compared: the container engine
   (docker or podman), the build type (ament_cmake or ament_python), the
   template (pubsub or param). A new optional flag or make variable on the
   student-facing surface ⇒ STOP AND ASK.
2. **Functional core, imperative shell.** Pure functions take text or values
   and return text or values: shell quoting, the CMakeLists / setup.py /
   package.xml patchers, the stale-image comparison, the CNI line filter.
   Subprocesses and file I/O live at the edges, in `main()` or close to it.
3. **Explicit errors, not exceptions as control flow.** An expected condition
   (no engine found, desktop not running, package already exists) is an exit
   code and a plain-English message, never a traceback reaching a student.
   No bare `except:`.
4. **No primitive obsession.** Paths are `pathlib.Path`. Commands are argv
   lists, never shell strings. **`shell=True` ⇒ STOP AND ASK**: it reintroduces
   the quoting bugs this port exists to end.
5. **Closed sets stay closed.** The pkg subcommands, the templates, and the
   make targets are fixed. Adding one is an architect decision ⇒ STOP AND ASK.
6. **Parse, don't validate.** Arguments are parsed once, at the entry point,
   into typed values; nothing downstream re-checks them. When a tool's output
   (`podman inspect`, the registry's headers) is not in the expected shape,
   surface that — never guess ⇒ STOP AND ASK if you find yourself guessing.
7. **Student work is append-only.** Never overwrite or delete anything under a
   workspace or volume as a side effect: `pkg new` on an existing package
   refuses rather than clobbers, `init-workspace` never overwrites. Destructive
   operations stay explicit and confirmed. Changing either ⇒ STOP AND ASK.
8. **Behaviour is preserved exactly.** This is a port. User-visible output —
   messages, the printed commands, exit codes — stays the same wherever the
   suite, the docs, or a student's muscle memory depends on it, and printed
   commands stay paste-safe. An intentional user-visible change ⇒ STOP AND ASK.

## Coordinator practices

### Added after v1.0 (2026-09-29), before stage 11

Not a five-stage retro (none was due); lessons from one session that bypassed
the pipeline, recorded so it does not happen again:

- **Behaviour changes go through a stage, however they arrive.** Requests made
  in conversation ("add a help target", "fix the python side") drifted into
  the coordinator committing features straight to `main`: `ros2.ps1` help,
  full `make` parity for `ros2.ps1`, and the image-name fix, plus an
  unmerged prototype, `spike/multi-distro`. The coordinator commits directly
  only to `docs/stages/`; anything that changes what a script, the image, or
  CI does is a stage prompt on an integration branch.
- **Check CI before authoring a stage and before merging one.**
  `gh run list --branch <branch> --limit 3`. `main` was red for seven pushes,
  four before the session and three of its own (the image was renamed in
  `compose.yaml` and nothing else followed), and nobody looked.
- **Every self-test, by anyone, sets `IMAGE_NAME`.** Plain `make selftest`
  rebuilds `ghcr.io/durantschoon/ros2-classroom:latest`, the tag the user's
  running desktop was created from, so their next `make up` recreates it from
  a branch build. It happened in stage 11 (the executor's runs and the
  coordinator's review run, 2026-09-29) and stage 12's executor caught it
  (Open question 4). Always `IMAGE_NAME=ros2-tutorials-stNN make selftest`,
  and remove that image afterwards.
- **A prototype is evidence, not a base.** A prompt may cite a spike branch for
  design and measurements; the executor still implements from the prompt, with
  tests, and no stage merges the spike.

- Stage prompts land on the integration branch before launch: canonical text, and the
  number reserved.
- At most one in-flight stage touches any shared registration file. In this
  repo those are `Makefile`, `.github/workflows/docker-image.yml`, `Dockerfile`,
  `compose.yaml`, `scripts/smoke-container`, `scripts/workstation-help`,
  `ros2.ps1`, and `distros.json`. `tests/host/test_ros2_ps1.py` fails when a
  target in `make help` has no `ros2.ps1` command, so a stage that adds a make
  target also adds it to `ros2.ps1`, or another stage must first.
- **Tests before ports.** A script with no test coverage gets coverage in a
  tests-only stage *before* it is ported. Never change the tests and the code
  they judge in the same stage.
- Stages running concurrently get distinct `SELFTEST_PROJECT`,
  `SELFTEST_NOVNC_PORT`, `SELFTEST_ROS_DOMAIN_ID`, and `IMAGE_NAME`.
- Executors push their own stage branch, and on this host that succeeds. The
  coordinator still does every merge and every push of the integration branch.
- Review is the diff plus an independent rerun of the gates, never reading the
  report alone.
- A retro every 5 stages (before authoring stage 05, 10, …), plus whenever the
  user asks.

### Added by the retro before stage 05

Patterns across the reports of stages 01-04, and the rule each one became:

- **The executor's worktree was created at a stale commit in 4 of 4 stages.**
  Every prompt now opens with a "First step": check for the prompt file, and
  fast-forward to the integration branch on `origin` when it is missing.
- **The coordinator's own test payloads were wrong in 3 of 4 stages.** Stage
  01's negative control could not fail at the severity the same prompt
  specified; stage 03's "remove the tool from PATH" command left the tool on
  PATH; stage 04's example of a header the old code missed was one it matched.
  Each time the executor noticed and disclosed it. The rule: **the coordinator
  runs every negative control and every example before committing a prompt.**
  A payload that was never executed is a guess.
- **Commit messages.** Prompts specify the exact *subject line*. Executors add a
  `Co-Authored-By:` trailer under their own standing instructions; that is
  expected, not a deviation.
- **Reverting a mutation.** `git checkout --` restores the *committed* file,
  which during a port is the old implementation, not the executor's work.
  Mutations are reverted by copy-out and copy-back, confirmed with a checksum.
- **Never overlap a baseline or a mutation with a running self-test**; the
  self-test builds from the working tree.
- Stage files by path. Never `git add -A`: agent worktrees live inside this
  repository (`.claude/worktrees/` is ignored, but do not rely on that alone).
- Executors running extra, read-only verification beyond the prompt is
  welcome. It goes under Deviations like everything else.

More environment facts learned the hard way:

- A container started with `--network=none` makes freshly generated packages
  *fail* `pkg test`: some ament lint tests fetch XML schemas.
- zsh does not word-split unquoted variables. Loop over explicit words, or use
  `bash -c`.
- The local `python3` is 3.10. Real 3.9 is
  `podman run --rm -v "$PWD":/repo:ro -w /repo docker.io/library/python:3.9-slim …`.

## Lessons that belong elsewhere

A retro's lessons go to two places. What is true of *this repository* stays in
this file. What would be true of any repository is a lesson about shared
tooling that lives elsewhere, and it is filed privately, outside this
repository, never here. This repository holds only its own process records.

## Backlog from the reports' Open questions

Unresolved, and deliberately not slipped into a port stage:

- Lint the permanent shell files at `--severity=info`? It needs six
  behaviour-neutral `# shellcheck disable=` comments.
- CI installs apt's shellcheck (0.9.x); local runs pin v0.11.0. Findings can
  differ.
- `lint-scripts` finds its engine through `compose-command`, so a host with a
  bare engine and no compose cannot lint shell files.
- `install-ros-packages` runs `sudo apt-get update` without echoing it, against
  the no-black-box rule.
- `tutorial list` prints the workspace root when `src/.git` exists. Preserved
  by the port; probably a bug.
- `pkg new` accepts a name beginning with `--`.
- `run-quiet` handles SIGINT but not SIGTERM or SIGHUP.
- `compose-up` reads `COMPOSE_PROJECT_NAME` to find the desktop but does not
  pass it on, so the project is decided in two places.
- `quote()` is duplicated in `pkg` and `tutorial`; sharing it needs a Dockerfile
  change.
- From stage 06: `make check` now takes about 27 s against a 30 s budget,
  because it runs the whole self-test against fakes some thirteen times. Share
  scenarios between tests, or raise the budget.
- From stage 06: `tests/host/test_smoke_container.py` still links `grep`,
  `tail`, `awk` and friends for a script that no longer calls them, and carries
  a dead `SESSION_START`. Harmless; tidy in a tests-only change.
- From stage 06: when the desktop never becomes ready, the suite still exits
  with no summary line, the same "stops counting" shape the port removed from
  the missing-engine path.
- From the stage 06 review: neither the shell suite nor the port tears down
  when its output pipe closes early (`make selftest | head`). Pre-existing;
  the containers are left running until the next run.
- **No real `docker compose` has ever run this project.** Every real run so far
  is Podman on WSL. The macOS section of `docs/platform-test-matrix.md` is
  where that gets tested.

## Plan for multi-distro (integration branch `multi-distro`)

One knob, `ROS_DISTRO`, chooses among humble (Ubuntu 22.04), jazzy (24.04),
kilted (24.04) and lyrical (26.04, the default). A table, `distros.json`,
pairs each with the digest of `ros:<distro>-ros-base`; the default's names are
the aliases (`:latest`, project `ros2-tutorials`), so existing students keep
their work. Each other distribution gets its own image tag and compose
project, hence its own `/workspace`. The prototype is `spike/multi-distro`
(local only, `02ada84`); trial builds of humble, jazzy and kilted from the
unchanged Dockerfile are recorded in stage 11's prompt.

| Stage | Kind | Scope | State |
|---|---|---|---|
| 11 | Feature | `distros.json`, `scripts/distros`, Makefile and compose wiring, `make distros`, `make digest` refreshes the table; the same resolution in `ros2.ps1` (the parity test requires it); CI runs on this branch | merged as `3e8974d` (reviewer: mechanically clean; coordinator reran lint, check with pwsh, and selftest 48/48) |
| 12 | Feature | `compose-up`, `uninstall` (both `scripts/uninstall` and `ros2.ps1 uninstall`) and `smoke-container` know about every distribution; the shell prompt names the distribution, `(jazzy) ros@…:/workspace$`, for the default too (`docker/bashrc.d/ros-workspace.sh`); a noVNC port per distribution, so several run at once: each table entry becomes (Ubuntu, port, digest), lyrical 6080 (the default keeps today's port), humble 6082, jazzy 6083, kilted 6084, 6081 left to the self-test; the resolver exports `NOVNC_PORT` (an explicit one wins) and refuses a table with a shared port or 6081; `distros` lists the port (user's decision, 2026-09-29) | merged as `a38ba0d` + report fix `8d57310` (reviewer: one defect, the report's missing messages section, fixed; coordinator reran lint, check with pwsh, isolated selftest 48/48). Jazzy self-test 47/48 (cross-service DDS) handed to stage 13 |
| 13 | Feature | Per-distribution Dockerfile fixes if needed (none so far: humble, jazzy and kilted trial builds all exited 0 from the unchanged Dockerfile on 2026-09-29); CI smoke-tests the default on every push and all four nightly and on manual dispatch; CI publishes `:latest`, `:lyrical`, `:humble`, `:jazzy`, `:kilted` to ghcr on pushes to `main` (amd64 and arm64; needs `packages: write`); docs | authored |

User decisions, 2026-09-29: CI publishes all four tags on `main`; the default
is smoke-tested on every push, all four nightly; the branch reaches `main` by a
pull request the coordinator opens and the user merges; after multi-distro the
quiz comes first, which first needs the user's decision on `native-commands`
(it still carries pre-v1.0 history).
After stage 13 merges, the coordinator deletes the user's reference branch
`publish-for-stage13` from origin (the user's instruction, 2026-09-29).

These share `Makefile`, `compose.yaml` and the workflow, so they run one at a
time.

## Ideas from the user, not yet staged (2026-09-29)

Recorded as they arrived; each needs a prompt before anything is built.

- **Quiz on the native commands** (belongs to `native-commands`, whose goal is
  command memorisation): "what would you type to create a package?", answered
  without this repo's helpers. Proposed shape: parse the answer with shell
  word-splitting, check the command path and positionals in order and flags
  as a set, compare flag values, accept `--flag=value`; feedback per part,
  then a hint ladder (which part, then the shape, then the answer). The answer
  key is the exact command `pkg` prints, tied by a test so the quiz cannot
  teach something else. `pkg quiz`, run in the desktop's terminal.
- **Quiz on general knowledge, not only commands**: where to run
  `colcon build` yourself (the workspace root, `/workspace`, never `src/` or a
  package directory, which scatters `build/ install/ log/` in the wrong
  place); which shells must `source install/setup.bash`, and why a shell that
  was already open does not see a new package; what `--symlink-install`
  changes.
- **Rename a node from the desktop menu**: a right-click entry opens a dialog
  for the new name, runs the node, and prints the real command, e.g.
  `ros2 run turtlesim turtlesim_node --ros-args -r __node:=my_turtle` (ROS 2
  needs `--ros-args -r`; a bare `__node:=` is ROS 1). A quiz item later.
  Needs a dialog tool in the image (zenity or similar: a Dockerfile change).
- **Colour for `ros2 node info`.** Nothing released does it: ros2cli PR
  #1248 (colour helpers, `node info` first) was open and Rolling-only on
  2026-09-29; ros2tree and the TUIs (rtui, rosgraph_tui) are different
  commands, which would teach students a command a plain install lacks. So a
  filter, keeping the native command in their hands:
  `ros2 node info /turtlesim | ros2-color`, colouring section headers, names
  and types; plain when not a terminal or when `NO_COLOR` is set; unknown
  lines passed through untouched. Tested against all four distributions'
  output, so after multi-distro. Drop it where #1248 ships.
- **Rebuild only what changed**: colcon + CMake already rebuild changed files
  within a package, and `--symlink-install` Python needs none; the gain is
  skipping unchanged packages. `pkg build --changed`: compare sources against
  each package's install stamp, run and print
  `colcon build --packages-above <changed>`.
- **Add a dependency**: `pkg add-dep PKG LIB` edits `package.xml` (ElementTree)
  and `CMakeLists.txt`. Jinja renders the whole file at `pkg new` (order fixed:
  `find_package`, executable, linking, `install(TARGETS)`, `ament_package()`
  last); after that it renders only a marked, tool-owned block and splices it
  in, so a student's own edits are never regenerated away (guardrail 7), and
  the diff is printed. Distribution-aware: Kilted deprecates
  `ament_target_dependencies` for `target_link_libraries(… pkg::target)`, so
  this follows multi-distro. Needs `python3-jinja2` in the image. The native
  form to teach alongside: `ros2 pkg create --dependencies`.

## Backlog from the reports' Open questions (multi-distro)

From stage 11, for stage 12 unless noted:

- `scripts/distros -h`/`--help` was added beyond the prompt and has no test.
- `ros2.ps1` validates the table more coarsely than `scripts/distros` (no
  digest shape); a shared fixture of malformed tables run through both would
  pin them together.
- An unsupported `ROS_DISTRO` in `.env` stops every target, `make distros`
  and `make help` included, so the way to recover is to edit `.env` first.
- Plain `docker compose` with `ROS_DISTRO=jazzy` in `.env` and no `eval`
  still pairs jazzy with the default's digest and tag: documented in
  `.env.example`, not prevented.
- A student's old `.env` pinning `ROS_BASE_DIGEST` is now overridden by the
  table (make and `ros2.ps1` export it). Identical today; after a refresh the
  table wins. Probably right; say so in stage 13's docs.
- Inline comments in `.env` (`ROS_DISTRO=jazzy  # mine`) are not stripped;
  the result is a loud "not supported", never a silent wrong choice.
- `make check` grew to about 90 s (each `make` parse starts one more
  `python3`, and the self-test's tests parse the Makefile many times).
- make 3.81 (macOS) untested; the resolver uses only functions 3.81 has.

## Plan for roadmap Stage 2, "What you would have run"

| Stage | Kind | Scope | State |
|---|---|---|---|
| 07 | Feature | The first-run question, its saved answer, `make choose`, and the `EXPLAIN` override | authored |
| 08 | Feature | The recipe data model and platform detection; the self-test pins `EXPLAIN=0` | planned |
| 09 | Feature | Linux/apt recipes, verified for real in CI; targets print them | planned |
| 10 | Feature | macOS and WSL recipes, entering as `verified-by-hand` or `community-reported` (retro first) | planned |

These are new features, not ports, so guardrail 8 reads differently: existing
behaviour is preserved exactly for a student who answers 1 or is never asked.
A new script and its tests may arrive in the same stage; "tests before ports"
is about code that already exists.

## Plan for the Python port

| Stage | Kind | Scope | Runs | State |
|---|---|---|---|---|
| 01 | Infra | Lint by shebang: real shellcheck and a Python 3.9 gate, locally and in CI; CI triggers that actually fire | alone | merged |
| 02 | Tests only | Black-box tests for the host scripts; smoke coverage for `tutorial` and `init-workspace` | alone | merged |
| 03 | Port | Container scripts: `pkg`, `tutorial`, `init-workspace`, `install-ros-packages` | parallel with 04 | merged |
| 04 | Port | Host scripts: `compose-command`, `compose-up`, `check-host`, `run-quiet`, `open-url`, `base-image-digest` | parallel with 03 | merged |
| 05 | Tests only | Black-box tests for `scripts/smoke-container` itself: isolation, accounting, cleanup (retro first) | alone | merged |
| 06 | Port | `scripts/smoke-container`, last | alone | merged |

The suite's port was planned as stage 05. It became stage 06 when the rule
"tests before ports" was applied to the suite itself: it judged every other
port, and nothing judged it.

The same names throughout, with no `.py` extension, so the Makefile, Dockerfile,
CI, and docs need no renames. What stays shell, and why, is in
[../roadmap.md](../roadmap.md#language-python-replaces-shell).
