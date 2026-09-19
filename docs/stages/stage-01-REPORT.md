# Stage 01 report: lint every script by shebang, and make CI actually run

Branch: `stage-01-lint-by-shebang`. Base: `python-port` at `9124e0e`.

## 1. Checklist

### The change

- [x] `scripts/lint-scripts`: new, Python, `#!/usr/bin/env python3`, no `.py`, executable, stdlib only.
- [x] Discovery: every regular file directly in `scripts/` and `docker/scripts/`, plus `docker/entrypoint.sh`, `docker/bashrc.d/*.sh`, `docker/desktop/openbox-autostart`.
- [x] Classification by first line into a closed `Enum` (`Kind`: `SHELL`, `SOURCED_BASH`, `PYTHON`, `UNCLASSIFIABLE`). `sh`/`bash` means shell, `python3` means Python, `docker/bashrc.d/*.sh` is bash by path, and anything else FAILs naming the file.
- [x] Shell files run through `shellcheck --severity=warning`, with `--shell=bash` for the sourced drop-ins.
- [x] Enforced files are one named constant (`ENFORCED_SHELL`) with a comment pointing at `docs/roadmap.md`. Every other shell file is advisory: findings are printed and labelled advisory, and they do not fail the lint. Python files are never looked up in that list.
- [x] shellcheck comes from PATH if present. Otherwise it runs through `<engine> run --rm -v <repo>:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0`, where the engine comes from `scripts/compose-command --engine`. If there is neither, it FAILs with "shell linting could not run".
- [x] Python under `scripts/` is parsed with `ast.parse(source, filename, feature_version=(3, 9))`. Python under `docker/scripts/` gets a plain `ast.parse`.
- [x] Output is one line per file (verdict, path, classification), then a summary with counts. The exit status is 0 only when there are no failures.
- [x] The checking logic is pure functions (`interpreter`, `classify`, `is_enforced`, `check_python`, `shellcheck_argv`, `judge_shellcheck`, `render`). Subprocess and file I/O happen only in `discover`, `find_shellcheck`, `lint`, and `main`. Commands are argv lists and there is no `shell=True`.
- [x] Makefile `lint`: the hand-listed shellcheck call is replaced by `./scripts/lint-scripts`, and `compose config` still runs first. The `make help` line is updated.
- [x] CI `on:` now pushes on `main`, `python-port`, and `docker/**`. `pull_request` and `workflow_dispatch` are unchanged.
- [x] CI `lint` job: `actions/setup-python@v5` with `python-version: "3.9"`, apt-installs shellcheck as before, then runs `scripts/lint-scripts`. The compose-config step, the hadolint step, and all other jobs are untouched.
- [x] README: only the `make lint` row changed.

### Tests

- [x] 1. `./scripts/lint-scripts` exits 0 and lists every file with its classification.
- [x] 2. Classification matches reality (table below). `scripts/lint-scripts` appears as Python with the 3.9 check applied.
- [x] 3. `make lint` exits 0.
- [~] 4. Enforced negative control. The literal payload `rm $1` does **not** fail, because SC2086 is info severity and the prompt mandates `--severity=warning` (Deviation 2). A warning-level payload on the same file fails as required. Both outputs are below.
- [x] 5. Python 3.9 negative control (`match`): exits 1 and names the file.
- [x] 6. Unclassifiable negative control (`perl`): exits 1 and names the file.
- [x] 7. No linter available: exits 1 with "shell linting could not run".
- [x] 8. The CI workflow is valid YAML.

### Definition of Done

- [x] Baseline measured on the unmodified base: `make lint` exited 0 but skipped shellcheck. `make selftest` passed 32/32.
- [x] Final `make lint` exits 0.
- [x] Final `make selftest`: 32 passed, 0 failed, the same PASS lines as the baseline (diffed: identical).
- [x] Tests 1–8 were run and their outputs are below. Test 4 needs Deviation 2 to pass.
- [x] `git diff python-port --stat` shows only allowed files.

## 2. Gates: baseline vs final

Every shell had `export PATH="$HOME/.local/bin:$PATH"`. The engine is Podman (podman-compose). No local shellcheck is installed.

### `make lint`

Baseline (`9124e0e`, unmodified):

```
podman-compose config --quiet && echo 'compose config: ok'
compose config: ok
shellcheck not installed; skipping script lint
EXIT=0
```

Final:

```
podman-compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: podman run --rm -v /home/durant/Repos/ds/ros2_turtlesim/.claude/worktrees/agent-a214291206123fc1e:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
ok       docker/bashrc.d/ros-workspace.sh     bash (sourced), enforced
ok       docker/desktop/openbox-autostart     shell, enforced
ok       docker/entrypoint.sh                 shell, enforced
ok       docker/scripts/init-workspace        shell, advisory
ok       docker/scripts/install-ros-packages  shell, advisory
ok       docker/scripts/pkg                   shell, advisory
ok       docker/scripts/tutorial              shell, advisory
ok       scripts/base-image-digest            shell, advisory
ok       scripts/check-host                   shell, advisory
ok       scripts/compose-command              shell, advisory
ok       scripts/compose-up                   shell, advisory
ok       scripts/lint-scripts                 python, host (3.9 grammar)
ok       scripts/open-url                     shell, advisory
ok       scripts/run-quiet                    shell, advisory
ok       scripts/smoke-container              shell, advisory
lint-scripts: 15 files: 15 ok, 0 advisory, 0 FAIL
EXIT=0
```

### `make selftest`

The default project `ros2-tutorials-selftest` on port 6081 was used for both runs. The user's `ros2-tutorials` project was not touched. PASS/FAIL lines are extracted from each log with ANSI colours stripped. Baseline and final are **identical** (`diff` printed nothing):

```
  PASS image builds
  PASS desktop container accepts commands
  PASS the image defaults to the non-root ros user
  PASS desktop programs run as the non-root ros user
  PASS ROS_DISTRO is set
  PASS ros2 is on PATH
  PASS rosdep is on PATH
  PASS colcon is on PATH
  PASS turtlesim_node and turtle_teleop_key are installed
  PASS turtlesim stays alive for 5s on the virtual display
  PASS noVNC answers inside the container
  PASS noVNC answers on the host at http://localhost:6081
  PASS a node in one service receives messages from another service
  PASS install-ros-packages installs a ROS short name
  PASS installed package is runnable
  PASS install-ros-packages fails loudly on a missing package
  PASS colcon builds a source package in the persistent workspace
  PASS new shells source the workspace overlay automatically
  PASS pkg new --template pubsub builds
  PASS templated package registers its talker executable
  PASS templated pubsub node actually publishes on /chatter
  PASS pkg new --interfaces builds
  PASS ros2 interface show works for a generated message
  PASS ros2 interface show works for a generated service
  PASS pkg test reports a clean lint result for a generated package
  PASS make package prints the real command and points at make build
  PASS printed commands quote arguments so they paste correctly
  PASS make build prints colcon build and points at make run
  PASS make test reports the real colcon test-result verdict
  PASS make typed inside the container explains where to run it
  PASS workspace source survives container recreation
  PASS built overlay survives container recreation
32 passed, 0 failed
EXIT=0
```

| Gate | Baseline | Final |
|---|---|---|
| `make lint` | exit 0 (shellcheck skipped) | exit 0 (15 files linted, 0 FAIL) |
| `make selftest` | 32 passed, 0 failed | 32 passed, 0 failed |

## 3. Test outputs

### Test 1: `./scripts/lint-scripts`

This is the same output as the lint section of the final `make lint` above, with exit 0.

### Test 2: classification vs reality

| File | First line | Classified | Shell mode |
|---|---|---|---|
| `docker/bashrc.d/ros-workspace.sh` | (no shebang; sourced) | bash (sourced), by path | enforced |
| `docker/desktop/openbox-autostart` | `#!/bin/sh` | shell | enforced |
| `docker/entrypoint.sh` | `#!/bin/bash` | shell | enforced |
| `docker/scripts/init-workspace` | `#!/bin/bash` | shell | advisory |
| `docker/scripts/install-ros-packages` | `#!/bin/bash` | shell | advisory |
| `docker/scripts/pkg` | `#!/bin/bash` | shell | advisory |
| `docker/scripts/tutorial` | `#!/bin/bash` | shell | advisory |
| `scripts/base-image-digest` | `#!/bin/sh` | shell | advisory |
| `scripts/check-host` | `#!/bin/sh` | shell | advisory |
| `scripts/compose-command` | `#!/bin/sh` | shell | advisory |
| `scripts/compose-up` | `#!/bin/sh` | shell | advisory |
| `scripts/lint-scripts` | `#!/usr/bin/env python3` | **python, host (3.9 grammar)** | n/a |
| `scripts/open-url` | `#!/bin/sh` | shell | advisory |
| `scripts/run-quiet` | `#!/bin/sh` | shell | advisory |
| `scripts/smoke-container` | `#!/usr/bin/env bash` | shell | advisory |

That is 3 enforced shell, 11 advisory shell, and 1 Python (host). The first lines were read with `head -1` on each file and match.

Additional evidence that the linter really is 3.9-compatible: it ran under a real Python 3.9 (`docker.io/library/python:3.9-slim`, no shellcheck and no engine inside). It got through to its summary and exited 1 because it could not shell-lint, which is correct:

```
FAIL     scripts/smoke-container              shell, advisory
    shell linting could not run: no shellcheck on PATH, and no container engine to run it in (scripts/compose-command --engine found none)
lint-scripts: 15 files: 1 ok, 0 advisory, 14 FAIL
EXIT=1
```

### Test 3: `make lint`

This is the final `make lint` above, with exit 0.

### Test 4: enforced shell negative control

**Literal payload.** `echo 'rm $1' >> docker/desktop/openbox-autostart`, then `./scripts/lint-scripts`:

```
shellcheck via: podman run --rm -v /home/durant/Repos/ds/ros2_turtlesim/.claude/worktrees/agent-a214291206123fc1e:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
ok       docker/bashrc.d/ros-workspace.sh     bash (sourced), enforced
ok       docker/desktop/openbox-autostart     shell, enforced
ok       docker/entrypoint.sh                 shell, enforced
[... 11 advisory + 1 python lines, all ok ...]
lint-scripts: 15 files: 15 ok, 0 advisory, 0 FAIL
EXIT=0
```

The reason, shown by shellcheck directly on the modified file (default severity first, then `--severity=warning`):

```
In docker/desktop/openbox-autostart line 17:
rm $1
   ^-- SC2086 (info): Double quote to prevent globbing and word splitting.
...
---
exit=0
```

**Warning-level payload.** `printf '%s\n' 'rm $1' 'cd $1' >> docker/desktop/openbox-autostart`, then `./scripts/lint-scripts`:

```
shellcheck via: podman run --rm -v /home/durant/Repos/ds/ros2_turtlesim/.claude/worktrees/agent-a214291206123fc1e:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
ok       docker/bashrc.d/ros-workspace.sh     bash (sourced), enforced
FAIL     docker/desktop/openbox-autostart     shell, enforced
    In docker/desktop/openbox-autostart line 18:
    cd $1
    ^---^ SC2164 (warning): Use 'cd ... || exit' or 'cd ... || return' in case cd fails.
    
    Did you mean:
    cd $1 || exit
    
    For more information:
      https://www.shellcheck.net/wiki/SC2164 -- Use 'cd ... || exit' or 'cd ... |...
ok       docker/entrypoint.sh                 shell, enforced
ok       docker/scripts/init-workspace        shell, advisory
ok       docker/scripts/install-ros-packages  shell, advisory
ok       docker/scripts/pkg                   shell, advisory
ok       docker/scripts/tutorial              shell, advisory
ok       scripts/base-image-digest            shell, advisory
ok       scripts/check-host                   shell, advisory
ok       scripts/compose-command              shell, advisory
ok       scripts/compose-up                   shell, advisory
ok       scripts/lint-scripts                 python, host (3.9 grammar)
ok       scripts/open-url                     shell, advisory
ok       scripts/run-quiet                    shell, advisory
ok       scripts/smoke-container              shell, advisory
lint-scripts: 15 files: 14 ok, 0 advisory, 1 FAIL
EXIT=1
```

This output was captured before the whitespace-only render tweak in Deviation 5, which is why a blank findings line shows trailing spaces. The file was reverted with `git checkout -- docker/desktop/openbox-autostart`.

**Extra control, advisory path** (not required by the prompt). `sed -i '2i zz_unused_negative_control=1' scripts/open-url`:

```
ok       scripts/lint-scripts                 python, host (3.9 grammar)
advisory scripts/open-url                     shell, advisory
    advisory findings (not failing; slated for the Python port):
    In scripts/open-url line 2:
    zz_unused_negative_control=1
    ^------------------------^ SC2034 (warning): zz_unused_negative_control appears unused. Verify use (or export if used externally).

    For more information:
      https://www.shellcheck.net/wiki/SC2034 -- zz_unused_negative_control appear...
ok       scripts/run-quiet                    shell, advisory
ok       scripts/smoke-container              shell, advisory
lint-scripts: 15 files: 14 ok, 1 advisory, 0 FAIL
EXIT=0
```

The file was reverted. Two earlier attempts at this control produced no finding at all and are recorded for honesty. `cd $1` appended after the script's final `exit 0` is unreachable, and `cd $1` on line 2 is suppressed by the script's `set -e`.

### Test 5: Python 3.9 negative control

`scripts/zz-negative-control` contained `#!/usr/bin/env python3` followed by `match 1:` / `case 1:` / `pass`:

```
[... 15 lines, all ok ...]
FAIL     scripts/zz-negative-control          python, host (3.9 grammar)
    needs Python newer than 3.9, or is invalid: Pattern matching is only supported in Python 3.10 and greater (zz-negative-control, line 4)
lint-scripts: 16 files: 15 ok, 0 advisory, 1 FAIL
EXIT=1
```

The file was deleted.

### Test 6: unclassifiable negative control

```
[... 15 lines, all ok ...]
FAIL     scripts/zz-negative-control          unclassifiable
    first line '#!/usr/bin/env perl' names neither sh, bash, nor python3
lint-scripts: 16 files: 15 ok, 0 advisory, 1 FAIL
EXIT=1
```

The file was deleted.

### Test 7: no linter available

`PATH` was set to a scratch directory containing only symlinks to `python3` and `sh`, so there was no `shellcheck`, `docker`, or `podman`. Command: `PATH=<scratch>/nolinter-bin ./scripts/lint-scripts`:

```
lint-scripts: shell linting could not run: no shellcheck on PATH, and no container engine to run it in (scripts/compose-command --engine found none)
FAIL     docker/bashrc.d/ros-workspace.sh     bash (sourced), enforced
    shell linting could not run: no shellcheck on PATH, and no container engine to run it in (scripts/compose-command --engine found none)
FAIL     docker/desktop/openbox-autostart     shell, enforced
    shell linting could not run: no shellcheck on PATH, and no container engine to run it in (scripts/compose-command --engine found none)
[... the same FAIL + message for each of the 11 advisory shell files ...]
ok       scripts/lint-scripts                 python, host (3.9 grammar)
lint-scripts: 15 files: 1 ok, 0 advisory, 14 FAIL
EXIT=1
```

(The first line goes to stderr.)

### Test 8: CI workflow is valid YAML

```
$ python3 -c 'import yaml,sys; yaml.safe_load(open(".github/workflows/docker-image.yml"))'; echo "YAML_EXIT=$?"
YAML_EXIT=0
```

`git status --short` after the last negative control was reverted (before the Makefile, CI, and README edits): `?? scripts/lint-scripts` only. Nothing from the controls remains.

## 4. shellcheck image

Pinned image: `docker.io/koalaman/shellcheck:v0.11.0`. It is the newest stable release, confirmed three ways:

- The Docker Hub tags API (`hub.docker.com/v2/repositories/koalaman/shellcheck/tags`) lists `v0.11.0` (updated 2025-08-04) as the newest version tag. The only other entries are `latest` and `stable`.
- The GitHub releases API reports `koalaman/shellcheck` latest release `v0.11.0`, published 2025-08-04.
- `podman pull docker.io/koalaman/shellcheck:v0.11.0` succeeded, and `podman run --rm docker.io/koalaman/shellcheck:v0.11.0 --version` printed `version: 0.11.0`.

No local shellcheck was installed. Every run in this report went through Podman.

## 5. Advisory findings, verbatim

At the mandated `--severity=warning`, **there are none**: all 11 slated-for-port shell files are clean (`0 advisory` in the final output above).

Supplementary information for stages 03–05, not produced by the linter. At shellcheck's default severity, the slated-for-port files have only these info-level notes (`--format=gcc`, all 11 advisory files):

```
docker/scripts/pkg:227:46: note: Expressions don't expand in single quotes, use double quotes for that. [SC2016]
docker/scripts/pkg:246:50: note: Expressions don't expand in single quotes, use double quotes for that. [SC2016]
docker/scripts/pkg:255:50: note: Expressions don't expand in single quotes, use double quotes for that. [SC2016]
scripts/check-host:59:10: note: Expressions don't expand in single quotes, use double quotes for that. [SC2016]
scripts/smoke-container:116:44: note: Expressions don't expand in single quotes, use double quotes for that. [SC2016]
scripts/smoke-container:182:14: note: Expressions don't expand in single quotes, use double quotes for that. [SC2016]
```

All of these are intentional: literal CMake text, and commands passed to another shell.

## 6. `git diff python-port --stat`

```
 .github/workflows/docker-image.yml |  14 +-
 Makefile                           |   6 +-
 README.md                          |   2 +-
 docs/stages/stage-01-REPORT.md     | 357 +++++++++++++++++++++++++++++++++++++
 scripts/lint-scripts               | 223 +++++++++++++++++++++++
 5 files changed, 591 insertions(+), 11 deletions(-)
```

## 7. Deviations

1. **The worktree started on the wrong commit.** The isolated worktree was created at `8256560`, an ancestor of the specified base, not at `9124e0e`. It was clean, so I fast-forwarded it (`git merge --ff-only 9124e0e`) before measuring anything. All baseline numbers are from `9124e0e`.
2. **Test 4 contradicts the specified severity.** The prompt requires `--severity=warning` and also expects `rm $1` to fail the lint. SC2086 (unquoted `$1`) is **info** severity in shellcheck 0.11.0, so at warning severity that payload cannot fail. As the minimal resolution, I kept the code exactly as specified (`--severity=warning` everywhere) and proved the enforced-FAIL path with a warning-level payload (`cd $1`, SC2164) on the same file. The literal payload's exit-0 output is recorded above. I rejected the alternative, linting enforced files at `--severity=info`, because it departs from the spec and would require suppressing five intentional info notes in enforced files: SC1091 ×2, SC2317, SC2016 ×3 (see Open question 1).
3. **CI runs `python scripts/lint-scripts`, not `./scripts/lint-scripts`.** This makes the step run on setup-python's 3.9 regardless of what `/usr/bin/env python3` would resolve to. The step also prints `python --version` so the log shows which interpreter ran. I bumped `actions/setup-python` to `@v5`; the prompt named the action but no version.
4. **The linter prints the command it uses to run shellcheck** (`shellcheck via: podman run ...`). The prompt did not ask for this. I added it for consistency with the repo's no-black-box convention that tooling prints the native commands it stands in for. It is one extra line.
5. **Whitespace-only render tweak made after the Test 4 capture.** Indented findings lines are now right-stripped, so blank lines inside shellcheck output no longer carry four trailing spaces. The Test 4 warning-payload output above predates this change. All later outputs include it.
6. **Unexpected shellcheck exit codes FAIL, even for advisory files.** If shellcheck (or the engine) exits with something other than 0 or 1, for example an image pull failure (Podman exit 125), the file FAILs and stderr is shown. The prompt did not cover this case. Treating it as a pass or an advisory would violate "must never report success without having run". Stderr is otherwise discarded, which drops Podman's harmless CNI config warnings on this host.
7. **Selftest overlap with a negative control.** The baseline `make selftest` ran in the background while I was writing the linter. The Test 4 edit to `docker/desktop/openbox-autostart`, which is `COPY`'d into the image, happened while that run was in progress. By the timeline, the image build step (at the start) had already finished before the edit, and no test exercises that file's contents. The final selftest ran with no temporary edits present, and its results are identical to the baseline.
8. **No enforced file needed a fix.** `docker/entrypoint.sh`, `docker/bashrc.d/ros-workspace.sh`, and `docker/desktop/openbox-autostart` were already clean at warning severity and are unmodified.

## 8. Open questions

1. **Should enforced files be linted at `--severity=info`?** That is what Test 4's intent (catching unquoted `$1`) implies. It would require `# shellcheck disable=` directives in the enforced files for SC1091 (`entrypoint.sh:47`, `ros-workspace.sh:25`, which source a runtime-generated `setup.bash`), SC2317 (`ros-workspace.sh:14`, the deliberate `return 0 2>/dev/null || true`), and SC2016 (`ros-workspace.sh:46,50,51`, backticks shown literally in help text). All are comment-only and behaviour-neutral. This is an architect decision, so I did not make it.
2. **CI uses Ubuntu's apt shellcheck, not the pinned v0.11.0.** The prompt said to keep the apt install. On `ubuntu-latest` (24.04) that is shellcheck 0.9.x, so CI and a local container run can disagree on findings. Pinning CI to the same image or release would remove the drift.
3. **The linter prefers docker over podman via `compose-command`,** which requires a working *compose*, not just an engine. A host with a bare engine and no compose will FAIL shell linting even though `<engine> run` would work. This follows the prompt as written. Flagged only.
4. **`--severity=warning` hides SC2086-class quoting bugs in the advisory scripts too.** None exist at info level today (Section 5), but this is worth knowing for stages 03–05, since quoting bugs are the port's stated motivation.
5. **CI was not observed.** My push is expected to fail, and I make no claim about CI results. The new `push: [main, python-port, ...]` trigger means the first push of `python-port` will run all jobs, including `smoke`, `build-arm64`, `smoke-podman`, and `scan`, for the first time ever.
