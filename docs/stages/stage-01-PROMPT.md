# Stage 01 — Lint every script by shebang, and make CI actually run

Branch name for this stage: `stage-01-lint-by-shebang`. Base: `python-port`.

Read `docs/stages/README.md` first. Its gates, environment facts, and
guardrails apply to this stage and are not repeated here.

## Motivation (measured)

1. **CI has never run.** `.github/workflows/docker-image.yml` triggers on
   `push: branches: ["docker/**"]`, `pull_request`, and `workflow_dispatch`.
   The remote's branches are `guix`, `main`, `plan/cross-platform-ros-tutorials`,
   and `podman`, and no pull request has been opened. Every check in that
   workflow has never executed.
2. **No script has ever been linted.** `shellcheck` is not installed on the
   development host, and `make lint` prints `shellcheck not installed; skipping
   script lint` and exits 0. A skipped check is indistinguishable from a pass.
3. **The Python 3.9 constraint is unchecked.** `docs/roadmap.md` requires host
   scripts to be stdlib-only and Python 3.9-compatible, because macOS's Command
   Line Tools ship 3.9. Stages 03–05 will port scripts to Python; nothing today
   would catch 3.10+ syntax.
4. **The lint file list is a contention point.** It is spelled out by hand in
   two shared registration files, the Makefile's `lint` target and the CI
   workflow. Each port stage would have to edit both, which would stop 03 and
   04 from running in parallel. Discovering scripts by shebang removes that.

## The change

### 1. `scripts/lint-scripts` (new, Python)

A Python 3.9-compatible, stdlib-only script: `#!/usr/bin/env python3`, no `.py`
extension, executable.

**Discovery.** Candidates are every regular file directly in `scripts/` and
`docker/scripts/`, plus `docker/entrypoint.sh`, every `docker/bashrc.d/*.sh`, and
`docker/desktop/openbox-autostart`.

**Classification**, by first line:

- a shebang naming `sh` or `bash` → shell
- a shebang naming `python3` → Python
- `docker/bashrc.d/*.sh`, which are sourced and have no shebang → bash, by path
- anything else → a lint **failure** naming the file. An unclassifiable file in
  these directories is a finding, not something to skip.

Model the classification as a closed type (an `Enum`), not strings compared
later (guardrail 1).

**Shell files** are checked with `shellcheck --severity=warning`, passing
`--shell=bash` for the sourced drop-ins.

- **Enforced** — a finding fails the lint: the files that stay shell
  permanently, namely `docker/entrypoint.sh`, `docker/bashrc.d/*.sh`, and
  `docker/desktop/openbox-autostart`.
- **Advisory** — findings are printed, clearly labelled advisory, and do not
  fail the lint: every other shell file. These are slated for the Python port;
  fixing them now would be wasted work. Keep the list of enforced paths as one
  named constant with a comment pointing at `docs/roadmap.md`. A file that has
  already been ported is Python by shebang, so it is never looked up in that
  list.

**Where shellcheck comes from.** Use `shellcheck` from PATH when present.
Otherwise run it through the container engine that `scripts/compose-command
--engine` reports: `<engine> run --rm -v <repo>:/mnt:ro -w /mnt <image> …`.
Pin the image to a **version tag** you have confirmed exists on Docker Hub
(`docker.io/koalaman/shellcheck:vX.Y.Z`, newest stable), and record the tag you
chose in the report. If neither a local shellcheck nor an engine is available,
**fail** with a message saying shell linting could not run. It must never
report success without having run (motivation 2).

**Python files.**

- Files under `scripts/` (host side): parse with
  `ast.parse(source, filename, feature_version=(3, 9))`. A syntax error there
  means the file needs Python newer than 3.9, and that is a failure.
- Files under `docker/scripts/` (container side, which runs Ubuntu Resolute's
  Python): plain `ast.parse` with the running interpreter.

**Output.** One line per file giving its path, classification, and result
(`ok`, `FAIL`, or `advisory`), then a summary with counts. Exit 0 only when
there are no failures. Keep the checking logic in pure functions that take text
and return results, with process spawning at the edges (guardrail 2). Build
commands as argv lists; `shell=True` is forbidden (guardrail 4).

### 2. Makefile `lint` target

Replace the hand-listed shellcheck invocation with `./scripts/lint-scripts`,
keeping the existing `compose config` check first. Update the `make lint` line
in `make help` to describe what it now does, e.g. "Validate compose.yaml and
lint every script (shellcheck, Python 3.9)". Change nothing else in the
Makefile.

### 3. CI workflow

- **Triggers:** `push` on branches `main`, `python-port`, and `docker/**`. Keep
  `pull_request` and `workflow_dispatch` as they are.
- **lint job:** replace the hand-listed shellcheck step with a step that runs
  `scripts/lint-scripts` under **Python 3.9** (`actions/setup-python` with
  `python-version: "3.9"`), after installing shellcheck with apt as the job does
  today. Running the linter itself on 3.9 proves the linter is 3.9-compatible.
- Leave the `compose config` and hadolint steps, and every other job, exactly
  as they are.

### 4. README

In the README's commands table, update only the `make lint` row's description
to match the new `make help` text.

## Ground rules

- Behaviour of every existing script is unchanged: this stage adds a linter and
  rewires two callers of it.
- The advisory shell findings are information for stages 03–05. Record them
  verbatim in the report (see Report requirements); do not fix them.
- If shellcheck reports a finding in an **enforced** file, fix it minimally and
  disclose each fix as a Deviation. A fix that would change behaviour is a
  Blocked finding.
- You will not be able to observe CI, since your push is expected to fail. Do
  not claim CI results.

## Allowed files

- `scripts/lint-scripts` (new)
- `Makefile` — the `lint` target and its `make help` line only
- `.github/workflows/docker-image.yml` — the `on:` block and the `lint` job only
- `README.md` — the `make lint` row of the commands table only
- `docker/entrypoint.sh`, `docker/bashrc.d/ros-workspace.sh`,
  `docker/desktop/openbox-autostart` — minimal shellcheck-driven fixes only, if
  shellcheck requires any
- `docs/stages/stage-01-REPORT.md` (new)

Anything else is out of scope. Needing another file is a Blocked finding.

## Tests

Run each of these and paste its output into the report. The negative controls
(4–7) are temporary edits: make them, capture the output, then revert, and
confirm with `git status` that nothing from them remains before you commit.

1. `./scripts/lint-scripts` on the finished stage: exit 0, with every
   discovered file listed and classified.
2. The classification matches reality. Enumerate which files came out shell
   (and whether each is enforced or advisory) and which came out Python.
   `scripts/lint-scripts` must appear in its own output as Python, with the 3.9
   check applied.
3. `make lint`: exit 0.
4. **Negative control, enforced shell.** Append `rm $1` to
   `docker/desktop/openbox-autostart`. `./scripts/lint-scripts` exits non-zero
   and names that file. Revert.
5. **Negative control, Python 3.9.** Create `scripts/zz-negative-control` with a
   `#!/usr/bin/env python3` shebang containing a `match` statement.
   `./scripts/lint-scripts` exits non-zero and names the file. Delete it.
6. **Negative control, unclassifiable.** Create `scripts/zz-negative-control`
   with the shebang `#!/usr/bin/env perl`. `./scripts/lint-scripts` exits
   non-zero and names the file. Delete it.
7. **Negative control, no linter available.** Run `./scripts/lint-scripts` with
   a `PATH` that contains neither `shellcheck` nor `docker` nor `podman`. It
   exits non-zero with a message saying shell linting could not run.
8. The CI workflow is still valid YAML:
   `python3 -c 'import yaml,sys; yaml.safe_load(open(".github/workflows/docker-image.yml"))'`.

## Definition of Done

- Baseline measured on the unmodified base before any change: `make lint`
  (exit status and output) and `make selftest` (pass/fail counts).
- Final: `make lint` exits 0.
- Final: `make selftest` passes with the same count as the baseline (32/32
  expected). This stage runs alone, so the default self-test project and port
  are fine.
- Tests 1–8 pass, with their outputs in the report.
- `git diff python-port --stat` shows only allowed files.

## Commit

One commit, containing the change and `docs/stages/stage-01-REPORT.md`, with
exactly this message:

```
ci: lint every script by shebang, and make CI actually run
```

Then attempt `git push -u origin stage-01-lint-by-shebang`. It is expected to
fail on credentials; say so and stop.

## Report requirements

`docs/stages/stage-01-REPORT.md` must contain:

1. A checklist echo of every item in "The change", Tests, and Definition of Done.
2. Baseline and final gate outputs, verbatim and side by side.
3. The outputs of Tests 1–8.
4. The shellcheck image tag you pinned and how you confirmed it exists, or a
   statement that a local shellcheck was used.
5. **Advisory findings, verbatim**: every shellcheck finding on a
   slated-for-port file, grouped by file. Stages 03–05 depend on this list.
6. `git diff python-port --stat`.
7. **Deviations**, numbered and honest, including the boring ones.
8. **Open questions**: things you noticed but correctly did not do.

## Blocked protocol

STOP and commit only the report, with a BLOCKED section giving the exact
failing output and why each permitted path is closed, if:

- a gate already fails on the unmodified base;
- an enforced file needs a shellcheck fix that would change its behaviour;
- no shellcheck version tag can be confirmed to exist, and no local shellcheck
  is available;
- the change cannot be made inside the allowed files;
- any guardrail in `docs/stages/README.md` says STOP AND ASK.

A clean block is a successful execution.
