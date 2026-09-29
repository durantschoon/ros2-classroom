# Stage 11 report: choose the ROS distribution with ROS_DISTRO, from one table

Branch `stage-11-distro-table`, base `multi-distro`.

## 1. First step

```
$ git log --oneline -1
4afa6cd docs(stages): stage 11 prompt -- choose the distribution from one table, on a new integration branch
```

`docs/stages/stage-11-PROMPT.md` was present, so no fetch or merge was needed.
The worktree branch was renamed with `git branch -m stage-11-distro-table`.

## 2. Checklist

### The change

- [x] 1. `distros.json` (new): `_comment`, `default: lyrical`, and four entries
  with the prompt's full digests. It is laid out exactly as `refresh` writes it
  (one line per distribution), so a refresh that changes one digest changes one
  line. `render_table(parse_table(file)) == file` was checked.
- [x] 2. `scripts/distros` (new, stdlib, 3.9): `env`, `env --make`, `list`,
  `refresh`. It finds `../distros.json`, `../.env` and `./base-image-digest`
  from its own location. There is no relocation variable.
- [x] 3. `Makefile`: the resolver replaces `ROS_DISTRO ?= lyrical`. The four
  inputs are handed over explicitly, `$(error)` carries the resolver's message,
  and each `NAME=value` is exported. Commented. New `distros` target. `digest`
  is now `./scripts/distros refresh`, echoed, with a new comment. `reset`'s
  three echo lines name `$(COMPOSE_PROJECT_NAME)` and `$(ROS_DISTRO)`.
  `distros` is added to `.PHONY`.
- [x] 4. `compose.yaml`: `image: ${IMAGE_NAME:-...}:${IMAGE_TAG:-latest}` plus
  a one-line comment. The build-arg defaults are unchanged.
- [x] 5. `Dockerfile`: header comment only. `.env.example` keeps
  `ROS_DISTRO=lyrical`, and `ROS_BASE_DIGEST` is now a commented-out override.
  The comment names `make distros`, says each distribution has its own
  `/workspace`, and gives `eval "$(./scripts/distros env)"` for plain
  `docker compose`.
- [x] 6. `scripts/workstation-help`: a `make distros` row after `make image` in
  "Start here". `make digest` now reads "Refresh every distribution's
  base-image digest".
- [x] 7. `ros2.ps1`: the same resolution runs before `$Url`. `ROS_DISTRO`
  comes from the environment (including a `ROS_DISTRO=` argument), else
  `.env`, else the default. An unsupported name gets the same message and exits
  2. It sets the four `$env:` values and keeps explicit ones. A new `distros`
  command prints the same table with the `.\ros2.ps1` hint. `help` lists
  `distros`, and its last line names the distribution and project. `reset`
  names the project. ASCII only; run under Windows PowerShell 5.1 (V4).
  `uninstall` code is untouched.
- [x] 8. Workflow: `multi-distro` is added to `on.push.branches`, nothing else.
- [x] 9. `README.md`: a Configuration paragraph (and see Deviation 3).

### Definition of Done

- [x] Baseline on the unmodified base: `make lint` ok. `make check` ran 209
  tests, OK (skipped=22) without pwsh and OK (skipped=7) with pwsh.
  `make selftest` was not re-measured on the base, as instructed.
- [x] Final `make lint` passes, and `scripts/distros` is classified
  `python, host (3.9 grammar)`.
- [x] Final `make check` passes with **251 tests** (209 + 33 in
  `test_distros.py` + 8 in `test_ros2_ps1.py` + 1 in
  `test_workstation_help.py`).
  `PWSH=$SCRATCH/pwsh/pwsh make check` also passes, with the `ros2.ps1` tests
  running (PowerShell 7.6.6 was still at that path). `test_distros.py` alone
  takes 3.8-4.1 s, under the 15 s budget.
- [x] Tests 1-28 are present, all five mutations were caught, and
  Verification 1-5 pass.
- [x] `grep -n "shell=True\|os.system" scripts/distros` finds nothing (grep
  exit 1).
- [x] `git diff multi-distro --stat` shows only allowed files (section 6).

## 3. Gate outputs, verbatim

`$SCRATCH` stands for this session's scratchpad directory. Every gate was run
through a wrapper that does `cd <worktree>; export PATH="$HOME/.local/bin:$PATH";
[PWSH=$SCRATCH/pwsh/pwsh] time make <gate>` and appends the exit status.

### Baseline (unmodified `4afa6cd`)

`make lint`:

```
docker compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: docker run --rm -v /home/durant/Repos/ds/ros2_turtlesim/.claude/worktrees/agent-a1919301c3a1fb515:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
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
ok       tests/host/test_open_url.py           python, host (3.9 grammar)
ok       tests/host/test_ros2_ps1.py           python, host (3.9 grammar)
ok       tests/host/test_run_quiet.py          python, host (3.9 grammar)
ok       tests/host/test_smoke_container.py    python, host (3.9 grammar)
ok       tests/host/test_uninstall.py          python, host (3.9 grammar)
ok       tests/host/test_workstation_help.py   python, host (3.9 grammar)
lint-scripts: 32 files: 32 ok, 0 advisory, 0 FAIL
make lint  0.50s user 0.31s system 24% cpu 3.279 total
exit 0
```

`make check`:

```
python3 -m unittest discover -s tests/host
.................ss..........s.........................................................ssss......sssssssssssssss.................................................................................................
----------------------------------------------------------------------
Ran 209 tests in 49.278s

OK (skipped=22)
make check  38.50s user 10.96s system 99% cpu 49.795 total
exit 0
```

`PWSH=$SCRATCH/pwsh/pwsh make check` (a clean rerun; see Deviation 1):

```
python3 -m unittest discover -s tests/host
.................ss..........s.........................................................ssss......................................................................................................................
----------------------------------------------------------------------
Ran 209 tests in 90.004s

OK (skipped=7)

real	1m30.698s
user	1m12.419s
sys	0m21.235s
exit 0
```

### Final

`make lint`:

```
docker compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: docker run --rm -v /home/durant/Repos/ds/ros2_turtlesim/.claude/worktrees/agent-a1919301c3a1fb515:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
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

real	0m2.832s
user	0m0.528s
sys	0m0.378s
exit 0
```

`make check`:

```
python3 -m unittest discover -s tests/host
.................ss..........s..........................................................................................ssss......sssssssssssssssssssssss..................................................................................................
----------------------------------------------------------------------
Ran 251 tests in 89.532s

OK (skipped=30)

real	1m30.401s
user	1m8.917s
sys	0m21.211s
exit 0
```

`PWSH=$SCRATCH/pwsh/pwsh make check`:

```
python3 -m unittest discover -s tests/host
.................ss..........s..........................................................................................ssss...............................................................................................................................
----------------------------------------------------------------------
Ran 251 tests in 117.162s

OK (skipped=7)

real	1m58.067s
user	1m34.459s
sys	0m26.928s
exit 0
```

On wall time: the final `make check` took 89.5 s against the baseline's 49.3 s.
The host was busier by then. With the *base* Makefile swapped back in
(copy-out, copy-back, checksum verified), `test_smoke_container` alone took
53.0 s, against 61.4 s and 55.2 s with this stage's Makefile. Most of the
increase is host load. The stage's own cost is a few seconds from one extra
`python3` start per `make` parse, which the smoke-suite tests do many times.
See Open question 9.

## 4. Tests, mutations, verification

### Tests 1-28

| # | Test |
|---|---|
| 1 | `test_distros.EnvTests.test_nothing_set_is_the_default_under_its_old_names` |
| 2 | `test_distros.EnvTests.test_another_distribution_gets_its_own_names` |
| 3 | `test_distros.EnvTests.test_naming_the_default_explicitly_gives_the_default_names` |
| 4 | `test_distros.EnvTests.test_dotenv_chooses_bare_quoted_and_after_a_comment` (bare, `"..."`, `'...'`, after a comment and blank line), `test_the_environment_beats_dotenv`, `test_an_empty_environment_value_falls_through_to_dotenv` |
| 5 | `test_distros.EnvTests.test_explicit_settings_in_the_environment_survive` |
| 6 | `test_distros.EnvTests.test_an_unsupported_name_from_the_environment_is_refused`, `test_an_unsupported_name_from_dotenv_is_refused` |
| 7 | `test_distros.EnvTests.test_make_form_is_four_bare_assignments` |
| 8 | `test_distros.ListTests.test_list_shows_a_header_and_a_row_per_distribution` |
| 9 | `test_distros.RefreshTests.test_nothing_new_leaves_the_table_byte_identical` (bytes and mtime unchanged; one call per name) |
| 10 | `test_distros.RefreshTests.test_one_new_digest_changes_only_its_own_entry` |
| 11 | `test_distros.RefreshTests.test_a_failed_fetch_keeps_the_old_digest_and_fails` |
| 12 | `test_distros.MalformedTableTests.test_not_json` (for `env`, `list`, `refresh`), `test_no_distros`, `test_a_default_not_in_the_table` |
| 13 | `test_distros.UsageTests.test_no_subcommand_or_an_unknown_one_is_a_usage_error` (none, `bogus`, `env --bogus`, `list extra`) |
| 14 | `test_distros.ListTests.test_a_closed_pipe_is_not_an_error` (the read end is closed before the script starts) |
| 15 | `test_distros.MakefileTests.test_a_command_line_distribution_reaches_compose` |
| 16 | `test_distros.MakefileTests.test_nothing_set_gives_compose_the_default` |
| 17 | `test_distros.MakefileTests.test_an_environment_distribution_reaches_compose` |
| 18 | `test_distros.MakefileTests.test_an_unsupported_distribution_stops_before_compose` |
| 19 | `test_distros.MakefileTests.test_make_distros_lists_them_with_the_hint` |
| 20 | `test_distros.MakefileTests.test_make_digest_runs_the_refresh_and_echoes_it` |
| 21 | `test_distros.MakefileTests.test_reset_names_the_distribution_and_its_project_and_removes_nothing` |
| 22 | `test_distros.ConsistencyTests.test_dockerfile_arg_defaults`, `test_compose_build_arg_defaults`, `test_env_example_distribution` |
| 23 | `test_workstation_help.DistrosRowTests.test_make_distros_is_in_start_here_after_make_image` |
| 24 | `test_ros2_ps1.DistroTests.test_a_named_distribution_reaches_docker` |
| 25 | `test_ros2_ps1.DistroTests.test_nothing_set_gives_docker_the_default` |
| 26 | `test_ros2_ps1.DistroTests.test_an_unsupported_distribution_is_refused_before_docker` |
| 27 | `test_ros2_ps1.DistroTests.test_dotenv_chooses_and_the_environment_beats_it` (and a `ROS_DISTRO=` argument beats it too) |
| 28 | `test_ros2_ps1.DistroTests.test_distros_prints_the_table_and_the_hint` |

Tests beyond the list: `EnvTests.test_the_export_form_evaluates_in_a_shell`,
`RefreshTests.test_an_answer_that_is_not_a_digest_is_not_used`,
`MalformedTableTests.test_a_missing_table`,
`MakefileTests.test_a_dotenv_distribution_reaches_compose`, and in
`test_ros2_ps1.DistroTests`: `test_explicit_settings_are_kept`,
`test_help_names_the_distribution_and_project_last`, and
`test_reset_names_the_project_it_would_remove`.

### Mutations

Each mutation was applied by a script. The script ran
`python3 -m unittest test_distros`, restored the file by copying back the saved
original, and compared SHA-256 before and after (first 16 hex digits shown).
The final run was after the last code change (Deviation 6).

| Mutation | File | Suite exit | Result | Caught by | Checksum | Restore |
|---|---|---|---|---|---|---|
| M1 default gets its own name as tag | scripts/distros | exit 1 | Ran 33 tests in 4.026s FAILED (failures=4) | caught by: test_list_shows_a_header_and_a_row_per_distribution, test_naming_the_default_explicitly_gives_the_default_names, test_nothing_set_gives_compose_the_default, test_nothing_set_is_the_default_under_its_old_names | sha before 351e31aef94a3a67 after 351e31aef94a3a67 | restored |
| M2 .env beats the environment | scripts/distros | exit 1 | Ran 33 tests in 3.948s FAILED (failures=1) | caught by: test_the_environment_beats_dotenv | sha before 351e31aef94a3a67 after 351e31aef94a3a67 | restored |
| M3 unsupported falls back to the default | scripts/distros | exit 1 | Ran 33 tests in 3.783s FAILED (failures=3) | caught by: test_an_unsupported_distribution_stops_before_compose, test_an_unsupported_name_from_dotenv_is_refused, test_an_unsupported_name_from_the_environment_is_refused | sha before 351e31aef94a3a67 after 351e31aef94a3a67 | restored |
| M4 refresh rewrites when nothing changed | scripts/distros | exit 1 | Ran 33 tests in 4.024s FAILED (failures=1) | caught by: test_nothing_new_leaves_the_table_byte_identical | sha before 351e31aef94a3a67 after 351e31aef94a3a67 | restored |
| M5 Makefile stops exporting IMAGE_TAG | Makefile | exit 1 | Ran 33 tests in 3.964s FAILED (failures=4) | caught by: test_a_command_line_distribution_reaches_compose, test_a_dotenv_distribution_reaches_compose, test_an_environment_distribution_reaches_compose, test_nothing_set_gives_compose_the_default | sha before d6f6e75e813c2dcf after d6f6e75e813c2dcf | restored |

Final full checksums: `scripts/distros`
`351e31aef94a3a67d40b07f4841c419a077cadc86247efe1f3e68117282ad931`,
`Makefile` `d6f6e75e813c2dcfccaaf04e0df583b0f1a08fa19fd5772b979a9a9b20c91ac1`.

### Verification 1: Python 3.9 for real

`docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo docker.io/library/python:3.9-slim python -m unittest discover -s tests/host -v`
(`-v` added so the skips could be counted):

```
Ran 251 tests in 27.046s

OK (skipped=94)
exit 0
```

Skips there, and why:

| Count | Reason |
|---|---|
| 51 | scripts/smoke-container is bash and drives the real Makefile; this machine is missing make |
| 23 | pwsh (PowerShell 7) is not installed; set PWSH to one |
| 13 | make is not installed |
| 4 | open-url decides it is on WSL from /proc/version as well as from WSL_DISTRO_NAME, and this host's /proc/version says microsoft. The non-WSL branches cannot be reached from outside the script here; they run in CI, which is real Linux. |
| 2 | this host has /proc/meminfo, which answers first |
| 1 | needs a host with sysctl and no /proc/meminfo |

`python:3.9-slim` has no `make` and no `pwsh`, and the host-specific skips
are the same ones as on this host. 25 `test_distros` tests pass
under 3.9. The 8 `MakefileTests` skip for want of `make`.

### Verification 2: what compose actually sees

Each command ran in a fresh `bash -c`, with the four variables unset first.
`^name:` was added to the grep to show the project (Deviation 8).

```
=== ROS_DISTRO=jazzy: config --images
ghcr.io/durantschoon/ros2-classroom:jazzy
=== ROS_DISTRO=jazzy: config | grep
name: ros2-tutorials-jazzy
        ROS_BASE_DIGEST: sha256:c3706ef0a0aa45413c07803cf433602f543b22e45b4855f6fca955c2d8ecc4e8
        ROS_DISTRO: jazzy
      ROS_BASE_DIGEST: sha256:c3706ef0a0aa45413c07803cf433602f543b22e45b4855f6fca955c2d8ecc4e8
      ROS_DISTRO: jazzy
=== ROS_DISTRO=<unset>: config --images
ghcr.io/durantschoon/ros2-classroom:latest
=== ROS_DISTRO=<unset>: config | grep
name: ros2-tutorials
        ROS_BASE_DIGEST: sha256:0c19f326a339ed770ef1d4c0646a8b53bdb49dd5ff74b6de41ebdb8ac21e1806
        ROS_DISTRO: lyrical
      ROS_BASE_DIGEST: sha256:0c19f326a339ed770ef1d4c0646a8b53bdb49dd5ff74b6de41ebdb8ac21e1806
      ROS_DISTRO: lyrical
```

### Verification 3: nothing changed for the default

Stdin was `/dev/null`, there was no `.env`, and the four variables were unset.
The commands were `make help`, `make engine`, and `make -n` of `up`, `shell`,
`turtlesim`, `package PKG=x`, `build`, `run PKG=x NODE=y`, `test`. Base
captured on `4afa6cd` before any edit, then on the branch. All nine exit 0
both times. The whole diff:

```
$ diff v3-base.txt v3-final.txt
19,20c19,21
<   make doctor   Check this machine can build and run the workstation
<   make image    Build the image (slow the first time, cached after)
---
>   make doctor    Check this machine can build and run the workstation
>   make image     Build the image (slow the first time, cached after)
>   make distros   List the ROS 2 distributions; pick one with ROS_DISTRO=name
44c45
<   make digest      Print the base-image digest to pin
---
>   make digest      Refresh every distribution's base-image digest
```

The only differences are the `make distros` row, the `make digest`
description, and the realignment of the two existing "Start here" rows by one
space (Deviation 2).

### Verification 4: Windows PowerShell 5.1

`powershell.exe` is reachable. The worktree's `ros2.ps1` ran through
`\\wsl.localhost\Ubuntu\...\ros2.ps1` with `-ExecutionPolicy Bypass`. `ps`
used Docker Desktop, read-only, against project `ros2-tutorials-jazzy`.

```
5.1.26100.9549
=== .\ros2.ps1 help
Usage: .\ros2.ps1 COMMAND [NAME=value ...]    (or .\ros2.bat COMMAND ...)
Every 'make COMMAND' in the docs is '.\ros2.ps1 COMMAND' here, same arguments.

  desktop                                    Start the desktop and open it in the browser (the default)
                                             runs: docker compose up -d, then open http://127.0.0.1:6080
  up                                         Start the desktop
                                             runs: docker compose pull; docker compose up -d
  open                                       Open the desktop in the browser
                                             runs: Start-Process http://127.0.0.1:6080/vnc.html?autoconnect=1&resize=remote&reconnect=true
  shell                                      Open a ROS shell in this terminal
                                             runs: docker compose run --rm shell
  turtlesim                                  Start turtlesim on the browser desktop
                                             runs: docker compose exec -u ros desktop ros2 run turtlesim turtlesim_node
  turtlesim-teleop                           Open the arrow-key controller on the desktop
                                             runs: docker compose exec -u ros desktop turtlesim-teleop
  package PKG=name [TEMPLATE=pubsub|param]   Create a package in /workspace/src (also PYTHON=1, INTERFACES=1)
                                             runs: docker compose exec -u ros desktop pkg new name [--template pubsub]
  build [PKG=name]                           Build one package, or all of them
                                             runs: docker compose exec -u ros desktop pkg build [name]
  run PKG=name NODE=executable               Run a node from your package
                                             runs: docker compose exec -u ros desktop pkg run name executable
  test [PKG=name]                            Test one package, or all of them
                                             runs: docker compose exec -u ros desktop pkg test [name]
  logs                                       Follow the desktop's logs (Ctrl-C to stop)
                                             runs: docker compose logs -f
  ps                                         List the workstation's containers
                                             runs: docker compose ps
  down                                       Stop the containers (your work is kept)
                                             runs: docker compose down
  reset                                      Delete your workspace and settings (asks first)
                                             runs: docker compose down -v --remove-orphans
  uninstall                                  Delete all of that and the images (asks first)
                                             runs: docker rm / volume rm / network rm / image rm
  doctor                                     Check this machine can run the workstation
                                             runs: docker info; docker compose version
  image                                      Build the image locally instead of pulling it
                                             runs: docker compose build
  distros                                    List the ROS 2 distributions; pick one with ROS_DISTRO=name
  engine                                     Show which compose command is used
                                             runs: docker compose version
  help                                       Show this help
  COMMAND help | COMMAND examples            More on shell, package, build, run, test

Example:
  .\ros2.ps1 package PKG=my_robot TEMPLATE=pubsub
  .\ros2.ps1 build PKG=my_robot
  .\ros2.ps1 run PKG=my_robot NODE=talker

Desktop: http://127.0.0.1:6080
Distribution: lyrical (compose project ros2-tutorials); others: .\ros2.ps1 distros
--- exit 0
=== .\ros2.ps1 distros
DISTRO   UBUNTU  IMAGE TAG  COMPOSE PROJECT
humble   22.04   humble     ros2-tutorials-humble
jazzy    24.04   jazzy      ros2-tutorials-jazzy
kilted   24.04   kilted     ros2-tutorials-kilted
lyrical  26.04   latest     ros2-tutorials         (default)

Choose one with ROS_DISTRO=<name>, e.g.  .\ros2.ps1 up ROS_DISTRO=jazzy
--- exit 0
=== .\ros2.ps1 ps ROS_DISTRO=jazzy
docker compose ps
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
--- exit 0
```

In addition, a temporary copy of `ros2.ps1` and `distros.json`, with a `.env`
of `# comment`, blank, `ROS_DISTRO="kilted"`, was run under 5.1 to exercise
the `.env` path (`-split '=', 2`, `Contains([string]"=")`). The help's rows
are filtered out here:

```
5.1.26100.9549
=== .\ros2.ps1 help
Usage: .\ros2.ps1 COMMAND [NAME=value ...]    (or .\ros2.bat COMMAND ...)
Every 'make COMMAND' in the docs is '.\ros2.ps1 COMMAND' here, same arguments.


Example:

Desktop: http://127.0.0.1:6080
Distribution: kilted (compose project ros2-tutorials-kilted); others: .\ros2.ps1 distros
--- exit 0
=== .\ros2.ps1 ps
docker compose ps
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
--- exit 0
```

### Verification 5: the real suite

`make selftest`, default distribution, default isolation (project
`ros2-tutorials-selftest`, port 6081). It was run twice, once before and once
after the last code change. Both gave 48/48. The second:

```
./scripts/smoke-container
using: docker compose -p ros2-tutorials-selftest  (isolated project; host port 6081)
...
  PASS workspace source survives container recreation
  PASS built overlay survives container recreation

== Result
48 passed, 0 failed

== cleaning up

real	3m1.174s
user	0m4.544s
sys	0m3.437s
exit 0
```

`git status` afterwards showed only this stage's own changes: 11 modified and
3 new files, nothing else. The user's `ros2-tutorials` project was not
touched.

## 5. Every message `scripts/distros` can print

Captured from a scratch copy (`<tree>`), with stdout and stderr merged:

```
$ <tree>/scripts/distros env
export ROS_DISTRO=lyrical
export ROS_BASE_DIGEST=sha256:0c19f326a339ed770ef1d4c0646a8b53bdb49dd5ff74b6de41ebdb8ac21e1806
export IMAGE_TAG=latest
export COMPOSE_PROJECT_NAME=ros2-tutorials
[exit 0]
$ <tree>/scripts/distros env --make
ROS_DISTRO=lyrical
ROS_BASE_DIGEST=sha256:0c19f326a339ed770ef1d4c0646a8b53bdb49dd5ff74b6de41ebdb8ac21e1806
IMAGE_TAG=latest
COMPOSE_PROJECT_NAME=ros2-tutorials
[exit 0]
$ <tree>/scripts/distros list
DISTRO   UBUNTU  IMAGE TAG  COMPOSE PROJECT
humble   22.04   humble     ros2-tutorials-humble
jazzy    24.04   jazzy      ros2-tutorials-jazzy
kilted   24.04   kilted     ros2-tutorials-kilted
lyrical  26.04   latest     ros2-tutorials         (default)
[exit 0]
$ <tree>/scripts/distros
usage: distros env [--make] | distros list | distros refresh
[exit 2]
$ <tree>/scripts/distros --help
usage: distros env [--make] | distros list | distros refresh
[exit 0]
$ env ROS_DISTRO=foxy <tree>/scripts/distros env
ROS_DISTRO=foxy is not supported. Choose one of: humble jazzy kilted lyrical
[exit 2]
$ <tree>/scripts/distros refresh
humble: base-image-digest answered 'nonsense', not a sha256 digest
humble   kept sha256:1813d3c85d7f96ff7d3012d865204583255740182db5d0065f8f8cd029a83138 (could not fetch)
jazzy    sha256:c3706ef0a0aa45413c07803cf433602f543b22e45b4855f6fca955c2d8ecc4e8 -> sha256:abababababababababababababababababababababababababababababababab
no digest for ros:kilted-ros-base
kilted   kept sha256:8e7b828a8f24416dd29fde258d81ad49c87fb9becc1289cf69c9d28d36fa78f9 (could not fetch)
lyrical  unchanged

Updated <tree>/distros.json. Rebuild each changed distribution:
  make image ROS_DISTRO=jazzy
Some digests could not be fetched; those entries were kept.
[exit 1]
$ <tree>/scripts/distros refresh
could not run <tree>/scripts/base-image-digest: [Errno 2] No such file or directory: '<tree>/scripts/base-image-digest'
humble   kept sha256:1813d3c85d7f96ff7d3012d865204583255740182db5d0065f8f8cd029a83138 (could not fetch)
could not run <tree>/scripts/base-image-digest: [Errno 2] No such file or directory: '<tree>/scripts/base-image-digest'
jazzy    kept sha256:abababababababababababababababababababababababababababababababab (could not fetch)
could not run <tree>/scripts/base-image-digest: [Errno 2] No such file or directory: '<tree>/scripts/base-image-digest'
kilted   kept sha256:8e7b828a8f24416dd29fde258d81ad49c87fb9becc1289cf69c9d28d36fa78f9 (could not fetch)
could not run <tree>/scripts/base-image-digest: [Errno 2] No such file or directory: '<tree>/scripts/base-image-digest'
lyrical  kept sha256:0c19f326a339ed770ef1d4c0646a8b53bdb49dd5ff74b6de41ebdb8ac21e1806 (could not fetch)
Some digests could not be fetched; those entries were kept.
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: not valid JSON (Expecting property name enclosed in double quotes: line 1 column 3 (char 2))
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: expected a JSON object at the top level
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: "_comment" must be a list of strings
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: missing "distros", an object of distribution names
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: 'Bad Name' is not a distribution name
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: "x" must be an object with "ubuntu" and "digest"
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: "x" has no "ubuntu" version
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: "x" has no "digest" of the form sha256:<64 hex digits>
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: missing "default", the name of the default distribution
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: the default, "y", is not in "distros"
[exit 1]
$ <tree>/scripts/distros env
<tree>/distros.json: cannot read it ([Errno 2] No such file or directory: '<tree>/distros.json')
[exit 1]
```

Usage errors (exit 2) and the unsupported-name error (exit 2) go to stderr.
Every table problem is one stderr line `<path>: <problem>` with exit 1. The
refresh lines go to stdout. `could not run ...`, `...: base-image-digest
answered ...` and `Some digests could not be fetched; those entries were
kept.` go to stderr. `base-image-digest`'s own errors pass through on its
stderr.

## 6. Stat, excluding this report

`git diff multi-distro --stat -- . ':!docs/stages/stage-11-REPORT.md'`, with the
new files staged:

```
 .env.example                        |  10 +-
 .github/workflows/docker-image.yml  |   2 +-
 Dockerfile                          |   5 +-
 Makefile                            |  42 ++--
 README.md                           |  12 +-
 compose.yaml                        |   3 +-
 distros.json                        |  18 ++
 ros2.ps1                            |  97 +++++++-
 scripts/distros                     | 427 ++++++++++++++++++++++++++++++++++++
 scripts/workstation-help            |   4 +-
 tests/host/fakes.py                 |   6 +-
 tests/host/test_distros.py          | 406 ++++++++++++++++++++++++++++++++++
 tests/host/test_ros2_ps1.py         | 116 ++++++++++
 tests/host/test_workstation_help.py |  13 ++
 14 files changed, 1131 insertions(+), 30 deletions(-)
```

## 7. Deviations

1. **The first pwsh baseline run was invalid, and the fault was mine.** I
   created `distros.json` and `scripts/distros` while
   `PWSH=... make check` was running on the base. Then
   `test_smoke_container.Housekeeping.test_the_repository_is_left_untouched_by_a_run`
   failed with `AssertionError: '' != '?? distros.json\n'`. I moved both files
   out of the tree, reran on the clean base (OK, skipped=7, the output above),
   and restored them. The non-pwsh baseline ran before any file existed.
2. **Verification 3** shows one difference the prompt did not list. The two
   existing "Start here" rows (`make doctor`, `make image`) are realigned by
   one space, because the group's column width follows its longest command,
   now `make distros`. It is whitespace only, and a direct result of the
   permitted row.
3. **README**: besides the Configuration paragraph, I updated the "Commands"
   table. Its `make digest` row said "Print the base-image digest to pin in
   `.env`", which is no longer true, so it now describes the refresh, and a
   `make distros` row was added. Same allowed file. The "What is in the
   image" paragraph still names only Lyrical; that is left for stage 13.
4. **Formats the prompt left open**:
   - A refresh line is `<name padded>  <outcome>`.
   - After a rewrite, refresh prints `Updated <path>. Rebuild each changed
     distribution:` and then `  make image ROS_DISTRO=<name>` per changed name.
   - The `list` header is `DISTRO  UBUNTU  IMAGE TAG  COMPOSE PROJECT`.
   - The first `reset` line is `This removes the <project> containers
     (<distro>) and these volumes:`. For the default that changes the text to
     `... ros2-tutorials containers (lyrical) ...`, as section 3 of the prompt
     requires.
   - The last line of `ros2.ps1 help` is `Distribution: <d> (compose project
     <p>); others: .\ros2.ps1 distros`, after the existing `Desktop:` line.
5. **Additions beyond the prompt, in `scripts/distros`**:
   - `-h`/`--help` prints the usage line and exits 0.
   - Table parsing also rejects a digest not shaped `sha256:<64 hex>`, a name
     not shaped `[a-z][a-z0-9_-]*`, a non-list `_comment`, and a non-object top
     level.
   - A sibling answer that is not a digest is reported and treated as "could
     not fetch" (guardrail 6: never guess).
   - A missing table and an unreadable `.env` each give one line and exit 1. A
     missing `.env` is not an error.
   - The table is rewritten atomically (temp file plus `os.replace`), keeping
     its file mode.
6. **A code change after the first full round of gates.** Capturing section 5
   showed that the final stderr summary could land before buffered stdout
   lines when piped. `complain()` now flushes stdout first. After that change
   I reran the five mutations, `make check` (both ways), `make lint`,
   Verification 1 and `make selftest`. Verifications 2-4 do not exercise that
   path and were not rerun.
7. **Makefile `$(error)` path.** On failure it reruns the resolver with all
   four inputs, capturing stderr only (`2>&1 >/dev/null`). The spike passed
   only `ROS_DISTRO` there. Behaviour is the same for the unsupported-name
   case.
8. **Verification 2** greps `^name:` as well, to show the project compose
   resolves. Verification 1 used `-v` to count skips.
9. **`ros2.ps1` choices**:
   - Its errors use `Write-Host` in red (stdout), the file's existing
     convention, not stderr.
   - Its malformed-table check is coarser than the script's. It reports a JSON
     read failure, or `no "distros", or the default is not among them`, and it
     does not validate digest shape.
   - The table is read on every command, including `help`, as make does.
10. **`ros2.ps1` tests**: all eight new tests run a temporary copy of
    `ros2.ps1` and `distros.json`, not only the `.env` one. That way a
    developer's own `.env` in the checkout cannot change their outcome. The
    imports were extended with two *added* lines (`import json`,
    `from typing import Dict`) rather than by editing `from typing import List`,
    to keep that file's diff additions-only.
11. **The Makefile tests** link the real `echo` into the sandbox, because make
    runs a simple recipe line like `echo ...` without a shell. They also
    replace `scripts/compose-command` in the temporary tree with a two-line
    stub, and copy the real `scripts/run-quiet`.
12. **Line endings.** My edit rewrote the working copy of `ros2.ps1` with LF,
    which `.gitattributes` pins to CRLF. I converted the working copy back to
    CRLF. Git normalises the blob either way (`i/lf w/crlf`), so the
    committed content is unaffected.
13. `make selftest` ran twice rather than once (Deviation 6).

## 8. Open questions

1. **`compose-up` still inspects `:latest`** for a non-default distribution
   (`scripts/compose-up` has `IMAGE_TAG = "latest"`), and so does
   `smoke-container`'s `image_reference`. That is stage 12.
2. **Uninstall already partly follows the distribution, without code
   changes.** Make now exports `COMPOSE_PROJECT_NAME`, and `ros2.ps1` sets it
   before `$Projects` is computed. So `make uninstall ROS_DISTRO=jazzy` and
   `.\ros2.ps1 uninstall ROS_DISTRO=jazzy` target project
   `ros2-tutorials-jazzy`, but still look for image `:latest`. The default is
   unchanged. Stage 12 should make this deliberate.
3. **A stale `ROS_BASE_DIGEST` in a student's `.env`** (the old
   `.env.example` had one) is now overridden. Make and `ros2.ps1` export the
   table's digest, and the environment beats `.env` in compose. Today the
   values are identical for lyrical. After a `make digest` refresh the table
   silently wins, which is probably right, but it is a change for anyone who
   pinned on purpose.
4. **Plain `docker compose` with `ROS_DISTRO=jazzy` in `.env` and no `eval`**
   still pairs jazzy with lyrical's digest and tag `latest`: the hazard from
   the Motivation. It is documented in `.env.example`, but nothing prevents
   it.
5. **Inline comments in `.env`** (`ROS_DISTRO=jazzy  # mine`) are not
   stripped, following the prompt's rules. Compose strips them for unquoted
   values. Here the result is a loud "not supported" error, never a silent
   wrong choice.
6. **An unsupported `ROS_DISTRO` in `.env` stops every target**, including
   `make help` and `make distros`. The error lists the valid names, but the
   student cannot use `make distros` to recover until they edit `.env`.
7. **make 3.81 (macOS)** was not tested. The resolver uses only `$(shell)`,
   `$(eval)`, `$(foreach)` and `$(error)` (no `.SHELLSTATUS`), which 3.81 has.
8. **`make digest` no longer uses `docker buildx imagetools`** when Docker is
   present. It always goes through `base-image-digest` (curl), as specified.
9. **`make check` wall time.** Each `make` parse now starts one extra
   `python3`, and `test_smoke_container` parses the real Makefile many times.
   That adds a few seconds, against a README that quotes ~53 s.
10. **The `ros2.ps1` table check does not validate digests**, so the two
    implementations can disagree on a hand-edited, malformed table. A shared
    fixture test of malformed tables across both would pin that down.
