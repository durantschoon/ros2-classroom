# Stage 13 report: four distributions in CI, published, and documented

Branch `stage-13-four-distros-ci`. The change is commit `242573c`
("ci: test all four distributions nightly and publish their images from
main"); this report is a second commit on top of it (Deviation 2).

## 1. First step

The worktree was created at `1cdff5f` (the stage 07 prompt, on
`native-recipes`), where `docs/stages/stage-13-PROMPT.md` exists but is not
this branch's base. I ran `git fetch origin` and
`git checkout -b stage-13-four-distros-ci origin/multi-distro` (Deviation 1).
Then `git log --oneline -1`:

```
ffdd4ec docs(stages): stage 13 revised for the macOS host; Stage 2 restarts as native-recipes, macOS through pixi
```

## 2. Checklist

### The change

- [x] **0. `make check` on macOS.** In `tests/host/test_distros.py`, the
  three `run.err.startswith(str(self.table_path) + ": ")` sites now compare
  against `self.table_path.resolve()`. Nothing else in the file changed. The
  module went from 54 run, 27 failures to 54 run, 0 failures (python3 3.12
  and `/usr/bin/python3` 3.9.6 both); `make check` from 288 run, 27 failures
  to 291 run, 0 failures (the 3 extra are item 1b's new tests).
- [x] **1. Per-distribution fixes.** None needed; nothing changed in the
  `Dockerfile` or `docker/**`. Humble, jazzy, kilted and lyrical each pass
  the isolated self-test 48/48 on this host (arm64), and each passes CI's
  `smoke` 48/48 (amd64) and `build-arm64` (section 5).
  - **Jazzy's stage 12 failure** ("no message crossed between compose
    services") did not reproduce: 48/48 in two local runs and in CI. Evidence
    gathered in the first local run, while the suite was waiting in that step:
    the talker container logged `publishing #1..#5`, both containers had
    `ROS_DOMAIN_ID=13` and `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`, and
    `ros2 topic list` / `ros2 topic echo --once /chatter` from the desktop
    container returned `/chatter` and `data: hello from the talker service`.
    That probe may itself have helped the suite (it started a `ros2` daemon
    in the desktop container), so I ran jazzy a second time without touching
    it: 48/48 again, the DDS check passing on its own. SUBNET discovery works
    on jazzy here, and the 10 s wait was enough. The cause on the old WSL host
    remains unknown; I made no change, since nothing pointed at one and a
    longer sleep is not a fix without evidence (Open question 1).
- [x] **1b. Busy-port hint.** `scripts/compose-up` now suggests
  `make up ROS_DISTRO=jazzy NOVNC_PORT=6085 && make open ROS_DISTRO=jazzy NOVNC_PORT=6085`
  when `ROS_DISTRO` (which make always exports) names a distribution other
  than the table's default. For the default, the text is unchanged. A name
  is printed only if it has the shape `scripts/distros` accepts
  (`[a-z][a-z0-9_-]*`), so the command stays paste-safe. There are three new
  tests in `tests/host/test_compose_up.py`; the existing ones are untouched.
- [x] **1b. `.env.example`.** `NOVNC_PORT=6080` is now commented out, with
  the precedence written above it: the command line, then the environment,
  then `distros.json` for make and `ros2.ps1`; `.env`'s value only for plain
  `docker compose`. I checked this against the Makefile (`DISTRO_INPUTS`
  hands only make's own variables to the resolver), `scripts/distros`
  (`environ.get("NOVNC_PORT") or str(distro.port)`), and `ros2.ps1` line 193.
- [x] **2. `docker-image.yml`.**
  - It now has a nightly `schedule` (`23 4 * * *`) and a `workflow_dispatch`
    input `distros`, default `all`.
  - A new first job, `distros`, reads `distros.json` with `jq`: the default
    alone for push and pull_request, every name for schedule and dispatch.
  - `smoke` and `build-arm64` are matrices over that list with
    `fail-fast: false`.
  - `smoke` runs `eval "$(./scripts/distros env)"` with `ROS_DISTRO` set,
    then the self-test through `ci-annotate`.
  - `build-arm64` resolves with `./scripts/distros env --make` and passes
    `ROS_DISTRO` and `ROS_BASE_DIGEST` as build args.
  - `smoke-podman` and `scan` are unchanged.
  - There is no publish job in this file.
- [x] **2a. `publish.yml` (new).**
  - Triggers: `workflow_run` on "Docker image" (`completed`, branches
    `[main]`), acting only on `success`; `workflow_dispatch`; and
    `pull_request` as a build-only dry run.
  - The checkout uses `workflow_run.head_sha || github.sha`.
  - A first job reads the names and the default with `jq`; then comes a
    matrix job over the names with `fail-fast: false`.
  - Each leg runs `./scripts/distros env --make | tee -a "$GITHUB_OUTPUT"`,
    sets up QEMU and buildx, then runs `docker/build-push-action@v6` with
    both build args, `linux/amd64,linux/arm64`, tags `:<name>` (plus
    `:latest` for the default), and a GHA cache scoped per distribution.
  - It pushes only for a `workflow_run` of a `push` event in this repository,
    or for a `workflow_dispatch` on `refs/heads/main`. That is stricter than
    the prompt (Deviation 4).
  - It uses only `GITHUB_TOKEN`, through `docker/login-action`, and logs in
    only when it pushes.
  - **`workflow_run` fires only for workflow files on the default branch, so
    this workflow publishes for the first time after the multi-distro pull
    request merges to `main`; this stage's pull request only proves the dry
    run.**
- [x] **3. Docs.**
  - `README.md` "Configuration" now has a table of the four distributions:
    Ubuntu, the URL with each one's port, and the image tags. It also covers
    `make distros`, setting the distribution per command or in `.env`,
    `ros2.ps1`, each distribution's own `/workspace` and `/home/ros`, and that
    published images make another distribution a download, not a build.
  - The "pair it with the matching base-image digest" sentence is gone
    (Deviation 5).
  - "What is in the image" now names all four.
  - `docs/ros-distributions.md` is rewritten around the table: why these
    four, the default and why, published images, `make digest` (including
    the hand edit of the `Dockerfile`/`compose.yaml` defaults that
    `make check` enforces), and the table winning over an old `.env` (the
    stage 11 backlog item). The `guix` section is kept.
  - `docs/cross-platform.md` gets one paragraph for `ros2.ps1`.

### Definition of Done

- [x] Baseline on the unmodified base: `make lint` passed; `make check` had
  27 failures, all in `tests/host/test_distros.py` (expected), and no others.
- [x] `make lint` passes; `make check` passes (291 run, 0 failures, 29 skipped).
- [x] All four local self-tests pass, 48/48 each.
- [x] `actionlint` is clean (with shellcheck 0.11.0).
- [x] The dry-run CI run is green: every matrix leg, both architectures,
  nothing pushed. So is the four-distribution dispatch run.
- [x] `git diff multi-distro --stat` shows only allowed files.

## 3. Gates, verbatim

### Baseline (unmodified `ffdd4ec`)

`make lint` (exit 0):
```
docker compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: docker run --rm -v <worktree>:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
ok       docker/bashrc.d/ros-workspace.sh      bash (sourced), enforced
ok       docker/desktop/openbox-autostart      shell, enforced
ok       docker/entrypoint.sh                  shell, enforced
ok       docker/scripts/init-workspace         python, container
ok       docker/scripts/install-ros-packages   python, container
ok       docker/scripts/pkg                    python, container
ok       docker/scripts/rqt_graph              shell, advisory
ok       docker/scripts/turtlesim-teleop       python, container
ok       docker/scripts/tutorial               python, container
ok       scripts/base-image-digest             python, host (3.9 grammar)
ok       scripts/check-host                    python, host (3.9 grammar)
ok       scripts/ci-annotate                   python, host (3.9 grammar)
ok       scripts/compose-command               python, host (3.9 grammar)
ok       scripts/compose-up                    python, host (3.9 grammar)
ok       scripts/distros                       python, host (3.9 grammar)
ok       scripts/lint-scripts                  python, host (3.9 grammar)
ok       scripts/open-url                      python, host (3.9 grammar)
ok       scripts/run-quiet                     python, host (3.9 grammar)
ok       scripts/smoke-container               python, host (3.9 grammar)
ok       scripts/uninstall                     python, host (3.9 grammar)
ok       scripts/workstation-help              python, host (3.9 grammar)
ok       tests/host/fakes.py                   python, host (3.9 grammar)
ok       tests/host/test_base_image_digest.py  python, host (3.9 grammar)
ok       tests/host/test_check_host.py         python, host (3.9 grammar)
ok       tests/host/test_ci_annotate.py        python, host (3.9 grammar)
ok       tests/host/test_compose_command.py    python, host (3.9 grammar)
ok       tests/host/test_compose_up.py         python, host (3.9 grammar)
ok       tests/host/test_distros.py            python, host (3.9 grammar)
ok       tests/host/test_open_url.py           python, host (3.9 grammar)
ok       tests/host/test_ros2_ps1.py           python, host (3.9 grammar)
ok       tests/host/test_run_quiet.py          python, host (3.9 grammar)
ok       tests/host/test_smoke_container.py    python, host (3.9 grammar)
ok       tests/host/test_uninstall.py          python, host (3.9 grammar)
ok       tests/host/test_workstation_help.py   python, host (3.9 grammar)
lint-scripts: 34 files: 34 ok, 0 advisory, 0 FAIL
```

`make check` (exit 2 from make; the 27 failures, then the summary):
```
FAIL: test_a_default_not_in_the_table (test_distros.MalformedTableTests.test_a_default_not_in_the_table)
FAIL: test_a_missing_table (test_distros.MalformedTableTests.test_a_missing_table)
FAIL: test_no_distros (test_distros.MalformedTableTests.test_no_distros)
FAIL: test_not_json (test_distros.MalformedTableTests.test_not_json) (args=('env',))
FAIL: test_not_json (test_distros.MalformedTableTests.test_not_json) (args=('list',))
FAIL: test_not_json (test_distros.MalformedTableTests.test_not_json) (args=('refresh',))
FAIL: test_a_port_out_of_range_is_refused (test_distros.PortTableTests.test_a_port_out_of_range_is_refused)
FAIL: test_a_port_that_is_not_an_integer_is_refused (test_distros.PortTableTests.test_a_port_that_is_not_an_integer_is_refused) (case='a port that is a string')
FAIL: test_a_port_that_is_not_an_integer_is_refused (test_distros.PortTableTests.test_a_port_that_is_not_an_integer_is_refused) (case='a port with a fraction')
FAIL: test_a_port_that_is_not_an_integer_is_refused (test_distros.PortTableTests.test_a_port_that_is_not_an_integer_is_refused) (case='a port written as a float')
FAIL: test_a_port_that_is_not_an_integer_is_refused (test_distros.PortTableTests.test_a_port_that_is_not_an_integer_is_refused) (case='a port that is true')
FAIL: test_a_port_that_is_not_an_integer_is_refused (test_distros.PortTableTests.test_a_port_that_is_not_an_integer_is_refused) (case='no port')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a port that is a string')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a port with a fraction')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a port written as a float')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a port that is true')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='no port')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a port below 1024')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a port above 65535')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='two distributions sharing a port')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case="the self-test's port")
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a digest of the wrong shape')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a name of the wrong shape')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='no default')
FAIL: test_every_malformed_table_is_refused (test_distros.PortTableTests.test_every_malformed_table_is_refused) (case='a default not in the table')
FAIL: test_the_self_tests_port_is_refused (test_distros.PortTableTests.test_the_self_tests_port_is_refused)
FAIL: test_two_distributions_sharing_a_port_are_refused (test_distros.PortTableTests.test_two_distributions_sharing_a_port_are_refused)
Ran 288 tests in 81.100s

FAILED (failures=27, skipped=29)
make: *** [check] Error 1
```
Each failure is the same assertion, for example:
```
AssertionError: False is not true : exit 1
--- stdout ---
--- stderr ---
/private/tmp/ros2-host-test-bd89o5jz/tree/distros.json: "humble" and "jazzy" share port 6082
```

### Final

`make lint` (exit 0): output identical to the baseline, line for line
(`diff` empty).

`make check` (exit 0):
```
----------------------------------------------------------------------
Ran 291 tests in 130.426s

OK (skipped=29)
```

The 29 skips are the same 29 as in the baseline; they include the `ros2.ps1`
tests, because this host has no `pwsh` (Deviation 3). CI's `lint` job, which
has `pwsh`, ran the same suite on `242573c`: `Ran 291 tests in 94.528s` /
`OK (skipped=3)`, with no `test_ros2_ps1` test skipped.

`actionlint` 1.7.12 (darwin_arm64, in the scratchpad), with shellcheck
0.11.0 (in the scratchpad):
```
$ actionlint -shellcheck <scratchpad>/bin/shellcheck
$ echo $?
0
```
The first run reported two shellcheck notes, which I fixed before committing:
SC2020 for `tr ', ' '\n\n'` and SC2086 for an unquoted `$TAGS`. An
intermediate SC2001 note on `sed 's/^/  /'` was fixed the same way.

## 4. Tests and mutations

Item 0 changes three assertions, and nothing else in `test_distros.py`.

Item 1b's new tests, in `DistributionTests` of `tests/host/test_compose_up.py`:

| Test | Pins |
|---|---|
| `test_the_hint_for_another_distribution_names_it` | `ROS_DISTRO=jazzy`, port 6083 busy ⇒ `  make up ROS_DISTRO=jazzy NOVNC_PORT=6085 && make open ROS_DISTRO=jazzy NOVNC_PORT=6085` |
| `test_the_hint_for_the_default_is_unchanged` | `ROS_DISTRO=lyrical` ⇒ the old text, and no `ROS_DISTRO` anywhere on stderr |
| `test_a_name_that_is_not_paste_safe_is_never_printed` | `jazzy; rm -rf ~`, `Jazzy`, `$(id)`, `-jazzy` ⇒ the old text, no `ROS_DISTRO` |

For the mutations, I copied the script out and restored it by copying it
back, checked with checksums. Good file: `2d48cf96b89b418cdf6ebc4900a6f0d19452e437`.

| Mutation | sha1 | Result |
|---|---|---|
| `distro_words` always returns `""` | (sed of the good file) | 1 failure: `test_the_hint_for_another_distribution_names_it` |
| drop the name-shape check (`if distro == default:`) | `3f72287d3a8b952540882adbce55b390cca1e413` | 8 failures: the 4 paste-safety subtests, and 4 existing hint tests (an unset `ROS_DISTRO` would print `ROS_DISTRO= `) |
| drop the default check (`if not DISTRO_NAME.fullmatch(distro):`) | `aa526f448481870bb18014f6e0bcfa01f3bdc0ab` | 1 failure: `test_the_hint_for_the_default_is_unchanged` |
| restored | `2d48cf96b89b418cdf6ebc4900a6f0d19452e437` | 34/34 |

## 5. Verification

### 1. The isolated self-test, all four, one at a time

Each was run as
`SELFTEST_PROJECT=ros2-tutorials-st13 SELFTEST_NOVNC_PORT=6096 SELFTEST_ROS_DOMAIN_ID=13 IMAGE_NAME=ros2-tutorials-st13 make selftest ROS_DISTRO=<name>`.
The host is macOS arm64 with OrbStack Docker, so these are `linux/arm64`
images. The amd64 side is proved only by CI (`smoke`, and the publish dry
run).

| Distribution | Base | Summary line |
|---|---|---|
| humble | `FROM docker.io/library/ros:humble-ros-base@sha256:1813d3c8…` | `48 passed, 0 failed` |
| jazzy (run 1, probed during the DDS step) | `FROM docker.io/library/ros:jazzy-ros-base@sha256:c3706ef0…` | `48 passed, 0 failed` |
| kilted | `FROM docker.io/library/ros:kilted-ros-base@sha256:8e7b828a…` | `48 passed, 0 failed` |
| jazzy (run 2, untouched) | same | `48 passed, 0 failed` |
| lyrical (the default; its local tag is `ros2-tutorials-st13:latest`) | `FROM docker.io/library/ros:lyrical-ros-base@sha256:0c19f326…` | `48 passed, 0 failed` |

Each began `using: docker compose -p ros2-tutorials-st13  (isolated project; host port 6096)`.
Afterwards I removed the `ros2-tutorials-st13:*` images (`docker rmi` of `:humble`, `:jazzy`, `:kilted`, `:latest`: 4 untagged; none left, and no `ros2-tutorials-st13` volumes).

### 2. actionlint

See section 3: exit 0, no output.

### 3. CI

I pushed the stage branch (`git push -u origin stage-13-four-distros-ci`,
which succeeded). I opened the draft pull request
https://github.com/durantschoon/ros2-classroom/pull/3 into `multi-distro`,
and closed it afterwards.

**The publish dry run** (`publish.yml`, `pull_request`), run
https://github.com/durantschoon/ros2-classroom/actions/runs/36935391168,
conclusion `success`:
```
distros: success 2026-10-01T22:29:43Z 2026-10-01T22:29:48Z
publish (humble): success 2026-10-01T22:29:50Z 2026-10-01T22:43:56Z
publish (kilted): success 2026-10-01T22:29:50Z 2026-10-01T22:48:29Z
publish (jazzy): success 2026-10-01T22:29:50Z 2026-10-01T22:46:48Z
publish (lyrical): success 2026-10-01T22:29:50Z 2026-10-01T22:46:44Z
```
Each leg took 14-19 minutes with a cold cache, arm64 by QEMU, well under the
90-minute limit. The steps of a leg:
`Log in to ghcr: skipped`, `Build for linux/amd64 and linux/arm64: success`.
Both architectures were built in every leg, for example:
```
publish (humble)  #10 [linux/arm64  1/16] FROM docker.io/library/ros:humble-ros-base@sha256:1813d3c8…
publish (humble)  #12 [linux/amd64  1/16] FROM docker.io/library/ros:humble-ros-base@sha256:1813d3c8…
```
Nothing was pushed. The log has no `pushing layers` or `pushing manifest`
lines (count 0), and the last step says:
```
publish (lyrical)  Dry run (pull_request): built for linux/amd64,linux/arm64, nothing pushed:
publish (lyrical)  ghcr.io/durantschoon/ros2-classroom:lyrical
publish (lyrical)  ghcr.io/durantschoon/ros2-classroom:latest
publish (humble)   Dry run (pull_request): built for linux/amd64,linux/arm64, nothing pushed:
publish (humble)   ghcr.io/durantschoon/ros2-classroom:humble
```
jazzy and kilted print the same with their own tag. `PUBLISH: false` is in
each leg's step environment.

**Four-distribution smoke** (`gh workflow run docker-image.yml --ref stage-13-four-distros-ci -f distros=all`),
run https://github.com/durantschoon/ros2-classroom/actions/runs/36935396175,
conclusion `success`:
```
lint: success
distros: success
smoke-podman: success
scan: success
build-arm64 (lyrical): success
build-arm64 (humble): success
smoke (lyrical): success
smoke (jazzy): success
smoke (humble): success
build-arm64 (kilted): success
build-arm64 (jazzy): success
smoke (kilted): success
```
`Distributions for this workflow_dispatch run: ["humble","jazzy","kilted","lyrical"]`.
Each smoke leg printed `48 passed, 0 failed`, and each `smoke` and
`build-arm64` leg built `FROM docker.io/library/ros:<its name>-ros-base@<its digest>`.

**The pull request's own "Docker image" run** (default only),
https://github.com/durantschoon/ros2-classroom/actions/runs/36935391083,
`success`:
`distros, lint, smoke-podman, build-arm64 (lyrical), smoke (lyrical), scan`,
all `success`.

### 4. Gates

See section 3.

## 6. Stat, excluding this report

```
$ git diff multi-distro --stat   (multi-distro = origin/multi-distro = ffdd4ec)
 .env.example                       |   8 ++-
 .github/workflows/docker-image.yml |  82 +++++++++++++++++++++--
 .github/workflows/publish.yml      | 133 +++++++++++++++++++++++++++++++++++++
 README.md                          |  33 ++++++---
 docs/cross-platform.md             |  10 +++
 docs/ros-distributions.md          | 106 +++++++++++++++++++++++------
 scripts/compose-up                 |  58 +++++++++++++---
 tests/host/test_compose_up.py      |  32 +++++++++
 tests/host/test_distros.py         |   6 +-
 9 files changed, 422 insertions(+), 46 deletions(-)
```
All of these are allowed files.

## 7. Deviations

1. **Base.** The worktree started at `1cdff5f` on `native-recipes`. I
   created the stage branch from `origin/multi-distro` (`ffdd4ec`) with
   `git fetch origin && git checkout -b stage-13-four-distros-ci origin/multi-distro`,
   and deleted the auto-created worktree branch.
2. **Two commits, not one.** Verification 3 needs the branch pushed before
   its results exist, and force-pushing is forbidden. So the change is
   `242573c`, with the prompt's exact subject line, pushed first. This report
   is a second commit on top, pushed the same way (a plain fast-forward push,
   so the branch was pushed twice). The coordinator can squash them.
3. **No `pwsh`.** The sandbox refused to unpack or run a portable PowerShell
   from the scratchpad, so the 15 `ros2.ps1` tests skipped locally, as in
   the baseline. CI's `lint` job (which has `pwsh`) ran them, and they were
   green in both "Docker image" runs. No `ros2.ps1` file was touched.
4. **Push conditions are stricter than the prompt's.**
   - "`push` true only for `workflow_run` and `workflow_dispatch`" became:
     a `workflow_run` whose triggering event was `push` in this repository,
     or a `workflow_dispatch` on `refs/heads/main`.
   - The reason for the first: a pull request from a fork whose head branch
     is named `main` reaches `workflow_run` with `branches: [main]` and a
     `success` conclusion, and would otherwise publish the fork's commit with
     this repository's token.
   - It also keeps the nightly scheduled run on `main` from republishing,
     which the user did not ask for.
   - The reason for the second: the ground rule "never pushes from a non-main
     push", applied to manual runs on other branches.
   - On `workflow_run`, the first job is skipped entirely unless those
     conditions hold.
5. **"Remove the 'requires the matching base digest' instruction."** That
   wording was not in the README. The nearest sentence ("make and `ros2.ps1`
   pair it with the matching base-image digest from `distros.json`") is
   removed. The digest is now explained only in `docs/ros-distributions.md`.
6. **The dispatch input accepts names as well as `all`** (space- or
   comma-separated, checked against the table, and an unknown name fails the
   `distros` job with an `::error::`). The prompt specified the input and
   its default only.
7. **`ci-annotate`'s title** for `smoke` is now `smoke <name>`
   (`smoke lyrical` for the default) rather than `smoke`, so annotations from
   four legs can be told apart. The test behaviour for the default is
   unchanged.
8. **Jazzy run 1 was probed while it ran** (read-only `docker logs`,
   `printenv`, `ros2 topic list/echo` inside the self-test's own containers).
   I disclosed this and repeated the run untouched.
9. Between runs, the jazzy run's final cleanup may have overlapped the first
   seconds of the humble run's image build. The build was still on
   `== Build`, and the cleanup touches only containers and volumes.
10. Read-only extras: I checked branch protection on `main` ("Branch not
    protected", so renaming the `smoke` check to `smoke (lyrical)` breaks no
    required status), and ran the two touched test modules under
    `/usr/bin/python3` 3.9.6.
11. `README.md` "What is in the image" was edited; item 3 names
    "Configuration and the prose around `ROS_DISTRO`", and the prompt's
    motivation names this section.

## 8. Open questions

1. **Jazzy's stage 12 DDS failure is unexplained.** It did not reproduce on
   macOS/OrbStack (2 runs) or on CI's Docker (1 run). If it comes back on WSL
   or Docker Desktop, the evidence to collect is the talker's log and
   `ros2 topic list` from the desktop at the moment of failure.
2. **The publish dry run runs on every pull request**, 4 legs of 14-19 min
   each. Path filters (`Dockerfile`, `docker/**`, `distros.json`, the
   workflow) would cut that; not done, since the prompt asked for
   `pull_request`.
3. **First publish.** The ghcr package was first pushed from the user's
   account. The first real publish after the merge may need the user to grant
   this repository write access ("Manage Actions access").
   `docker/build-push-action` also adds provenance attestations by default,
   which show as an `unknown/unknown` platform in ghcr's UI. That is harmless,
   but can be turned off with `provenance: false` if unwanted.
4. **The nightly schedule runs only on the default branch**, so
   "all four nightly" starts after the merge to `main`. Until then, the
   dispatch command above is the way to run it.
5. `.env.example` still says `ROS_BASE_DIGEST` "Overrides the digest
   distros.json pairs with ROS_DISTRO". In `.env` it overrides only for plain
   `docker compose`; make and `ros2.ps1` read it only from the command line
   or the environment. Not in item 1b's scope.
6. The README's "Documentation" list still titles
   `docs/ros-distributions.md` "Why the distribution choice differs from
   `main`", which no longer describes it. That section is outside item 3's.
7. The README Quick start still says `make image` "first time; downloads and
   builds". With published images, `make up` alone would pull. Stage 07 owns
   that section at the moment.
8. With an unreadable `distros.json`, `compose-up` cannot know the default
   and would name `ROS_DISTRO=lyrical` in the hint. That path is unreachable
   through make, which refuses such a table first.
