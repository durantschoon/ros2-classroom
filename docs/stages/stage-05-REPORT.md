# Stage 05 report — Tests before the last port: pin the self-test itself

Branch: `stage-05-test-the-selftest`. Base: `python-port` (see Deviation 1 and 7
for which commit, and why it moved twice).

No script changed. `scripts/smoke-container` is byte-identical to its base
version: `sha256 5a5885903d1968a9b94086e5c33d0e625b6f1bd82022b2e2d1ba4460db25511e`
before the stage, after every mutation, and at commit time.

## 1. Checklist echo

### "The change"

| # | Asked for | Done | Where |
|---|---|---|---|
| 1 | `fakes.py`: record calls as one JSON array per line, arguments with newlines survive; `argv()` / `last_argv()` keep their signatures and results | yes | `tests/host/fakes.py`, `_FAKE_TEMPLATE`, `Sandbox._records/argv/last_argv` |
| 1 | `fakes.py`: record chosen environment variables per call, opt-in per fake, with an accessor | yes | `Sandbox.fake(..., record_env=…)`, `recorded_envs()`, `last_recorded_env()` |
| 1 | `fakes.py`: a `contains` match mode firing on a substring of any argument | yes | `rule(..., match="contains")` |
| 2 | `test_smoke_container.py`, black box, subprocess on a sandbox PATH, `COMPOSE` naming a fake; fake `podman` (`compose version`, `image inspect` → `ros`), fake `podman-compose`, fake `sleep`, fake `curl`; real tools found by running it | yes | `REAL_TOOLS` and the comment above it; see §6 for how the list was found |
| 2 | Isolation of the project: `-p ros2-tutorials-selftest` on every call, `SELFTEST_PROJECT` overrides, never the bare `ros2-tutorials`, holds through `make` | yes | class `ProjectIsolation`, 7 tests |
| 2 | Isolation of the port: banner names 6081, `SELFTEST_NOVNC_PORT` overrides, host `curl` on that port, in-container check on 6080 | yes | class `PortIsolation`, 4 tests |
| 2 | Isolation of the ROS graph: `ROS_DOMAIN_ID=99` in compose's environment, `SELFTEST_ROS_DOMAIN_ID` overrides, never 42 | yes | class `RosGraphIsolation`, 5 tests |
| 2 | Accounting: exit 1, an `N passed, M failed` line, `N + M` equals the `PASS`/`FAIL` lines, a `failed checks:` list naming each failure once | yes | class `Accounting`, 4 tests |
| 2 | The happy path: every check passes, exit 0, `M` is 0, no `failed checks:`; pin the ordered step titles and check names; build it as a table of `contains` rules | yes | `HAPPY_COMPOSE_RULES`, `HAPPY_TRANSCRIPT`, class `HappyPath`, 5 tests |
| 2 | Cleanup: last compose call is `down -v --remove-orphans` on all-pass, on all-fail, and on an early abort | yes | class `Cleanup`, 5 tests |
| 2 | `--keep`: no `down` call, hint names the project | yes | class `KeepFlag`, 5 tests |
| 2 | Readiness: recovers after a few failures; gives up loudly and still cleans up; fake `sleep` keeps both fast | yes | class `Readiness`, 5 tests, via the new `times=` rule budget (Deviation 3) |
| 2 | Engine detection failing mid-suite: pin what happens today, raise it, do not fix it | yes | class `EngineDetection`, 3 tests; Open question 1 |
| 2 | "Add any observable behaviour this list misses" | yes | class `Housekeeping`, 5 tests; see §6 |
| 2 | Prove the tests have teeth: five mutations, each caught, each reverted by copy-out/copy-back with a checksum | yes | §4 |
| 3 | `tests/host/README.md`: the new fake features and how the scenario is built | yes | `tests/host/README.md` |

### Definition of Done

| Item | Result |
|---|---|
| Baseline on the unmodified base: `make lint`, `make check` (114 expected) | pass — 114 tests, 4 skipped, 6.0 s (§2) |
| Baseline `make selftest` not re-measured (coordinator measured 48/48) | honoured; measured anyway at the end, see below |
| Final `make lint` passes | pass — 26 files, 26 ok, 0 advisory, 0 FAIL |
| Final `make check` passes, under 30 s, new count reported | pass — 162 tests, 4 skipped, 16.4 s (three repeats: 16.6 / 17.5 / 15.7 s wall; one 919 s outlier explained in Deviation 6) |
| Final `make check` under real Python 3.9 | pass — 162 tests, 57 skipped (§3) |
| Final `make selftest` once, still 48/48 | pass, and additionally confirmed transcript-identical to the pinned one (§5, Deviation 5) |
| Five mutations, each caught, each reverted with a matching checksum | done (§4) |
| `git status` clean after a `make check` run; `git diff python-port --stat` shows only allowed files | done (§7) |

## 2. Gate outputs, verbatim

### Baseline, on the unmodified base `1472555`

```
$ export PATH="$HOME/.local/bin:$PATH"
$ make lint
podman-compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: podman run --rm -v /home/durant/Repos/ds/ros2_turtlesim/.claude/worktrees/agent-a6e3d5801fead1ed6:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
ok       docker/bashrc.d/ros-workspace.sh      bash (sourced), enforced
ok       docker/desktop/openbox-autostart      shell, enforced
ok       docker/entrypoint.sh                  shell, enforced
ok       docker/scripts/init-workspace         python, container
ok       docker/scripts/install-ros-packages   python, container
ok       docker/scripts/pkg                    python, container
ok       docker/scripts/turtlesim-teleop       python, container
ok       docker/scripts/tutorial               python, container
ok       scripts/base-image-digest             python, host (3.9 grammar)
ok       scripts/check-host                    python, host (3.9 grammar)
ok       scripts/compose-command               python, host (3.9 grammar)
ok       scripts/compose-up                    python, host (3.9 grammar)
ok       scripts/lint-scripts                  python, host (3.9 grammar)
ok       scripts/open-url                      python, host (3.9 grammar)
ok       scripts/run-quiet                     python, host (3.9 grammar)
ok       scripts/smoke-container               shell, advisory
ok       scripts/workstation-help              python, host (3.9 grammar)
ok       tests/host/fakes.py                   python, host (3.9 grammar)
ok       tests/host/test_base_image_digest.py  python, host (3.9 grammar)
ok       tests/host/test_check_host.py         python, host (3.9 grammar)
ok       tests/host/test_compose_command.py    python, host (3.9 grammar)
ok       tests/host/test_compose_up.py         python, host (3.9 grammar)
ok       tests/host/test_open_url.py           python, host (3.9 grammar)
ok       tests/host/test_run_quiet.py          python, host (3.9 grammar)
ok       tests/host/test_workstation_help.py   python, host (3.9 grammar)
lint-scripts: 25 files: 25 ok, 0 advisory, 0 FAIL
```

```
$ make check
python3 -m unittest discover -s tests/host
.......................................................................ssss.......................................................................................
----------------------------------------------------------------------
Ran 114 tests in 6.006s

OK (skipped=4)
ELAPSED 6.18 s
```

`make selftest` was not re-measured on the base, as the prompt directed.

### Final, on this branch

```
$ make lint
podman-compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
...
ok       scripts/smoke-container               shell, advisory
ok       scripts/workstation-help              python, host (3.9 grammar)
ok       tests/host/fakes.py                   python, host (3.9 grammar)
ok       tests/host/test_base_image_digest.py  python, host (3.9 grammar)
ok       tests/host/test_check_host.py         python, host (3.9 grammar)
ok       tests/host/test_compose_command.py    python, host (3.9 grammar)
ok       tests/host/test_compose_up.py         python, host (3.9 grammar)
ok       tests/host/test_open_url.py           python, host (3.9 grammar)
ok       tests/host/test_run_quiet.py          python, host (3.9 grammar)
ok       tests/host/test_smoke_container.py    python, host (3.9 grammar)
ok       tests/host/test_workstation_help.py   python, host (3.9 grammar)
lint-scripts: 26 files: 26 ok, 0 advisory, 0 FAIL
```

```
$ make check
python3 -m unittest discover -s tests/host
.......................................................................ssss.......................................................................................
----------------------------------------------------------------------
Ran 162 tests in 16.353s

OK (skipped=4)
ELAPSED 16.56 s
```

```
$ make selftest        # the run captured in full; see §5
...
== Result
48 passed, 0 failed

== cleaning up
EXIT=0
```

| Gate | Baseline | Final |
|---|---|---|
| `make lint` | 25 files, 25 ok, 0 FAIL | 26 files, 26 ok, 0 FAIL |
| `make check` | 114 tests, 4 skipped, 6.0 s | 162 tests, 4 skipped, 16.4 s |
| `make check` on real 3.9 | 114 tests, 9 skipped, 6.2 s | 162 tests, 57 skipped, 5.8 s |
| `make selftest` | 48/48 (coordinator's measurement) | 48/48, exit 0 |

## 3. Per-module counts, and the Python 3.9 run

```
$ python3 -m unittest discover -s tests/host -v | grep -oE "\(test_[a-z_]+\." | sort | uniq -c | sort -k2
     16 (test_base_image_digest.
     11 (test_check_host.
     16 (test_compose_command.
     23 (test_compose_up.
     15 (test_open_url.
     11 (test_run_quiet.
     48 (test_smoke_container.
     22 (test_workstation_help.
```

162 total; the 48 new ones are all in `test_smoke_container.py`.

```
$ podman run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo \
      docker.io/library/python:3.9-slim python -m unittest discover -s tests/host
.......................................................................ssss.................sssssssssssssssssssssssssssssssssssssssssssssssssssss.................
----------------------------------------------------------------------
Ran 162 tests in 5.764s

OK (skipped=57)
```

The same image on the unmodified test set, for comparison:

```
$ podman run ... python -m unittest discover -s tests/host -p 'test_[!s]*.py'
Ran 114 tests in 6.192s

OK (skipped=9)
```

So 57 = 9 pre-existing + 48 new. The skip reasons, counted:

| Count | Reason | New? |
|---|---|---|
| 48 | `scripts/smoke-container is bash and drives the real Makefile; this machine is missing make` | yes |
| 5 | `make is not installed` (`test_workstation_help`) | no, pre-existing |
| 4 | `open-url` WSL branch reason (`/proc/version` inside the container is still the WSL kernel) | no, pre-existing |

**Which of the new tests skip there, and why.** All 48. `python:3.9-slim` has no
`make`, and `scripts/smoke-container` runs the real `Makefile` in its "Student
make targets" step, so no scenario can be built. The skip is decided once, at
import, by `MISSING_TOOLS`, and the whole module is decorated. The value of the
3.9 run for this file is therefore that the module *imports and collects* under
3.9 — no 3.10-only syntax, no 3.10-only stdlib — which is what the grammar gate
in `make lint` also checks, from a different angle. On the host, where `make` and
`bash` exist, all 48 run: `make check` reports 4 skips, the same 4 as the
baseline.

## 4. The five mutations

Procedure, for each: copy the pristine file out to the scratchpad, `sed` the
mutation in from that copy, run `test_smoke_container.py`, copy the pristine file
back, checksum. `git checkout --` was never used.

Pristine checksum, throughout:
`5a5885903d1968a9b94086e5c33d0e625b6f1bd82022b2e2d1ba4460db25511e`.

| # | Mutation | Diff | Mutated sha256 | Caught by | Total failures | sha256 after revert |
|---|---|---|---|---|---|---|
| 1 | drop the `-p` project from `COMPOSE` | `COMPOSE="${COMPOSE} -p ${SELFTEST_PROJECT}"` → `COMPOSE="${COMPOSE}"` | `5b46a0c4…53bc7` | `ProjectIsolation.test_every_compose_call_carries_the_selftest_project` (+18 more) | 19 | `5a588590…5511e` ✔ |
| 2 | make `bad` stop counting | `bad() { …; failed=$((failed + 1)); failures+=("$1"); }` → without the increment | `8924ad47…2db16` | `Accounting.test_a_failing_run_exits_one_and_accounts_for_every_check`; `Accounting.test_the_failed_checks_list_names_each_failure_once_and_in_order` (error: no `failed checks:` line to index) | 3 | `5a588590…5511e` ✔ |
| 3 | exit 0 unconditionally at the end | line 497 `exit 1` → `exit 0` | `9e277e89…ba6ec` | `Accounting.test_a_failing_run_exits_one_and_accounts_for_every_check`; `KeepFlag.test_keep_still_reports_the_same_verdict` | 2 | `5a588590…5511e` ✔ |
| 4 | ignore `--keep` | line 48 `[ "${1:-}" = "--keep" ] && KEEP=1` → `KEEP=0` | `16db8f4f…be202` | `KeepFlag.test_keep_makes_no_down_call_at_all` (+2 more) | 3 | `5a588590…5511e` ✔ |
| 5 | stop exporting `ROS_DOMAIN_ID` | line 44 `export ROS_DOMAIN_ID=…` → `ROS_DOMAIN_ID=…` | `a222f67e…5651e` | `RosGraphIsolation.test_every_compose_call_runs_in_the_selftest_domain`; `RosGraphIsolation.test_selftest_ros_domain_id_overrides_it` | 2 | `5a588590…5511e` ✔ |

The full failing lists, verbatim:

```
### mutation: 1. drop the -p project from COMPOSE
FAIL: test_an_early_abort_still_removes_the_project (test_smoke_container.Cleanup)
FAIL: test_the_all_fail_run_ends_by_removing_its_own_project (test_smoke_container.Cleanup)
FAIL: test_the_all_pass_run_ends_by_removing_its_own_project (test_smoke_container.Cleanup)
FAIL: test_the_teardown_deletes_volumes_only_inside_the_selftest_project (test_smoke_container.Cleanup)
FAIL: test_a_missing_engine_still_cleans_up (test_smoke_container.EngineDetection)
FAIL: test_the_container_is_recreated_before_the_persistence_step (test_smoke_container.Housekeeping)
FAIL: test_the_demo_profile_is_named_on_both_the_up_and_the_stop (test_smoke_container.Housekeeping)
FAIL: test_the_first_compose_call_builds_and_the_second_starts_the_desktop (test_smoke_container.Housekeeping)
FAIL: test_keep_honours_an_overridden_project_in_its_hint (test_smoke_container.KeepFlag)
FAIL: test_keep_prints_a_removal_hint_naming_the_isolated_project (test_smoke_container.KeepFlag)
FAIL: test_every_compose_call_carries_the_selftest_project (test_smoke_container.ProjectIsolation)
FAIL: test_selftest_project_overrides_the_prefix_on_every_call (test_smoke_container.ProjectIsolation)
FAIL: test_the_banner_names_the_isolated_project_and_the_host_port (test_smoke_container.ProjectIsolation)
FAIL: test_the_exported_compose_already_carries_the_project_flag (test_smoke_container.ProjectIsolation)
FAIL: test_the_happy_path_keeps_the_project_on_every_call_too (test_smoke_container.ProjectIsolation)
FAIL: test_the_project_flag_reaches_the_calls_made_through_make (test_smoke_container.ProjectIsolation)
FAIL: test_a_desktop_that_never_answers_fails_the_check_and_exits_one (test_smoke_container.Readiness)
FAIL: test_a_retried_desktop_goes_on_to_run_the_whole_suite (test_smoke_container.Readiness)
FAIL: test_the_readiness_probe_is_exec_not_ps (test_smoke_container.Readiness)
Ran 48 tests in 10.002s
FAILED (failures=19)

### mutation: 2. bad stops counting
ERROR: test_the_failed_checks_list_names_each_failure_once_and_in_order (test_smoke_container.Accounting)
FAIL: test_a_failing_run_exits_one_and_accounts_for_every_check (test_smoke_container.Accounting)
FAIL: test_keep_still_reports_the_same_verdict (test_smoke_container.KeepFlag)
Ran 48 tests in 10.068s
FAILED (failures=2, errors=1)

### mutation: 3. exit 0 unconditionally at the end
FAIL: test_a_failing_run_exits_one_and_accounts_for_every_check (test_smoke_container.Accounting)
FAIL: test_keep_still_reports_the_same_verdict (test_smoke_container.KeepFlag)
Ran 48 tests in 9.851s
FAILED (failures=2)

### mutation: 4. ignore --keep
FAIL: test_keep_honours_an_overridden_project_in_its_hint (test_smoke_container.KeepFlag)
FAIL: test_keep_makes_no_down_call_at_all (test_smoke_container.KeepFlag)
FAIL: test_keep_prints_a_removal_hint_naming_the_isolated_project (test_smoke_container.KeepFlag)
Ran 48 tests in 10.280s
FAILED (failures=3)

### mutation: 5. stop exporting ROS_DOMAIN_ID
FAIL: test_every_compose_call_runs_in_the_selftest_domain (test_smoke_container.RosGraphIsolation)
FAIL: test_selftest_ros_domain_id_overrides_it (test_smoke_container.RosGraphIsolation)
Ran 48 tests in 10.262s
FAILED (failures=2)
```

Mutation 5 is the one that justifies `record_env`: the mutation leaves every
printed string identical — the in-container check still reads
`[ "$ROS_DOMAIN_ID" = "99" ]` — and only the *exported environment* of the
compose process changes. Nothing observable in stdout moves, so only a test that
records the child's environment can see it.

Note on a first pass, later corrected: a sixth test,
`Housekeeping.test_the_repository_is_left_untouched_by_a_run`, also failed under
all five mutations, because the mutation itself dirties `scripts/smoke-container`
and the test compared the tree against *clean*. It now compares
`git status --porcelain` taken at module import against the same after the runs,
which is the property actually wanted ("a run of the suite changes nothing").
The five mutation runs in the tables above are the re-runs, after that fix.

## 5. The ordered transcript of the happy-path run

Pinned as `HAPPY_TRANSCRIPT` in `tests/host/test_smoke_container.py`: 62 entries,
13 step titles and 48 check names, plus the trailing `cleaning up` the EXIT trap
prints with the same `== ` prefix.

```
== Build
  PASS image builds
== Start the desktop
  PASS desktop container accepts commands
== Image and environment
  PASS the image defaults to the non-root ros user
  PASS desktop programs run as the non-root ros user
  PASS ROS_DISTRO is set
  PASS the self-test runs in its own ROS domain, not the student default
  PASS ros2 is on PATH
  PASS rosdep is on PATH
  PASS colcon is on PATH
== Turtlesim
  PASS turtlesim_node and turtle_teleop_key are installed
  PASS turtlesim stays alive for 5s on the virtual display
== Browser desktop
  PASS noVNC answers inside the container
  PASS noVNC answers on the host at http://localhost:6081
== Cross-service DDS discovery
  PASS a node in one service receives messages from another service
== Package installation helper
  PASS install-ros-packages installs a ROS short name
  PASS installed package is runnable
  PASS install-ros-packages fails loudly on a missing package
== Source workspace build
  PASS colcon builds a source package in the persistent workspace
  PASS new shells source the workspace overlay automatically
== pkg helper: templates, interfaces, and lint
  PASS pkg new --template pubsub builds
  PASS templated package registers its talker executable
  PASS templated pubsub node actually publishes on /chatter
  PASS pkg new --interfaces builds
  PASS ros2 interface show works for a generated message
  PASS ros2 interface show works for a generated service
  PASS pkg test reports a clean lint result for a generated package
  PASS pkg test exits non-zero when a test really fails
  PASS pkg test reads only the tested package's results
== Student make targets (run from the host, as a student would)
  PASS make package prints the real command and points at make build
  PASS printed commands quote arguments so they paste correctly
  PASS make build prints colcon build and points at make run
  PASS make test reports the real colcon test-result verdict
  PASS make typed inside the container explains where to run it
== Container helpers: tutorial, init-workspace, pkg refusals
  PASS a second init-workspace reports the workspace is already initialized
  PASS init-workspace leaves the existing workspace marker untouched
  PASS tutorial with no arguments exits 2 and prints usage
  PASS tutorial clone echoes the real git command and succeeds
  PASS the clone lands in /workspace/src
  PASS tutorial list names the cloned repository
  PASS tutorial build echoes colcon build --packages-select and succeeds
  PASS tutorial deps echoes both rosdep commands and succeeds
  PASS pkg with no arguments exits 2 and prints usage
  PASS pkg new --python --interfaces is refused with an explanation
  PASS the refused interface package was never created
  PASS pkg new refuses to create a package that already exists
  PASS the existing package is byte-identical after the refusal
== Persistence across container recreation
  PASS workspace source survives container recreation
  PASS built overlay survives container recreation
== Result
== cleaning up
```

**This was checked against reality, not only against the fakes** (extra
verification, Deviation 5). The transcript of a real `make selftest` run —
containers, Podman, the built image, 48/48 — was extracted and compared with the
pinned list entry by entry:

```
pinned entries: 62
real entries:   62
IDENTICAL
```

So the canned scenario reproduces the real suite's output exactly, which is what
makes it usable as stage 06's contract.

## 6. Behaviours found that the prompt's list missed

Found by running the suite, then reading the recorded calls. All are pinned
unless the row says otherwise.

| Behaviour | Pinned in | Comment |
|---|---|---|
| **The suite writes two log files into the *host's* `/tmp`.** `>/tmp/pkg-smoke-pubsub.log` (line 239) and `>/tmp/pkg-smoke-msgs.log` (line 261) are host-side redirections of `in_desktop`'s output, not container paths. Every other `/tmp/…` in the script is inside a command string and lands in the container. | `Housekeeping.test_it_writes_two_log_files_into_the_hosts_own_tmp` | Pinned as-is. Almost certainly not intended — see Open question 2. It is also the one way these tests write outside their temporary directory; nothing else does. |
| **`export COMPOSE` carries the `-p` flag as part of its value**, which is the mechanism by which the Makefile targets address the self-test's project. | `ProjectIsolation.test_the_exported_compose_already_carries_the_project_flag` | A port that passed the project some other way (a `COMPOSE_PROJECT_NAME`, say) would pass every other project test and still break the Makefile path. |
| **`--profile demo` is named on both the `up` and the `stop`**, because podman-compose needs it on every subcommand addressing a profile service. | `Housekeeping.test_the_demo_profile_is_named_on_both_the_up_and_the_stop` | Easy to lose in a rewrite; the check that needs it would then fail only on Podman. |
| **The first two compose calls are `build` then `up -d desktop`**, in that order. | `Housekeeping.test_the_first_compose_call_builds_and_the_second_starts_the_desktop` | |
| **The persistence step recreates the container with `up -d --force-recreate desktop`.** | `Housekeeping.test_the_container_is_recreated_before_the_persistence_step` | Without `--force-recreate` the step proves nothing. |
| **The readiness loop gives up after exactly 30 attempts**, and each failed attempt is followed by `sleep 2`. | `Readiness.test_it_gives_up_rather_than_retrying_forever`, `…test_a_desktop_that_needs_a_few_tries_is_accepted` | |
| **`ps` is never used to decide readiness** — the probe is `exec … bash -lc true`. | `Readiness.test_the_readiness_probe_is_exec_not_ps` | The comment in the script says why; nothing enforced it. |
| **Exactly one teardown happens** on a normal run (not zero, not two). | `Cleanup.test_exactly_one_teardown_happens` | |
| **`--keep` does not change the verdict** — same exit status and same `N passed, M failed`. | `KeepFlag.test_keep_still_reports_the_same_verdict` | |
| **Every check name on the all-pass run is distinct**, so the `failed checks:` list is unambiguous. | `Accounting.test_every_check_name_is_distinct_on_the_all_pass_run` | |
| **The all-fail run asks the same checks, in the same step order, and the same number of them** as the all-pass run. | `HappyPath.test_the_all_fail_run_asks_the_same_checks_in_the_same_order` | Failure messages interpolate detail, so only the step order and the count can be compared. |
| **The image is inspected by name, `ros2-tutorials:lyrical`, through the detected engine** — not through compose. | `EngineDetection.test_the_engine_is_used_to_inspect_the_image_by_name` | |
| **`SELFTEST_ROS_DOMAIN_ID` also moves the in-container assertion**, not just the exported variable. | `RosGraphIsolation.test_the_domain_check_follows_the_override` | |
| `[ "${1:-}" = "--keep" ] && KEEP=1` does not trip `set -e` when there is no argument, because a failing command in a `&&` list is exempt unless it is the last one. | not pinned directly | Observed and relied on: every no-argument scenario would abort at line 48 otherwise. Pinned implicitly by every test that runs the suite with no arguments. |
| The suite's real host-tool needs, found by running it under an almost-empty PATH and reading the `command not found` lines: `bash`, `dirname`, `seq`, `grep`, `tail`, `head`, `tr`, `awk`, `make`. Notably **not** `sed`, `cat` or `curl`-as-a-real-tool — `sed` and `cat` only ever appear inside container command strings. | `REAL_TOOLS` | Without `dirname` the script does not abort: `cd "$(dirname "$0")/.."` becomes `cd /..`, i.e. `/`, and it runs the *wrong* `Makefile` — or none. That is a real, if remote, hazard, noted under Open question 5. |

## 7. `git diff python-port --stat`

```
 tests/host/README.md               |  69 +++
 tests/host/fakes.py                |  91 +++-
 tests/host/test_smoke_container.py | 849 +++++++++++++++++++++++++++++++++++++
 3 files changed, 998 insertions(+), 11 deletions(-)
```

Only allowed files. `docs/stages/stage-05-REPORT.md` joins them in the commit.

`git status --porcelain` after a `make check` run, before staging:

```
 M tests/host/README.md
 M tests/host/fakes.py
?? tests/host/test_smoke_container.py
```

Nothing else — no stray files in the repository, although the suite `cd`s to the
repository root and runs the real `Makefile` there.

## 8. Deviations

1. **The worktree was created at a stale commit, for the fifth stage running.**
   `docs/stages/stage-05-PROMPT.md` was absent at `cca3884`. Ran
   `git fetch origin && git merge --ff-only origin/python-port` as the prompt's
   "First step" directs, landing on `1472555`. Recorded here as instructed.

2. **`git branch -m stage-05-test-the-selftest`** renamed the worktree's
   generated branch, per the setup instructions. No nested worktree was created.

3. **A fourth feature was added to `fakes.py` beyond the three the prompt
   lists: a `times=N` budget on a rule.** The prompt requires pinning "when
   `exec` fails a few times and then succeeds, the suite proceeds". The readiness
   probe repeats a byte-identical argv, so no stateless rule can answer it
   differently on the fourth call. `times=N` spends a rule after N matches and
   lets the identical call fall through to the rules below; the count lives in a
   sidecar file next to the call log. It is additive and defaults to `None`, so
   every existing rule behaves exactly as before, and all 114 pre-existing tests
   pass unchanged.

4. **`ARG_SEP` was kept in `fakes.py` although nothing uses it any more.** The
   call format is JSON now. The prompt said the change must be API-preserving, so
   the name stays, with a comment saying why.

5. **Extra, read-only verification, beyond what the prompt asked for.**
   (a) `make selftest` was run three times rather than once, and its full output
   captured; (b) the transcript of a real 48/48 run was compared entry-by-entry
   with the pinned `HAPPY_TRANSCRIPT` and is identical (§5). (b) is the check
   that turns "the fakes agree with themselves" into "the fakes agree with the
   real suite", and it seemed worth the two minutes. It also surfaced Open
   question 3.

6. **One `make check` measurement came back at 919 s wall time** while the
   unittest runner inside it reported 18.6 s. It was the invocation immediately
   following three back-to-back `make selftest` runs; the Makefile evaluates
   `$(shell ./scripts/compose-command --make)` at parse time, which probes
   `podman compose version`, and Podman was still busy tearing down. Three
   repeats immediately afterwards gave 16.6 s, 17.5 s and 15.7 s. Reported rather
   than quietly dropped; the gate's own number, 16.4 s of test time, is stable.

7. **`python-port` moved during the stage, and this branch was fast-forwarded a
   second time.** Two docs-only commits (`5aa4aef`, `fa330eb`, adding
   `docs/stages/SKILL-FEEDBACK.md` and nine lines to `docs/stages/README.md`)
   landed after the base measurement. Left alone, `git diff python-port --stat`
   would have shown them as deletions. Since the base `1472555` is an ancestor,
   and neither commit touches anything this stage runs or edits, the branch was
   fast-forwarded to `fa330eb` before committing, and `make lint` and `make check`
   were re-run there with identical results. The new README section
   ("Lessons that belong upstream") adds no guardrail bearing on this stage.

8. **One new test skips itself when `git` is unavailable.**
   `Housekeeping.test_the_repository_is_left_untouched_by_a_run` needs `git` to
   read the working tree's status; it is guarded so the module still imports
   where `git` is absent. In practice the whole module already skips there, for
   want of `make`.

9. **`scripts/smoke-container` was modified five times, temporarily.** Each
   mutation was applied from a pristine scratchpad copy and reverted by copying
   that copy back, never with `git checkout --`. The checksum is recorded before,
   during, and after each (§4), and matches the base at commit time.

## 9. Open questions

1. **Engine detection failing mid-suite kills the run silently.** Pinned as it
   is today, in `EngineDetection`, and not fixed, as instructed. With `COMPOSE`
   set but no engine for `scripts/compose-command --engine` to find, the suite
   runs its Build, Start and part of Image-and-environment steps, then dies under
   `set -e` at line 108 with `no working docker or podman compose found` on
   stderr and **no `N passed, M failed` line and no `failed checks:` list at
   all** — exit 1, but a reader who greps for the summary sees nothing. Worth
   noting: the cleanup trap still fires, so nothing is left running. This is the
   one place in the suite where a failure is not accounted for, and it is exactly
   the "silently stop counting" failure mode stage 05 exists to guard against.
   Whether stage 06 should preserve it is an architect decision.

2. **The two `>/tmp/pkg-smoke-*.log` redirections are on the host side, and
   almost certainly should not be.** Every sibling redirection in the same file
   (`/tmp/turtlesim.log`, `/tmp/pkg-smoke-broken.log`, `/tmp/pkg-smoke-talker.log`)
   is inside the single-quoted command string and therefore lands in the
   container, where the log is actually useful. These two sit outside it, so the
   container's output is discarded into the *host's* `/tmp` and never looked at
   again. The behaviour is pinned so that stage 06 cannot change it by accident,
   but I believe the pinned behaviour is wrong, and it is also the only reason
   these tests write outside their temporary directory. If it is a bug, it is a
   one-character-class fix and it should be its own change, not part of the port.

3. **`make selftest` is flaky on the `Xvfb` user check.** Three consecutive runs
   during this stage gave 48/48, then 47/48, then 48/48; the failure was
   `desktop programs are not running as ros` (line 117,
   `exec -T desktop ps -o user= -C Xvfb`). Readiness is measured by `exec`
   working, which it does before Xvfb has necessarily started, so the probe can
   read an empty user. This is pre-existing and nothing to do with this stage —
   `scripts/smoke-container` is byte-identical to its base — but a ~1-in-3 flake
   in the project's own oracle will make stage 06's before/after comparison
   ambiguous unless it is dealt with first. The other two runs were
   transcript-identical to the pinned list.

4. **Do not pin the number of checks, but 48 is now in the report twice.**
   `HAPPY_TRANSCRIPT` pins the ordered *names*, as the prompt asked, and the
   accounting tests pin *relationships*. But a new check added to the suite will
   fail `HappyPath.test_the_ordered_transcript_is_what_stage_06_must_reproduce`
   until the table is updated — that is deliberate (it is the contract), and it
   is a one-line edit, but whoever adds a check next should know the list exists.

5. **The suite's `cd` is unguarded.** `cd "$(dirname "$0")/.."` has no `|| exit`,
   and with `dirname` missing from PATH — which is how it behaved in the first
   probe run here — `$(dirname "$0")` is empty, `cd "/.."` succeeds, and the suite
   proceeds from `/`, where `./scripts/...` and `make` mean something else
   entirely. `set -e` does not catch it because `cd` succeeded. Unlikely in
   practice; trivially fixed in the port by resolving the path in Python.

6. **`Housekeeping.test_the_repository_is_left_untouched_by_a_run` compares the
   tree against its state at module import, not against clean.** That is the
   right property, and it keeps the file usable while someone has uncommitted
   work, but it means the test would not notice a run that reverted a change
   someone had made and then re-made it. This seems fine; flagging the choice.
