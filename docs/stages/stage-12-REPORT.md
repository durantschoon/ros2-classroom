# Stage 12 report: every script knows every distribution, each on its own port and prompt

Branch `stage-12-every-script-every-distro`, base `multi-distro`.

## 1. First step

```
$ git log --oneline -1
3e33359 docs(stages): stage 12 prompt -- every script knows every distribution, each on its own port and prompt
```

`docs/stages/stage-12-PROMPT.md` was present, so there was no fetch or merge.
The worktree branch was renamed with `git branch -m stage-12-every-script-every-distro`.

## 2. Checklist

### The change

- [x] 1. `distros.json`: each entry has `"port"`. lyrical is 6080, humble 6082,
  jazzy 6083, kilted 6084. Three `_comment` lines say so. `scripts/distros`:
  - `parse_table` refuses a port that is not an integer from 1024 to 65535
    (a string, a float, a bool, or no port at all).
  - It refuses 6081, and it refuses two distributions that share a port.
    These are one-line `<path>: <problem>` messages with exit 1, the stage 11
    shape.
  - `env` prints `NOVNC_PORT` as the fifth line. An explicit non-empty value
    in the environment wins.
  - `list` has a `PORT` column between `UBUNTU` and `IMAGE TAG`.
  - `refresh` writes the port back unchanged. `render_table(parse_table(file)) == file`
    still holds.
  - `-h`/`--help` is kept and now tested.
- [x] 2. `Makefile`: `NOVNC_PORT ?= 6080` is gone. `NOVNC_PORT` is handed to
  the resolver explicitly, like the other four, and exported. `URL` and
  `DESKTOP_URL` are defined after the resolution. `make -n open ROS_DISTRO=jazzy`
  names `http://localhost:6083/...`.
- [x] 3. `ros2.ps1`:
  - `NOVNC_PORT` comes from the table unless set, it is exported to docker,
    and `$Url` is computed after the resolution. `distros` shows the port.
  - The table check is now as strict as `scripts/distros` and prints the
    same messages, in the same order of checks, with an ordinal sort (section
    4, test 9).
  - `uninstall` looks, for every distribution, for:
    - its project's containers, volumes and network, plus the self-test's
    - its image tag
    - the legacy `ros2-tutorials:<name>`
    - its base `docker.io/library/ros@<digest>`
  - The listing format, the confirmation and the removal order are unchanged.
  - ASCII and CRLF are kept.
- [x] 4. `scripts/compose-up`:
  - It inspects `${IMAGE_NAME:-default}:${IMAGE_TAG:-latest}`.
  - `port_to_suggest` skips 6081 and every port in `../distros.json`.
  - A table it cannot read or parse means "skip 6081 only".
- [x] 5. `scripts/uninstall`:
  - The survey covers every distribution in `../distros.json` (Deviation 3).
  - With a table it cannot read or use, it falls back to the old survey: the
    environment's project and image, and the Dockerfile's base.
  - The removal order, the confirmation word and `YES=1` are unchanged.
  - The docstring says it covers every distribution.
- [x] 6. `scripts/smoke-container`: `image_reference(name, tag)` builds
  `${IMAGE_NAME:-default}:${IMAGE_TAG:-latest}`. Nothing else changed: the
  self-test still uses its own project and 6081 (tested).
- [x] 7. `docker/bashrc.d/ros-workspace.sh`:
  - Interactive shells with `ROS_DISTRO` and `PS1` set get the prefix
    `(<distro>) `, the default distribution included. It is never added
    twice, and non-interactive shells are untouched.
  - The prefix is also re-applied through `PROMPT_COMMAND` (Deviation 1).
  - `make()`'s target list gains `distros` and `uninstall`.

### Definition of Done

- [x] Baseline and final `make lint`, `make check`, and `PWSH=... make check`
  (section 3).
- [x] Tests 1-11 and the five mutations (section 4). Verifications 1-4 are in
  section 5.
- [x] `git diff multi-distro --stat` shows only allowed files (section 6).

## 3. Gates, verbatim

Every gate ran from the worktree with `export PATH="$HOME/.local/bin:$PATH"`,
under `time`. `$SCRATCH` is this session's scratchpad. `PWSH=$SCRATCH/pwsh/pwsh`
is PowerShell 7.

### Baseline (unmodified `3e33359`)

`make lint`:
```
docker compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: docker run --rm -v <worktree>:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
[34 "ok" lines omitted]
lint-scripts: 34 files: 34 ok, 0 advisory, 0 FAIL
make lint  0.48s user 0.36s system 26% cpu 3.139 total
exit 0
```

`make check`:
```
Ran 251 tests in 80.868s

OK (skipped=30)
make check  63.52s user 19.20s system 99% cpu 1:23.34 total
exit 0
```

`PWSH=... make check` (a clean rerun, see Deviation 7):
```
Ran 251 tests in 121.210s

OK (skipped=7)
make check  99.80s user 28.89s system 103% cpu 2:04.47 total
exit 0
```

### Final

`make lint` (`docker/bashrc.d/ros-workspace.sh` passes shellcheck, enforced):
```
compose config: ok
lint-scripts: 34 files: 34 ok, 0 advisory, 0 FAIL
make lint  0.59s user 0.43s system 32% cpu 3.099 total
exit 0
```

`make check`:
```
Ran 288 tests in 92.004s

OK (skipped=36)
make check  72.46s user 21.77s system 98% cpu 1:35.47 total
exit 0
```

`PWSH=... make check`:
```
Ran 288 tests in 150.637s

OK (skipped=7)
make check  127.98s user 35.15s system 105% cpu 2:34.83 total
exit 0
```

There are 37 new tests (251 to 288). Without pwsh, 6 more tests skip (30 to
36): the six new `ros2.ps1` classes. The run took about 11 s longer than the
baseline without pwsh, and about 30 s longer with pwsh. The pwsh cost is the
13-case shared-table test (26 interpreter starts) and the uninstall and port
tests.

## 4. Tests and mutations

| # | Test(s) |
|---|---|
| 1 | `test_distros.PortTableTests`: `test_a_port_that_is_not_an_integer_is_refused` (string, fraction, float `6083.0`, `true`, no port), `test_a_port_out_of_range_is_refused` (80, 70000), `test_two_distributions_sharing_a_port_are_refused`, `test_the_self_tests_port_is_refused` |
| 2 | `PortTableTests.test_env_ends_with_each_distributions_port` (five lines, `NOVNC_PORT` last, per distribution), `test_an_explicit_port_wins_and_an_empty_one_does_not`, `test_list_shows_each_port`, `test_refresh_keeps_every_port`, and the edited `ListTests.test_list_shows_a_header_and_a_row_per_distribution` |
| 3 | `test_distros.MakefileTests`: `test_a_distribution_gives_compose_its_own_port` (`make ps ROS_DISTRO=jazzy` gives the fake 6083), `test_the_default_gives_compose_the_old_port`, `test_an_explicit_port_wins_over_the_table`, `test_open_names_the_distributions_port` (`make -n open`: jazzy 6083, default 6080, kilted 6084; no other port) |
| 4 | `test_compose_up.DistributionTests.test_the_distributions_own_image_is_inspected` (`IMAGE_TAG=jazzy`), `test_without_a_tag_latest_is_inspected`, `test_a_stale_distribution_image_is_recreated` |
| 5 | `DistributionTests.test_a_busy_distribution_port_skips_the_others_and_the_selftests` (from 6082 and from 6080, 6085 is suggested and 6081/6083/6084 never are), `test_an_unreadable_table_skips_only_the_selftests_port` (no table, then a table that is not JSON: 6082) |
| 6 | `test_uninstall.EveryDistributionTests.test_the_plan_lists_every_distributions_objects_with_sizes`, `test_everything_is_removed_in_order_one_call_per_kind` (nothing set, and make's jazzy environment: same removals, each object once), `test_an_unreadable_table_looks_only_where_it_did_before_the_table` (a copy with only the Dockerfile beside it, then with a table that is not JSON: today's removals, and no jazzy object is asked about) |
| 7 | `test_smoke_container.DistributionImage.test_the_image_user_check_inspects_the_distributions_image` (`IMAGE_TAG=kilted` inspects only `…:kilted`), `test_the_suite_keeps_its_own_project_and_port` (make's kilted exports set: still `-p ros2-tutorials-selftest`, `NOVNC_PORT=6081`, torn down) |
| 8 | `test_ros2_ps1.PortTests`: `test_each_distribution_hands_docker_its_own_port`, `test_an_explicit_port_wins`, `test_open_uses_the_distributions_port`. `EveryDistributionUninstallTests`: `test_uninstall_lists_every_distributions_objects`, `test_uninstall_removes_them_in_order_one_call_per_kind`. The edited `DistroTests.test_distros_prints_the_table_and_the_hint` covers `distros` |
| 9 | `tests/host/fakes.py: malformed_tables()` holds 13 cases: the port cases above, plus a bad digest, a bad name, no default, and a default not in the table. `test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike` runs each through `scripts/distros env` and `ros2.ps1 distros`: both exit 1, with identical `<path>: <problem>` lines, and docker is never called. `test_distros.PortTableTests.test_every_malformed_table_is_refused` runs the fixture through the script alone when there is no pwsh |
| 10 | `test_distros.HelpFlagTests.test_h_and_help_print_the_usage_and_succeed` |
| 11 | `test_distros.PromptTests` (skips without bash): `test_an_interactive_prompt_starts_with_the_distribution`, `test_the_default_distribution_is_named_too`, `test_sourced_twice_the_name_appears_once`, `test_sourced_again_past_its_guard_the_name_still_appears_once`, `test_without_a_distribution_the_prompt_is_left_alone`, `test_a_non_interactive_shell_is_untouched`, `test_the_name_comes_back_when_bashrc_sets_the_prompt_again` |

### Single-distribution test edits (the ground rules allow these)

1. `test_distros.DistrosTreeCase.assertSettings` expected exactly the four
   settings. It now expects five and fills in the distribution's port unless
   the case names one.
2. `test_distros.EnvTests.test_make_form_is_four_bare_assignments` pinned four
   lines. `NOVNC_PORT=6083` is appended to the expectation. The name is kept.
3. `test_distros.ListTests.test_list_shows_a_header_and_a_row_per_distribution`
   gains the `PORT` column.
4. `test_distros.MakefileTests.test_make_distros_lists_them_with_the_hint`
   gains the `PORT` column in the header.
5. `test_ros2_ps1.DistroTests.test_distros_prints_the_table_and_the_hint`
   gains the `PORT` column.
6. `test_compose_up.ComposeUpTests.test_a_failed_up_names_the_port_and_a_free_one_to_try`
   expected 6082 from 6080. That is now humble's port, so it expects 6085,
   and its comment says why.

Every other change to a test file is an addition: new classes, new methods in
`MakefileTests`, and imports added as new lines.

### Mutations

A script applied each mutation, ran the named module, restored the file by
copy-back, and compared SHA-256 (first 16 hex digits shown). It ran after the
last code change.

| Mutation | File | Suite | Caught by | Checksum | Restore |
|---|---|---|---|---|---|
| M1 allow a shared port | scripts/distros | exit 1: Ran 54 tests in 7.347s FAILED (failures=2) | test_every_malformed_table_is_refused, test_two_distributions_sharing_a_port_are_refused | 99f4416aa570693f / 99f4416aa570693f | restored |
| M2 Makefile stops exporting NOVNC_PORT (`filter-out NOVNC_PORT=%` in the export loop) | Makefile | exit 1: Ran 54 tests in 7.515s FAILED (failures=3, errors=2) | test_a_distribution_gives_compose_its_own_port, test_open_names_the_distributions_port, test_the_default_gives_compose_the_old_port | 09ef99e1ea007e66 / 09ef99e1ea007e66 | restored |
| M3 port_to_suggest forgets the table | scripts/compose-up | exit 1: Ran 31 tests in 6.337s FAILED (failures=3) | test_a_busy_distribution_port_skips_the_others_and_the_selftests, test_a_failed_up_names_the_port_and_a_free_one_to_try | cb6105b5d4dcbf3e / cb6105b5d4dcbf3e | restored |
| M4 uninstall surveys only the current distribution (table ignored) | scripts/uninstall | exit 1: Ran 16 tests in 8.332s FAILED (failures=3) | test_everything_is_removed_in_order_one_call_per_kind, test_the_plan_lists_every_distributions_objects_with_sizes | f0ef98fb5e62fcad / f0ef98fb5e62fcad | restored |
| M5 prompt prefix applied twice (the "already there" check never matches) | docker/bashrc.d/ros-workspace.sh | exit 1: Ran 54 tests in 6.859s FAILED (failures=1) | test_sourced_again_past_its_guard_the_name_still_appears_once | 97a38086bb25b66f / 97a38086bb25b66f | restored |

## 5. Verification

### 1. Python 3.9 for real

`docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v <worktree>:/repo:ro -w /repo docker.io/library/python:3.9-slim python -m unittest discover -s tests/host`:

```
Ran 288 tests in 46.992s

OK (skipped=106)
```

The image has no make and no pwsh, so the skips are stage 11's 94 plus this
stage's new make, pwsh and smoke-suite tests. It has bash, so `PromptTests`
ran there.

### 2. Two desktops at once, for real

Both desktops used throwaway projects and ports, and `IMAGE_NAME=ros2-tutorials-st12`
(Deviation 2). The images were those built by the self-tests below. The
driver was a Python script. This is its output, with compose's progress lines
trimmed:

```
$ make up COMPOSE_PROJECT_NAME=st12-a NOVNC_PORT=6085 IMAGE_NAME=ros2-tutorials-st12
+ docker compose up -d
 Container st12-a-desktop-1 Started
The desktop is starting. Next:  make open
[exit 0]
$ make up COMPOSE_PROJECT_NAME=st12-b NOVNC_PORT=6086 IMAGE_NAME=ros2-tutorials-st12 ROS_DISTRO=jazzy
+ docker compose up -d
 Container st12-b-desktop-1 Started
The desktop is starting. Next:  make open
[exit 0]
$ curl -sS -o /dev/null -w '%{http_code} 6085\n' http://127.0.0.1:6085/vnc.html
200 6085
$ curl -sS -o /dev/null -w '%{http_code} 6086\n' http://127.0.0.1:6086/vnc.html
200 6086
$ make turtlesim COMPOSE_PROJECT_NAME=st12-a NOVNC_PORT=6085 IMAGE_NAME=ros2-tutorials-st12
./scripts/run-quiet docker compose exec -T -u ros -e DISPLAY=:1 desktop bash -lc 'nohup ros2 run turtlesim turtlesim_node >/tmp/turtlesim.log 2>&1 &'
turtlesim started on the browser desktop (http://localhost:6085).
[exit 0]
$ make turtlesim COMPOSE_PROJECT_NAME=st12-b NOVNC_PORT=6086 IMAGE_NAME=ros2-tutorials-st12 ROS_DISTRO=jazzy
turtlesim started on the browser desktop (http://localhost:6086).
[exit 0]
$ docker compose exec -T -u ros desktop bash -lc 'echo "ROS_DISTRO=$ROS_DISTRO"; ros2 node list'   # st12-a
ROS_DISTRO=lyrical
/turtlesim
$ docker compose exec -T -u ros -w /workspace desktop bash -i  <<< exit                         # st12-a
(lyrical) ros@995ce358e56d:/workspace$ exit
$ docker compose exec -T -u ros desktop bash -lc 'echo "ROS_DISTRO=$ROS_DISTRO"; ros2 node list'   # st12-b
ROS_DISTRO=jazzy
/turtlesim
$ docker compose exec -T -u ros -w /workspace desktop bash -i  <<< exit                         # st12-b
(jazzy) ros@14ff3ad8a054:/workspace$ exit
$ docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}'
st12-b-desktop-1	ros2-tutorials-st12:jazzy	127.0.0.1:6086->6080/tcp
st12-a-desktop-1	ros2-tutorials-st12:latest	127.0.0.1:6085->6080/tcp
ros2-tutorials-shell-run-acf2547fc964	f23041cc97de	6080/tcp
ros2-tutorials-desktop-1	f23041cc97de	127.0.0.1:6080->6080/tcp
```

The first `curl` of the wait loop got `(56) Connection reset` while noVNC was
still starting. The loop retried. The direct `docker compose exec` calls ran
with the environment make hands compose (the resolver's five settings plus
the project, port and image name). The `bash -i` lines show the prompt a
student actually sees, after `/home/ros/.bashrc` has reset `PS1`.

Down, with the same variables:
```
$ make down COMPOSE_PROJECT_NAME=st12-a NOVNC_PORT=6085 IMAGE_NAME=ros2-tutorials-st12
 Container st12-a-desktop-1 Removed
 Network st12-a_ros Removed
$ make down COMPOSE_PROJECT_NAME=st12-b NOVNC_PORT=6086 IMAGE_NAME=ros2-tutorials-st12 ROS_DISTRO=jazzy
 Container st12-b-desktop-1 Removed
 Network st12-b_ros Removed
$ docker ps -a --filter name=st12- --format '{{.Names}}'
$ docker volume ls --filter name=st12- --format '{{.Name}}'
st12-a_ros-home
st12-a_ros-workspace
st12-b_ros-home
st12-b_ros-workspace
$ make reset YES=1 COMPOSE_PROJECT_NAME=st12-a NOVNC_PORT=6085 IMAGE_NAME=ros2-tutorials-st12
This removes the st12-a containers (lyrical) and these volumes: ...
$ make reset YES=1 COMPOSE_PROJECT_NAME=st12-b NOVNC_PORT=6086 IMAGE_NAME=ros2-tutorials-st12 ROS_DISTRO=jazzy
This removes the st12-b containers (jazzy) and these volumes: ...
$ docker ps -a --filter name=st12- --format '{{.Names}}'
$ docker volume ls --filter name=st12- --format '{{.Name}}'
$ docker network ls --filter name=st12- --format '{{.Name}}'
$ docker ps --filter name=ros2-tutorials-desktop-1 --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
ros2-tutorials-desktop-1	Up 22 hours (healthy)	127.0.0.1:6080->6080/tcp
```

`make down` keeps volumes, so `make reset YES=1` removed them (Deviation 4).
The user's `ros2-tutorials` desktop kept running throughout, untouched.
Afterwards I removed the throwaway images `ros2-tutorials-st12:latest` and
`:jazzy`.

### 3. Nothing changed for the default

`make help`, `make -n up` and `make -n open` ran with no `.env`, stdin
`/dev/null`, and the five variables unset. They ran in a `git archive` export
of `3e33359` and in the branch. Every command exited 0 in both.

```
lines: 94 94
diff: (none)
```

### 4. The self-test, default and jazzy

Both ran with `IMAGE_NAME=ros2-tutorials-st12` (Deviation 2). The project and
port were the self-test's own defaults, `ros2-tutorials-selftest` and 6081.

`make selftest IMAGE_NAME=ros2-tutorials-st12`:
```
using: docker compose -p ros2-tutorials-selftest  (isolated project; host port 6081)
...
== Result
48 passed, 0 failed

== cleaning up
make selftest IMAGE_NAME=ros2-tutorials-st12  4.76s user 3.97s system 4% cpu 3:01.12 total
exit 0
```

`make selftest ROS_DISTRO=jazzy IMAGE_NAME=ros2-tutorials-st12` (the jazzy
result, verbatim apart from the stripped colour codes and elided passes):
```
using: docker compose -p ros2-tutorials-selftest  (isolated project; host port 6081)
  PASS image builds
  PASS desktop container accepts commands
  PASS the image defaults to the non-root ros user
  ...
  PASS noVNC answers on the host at http://localhost:6081

== Cross-service DDS discovery
 Container ros2-tutorials-selftest-talker-1 Creating
 Container ros2-tutorials-selftest-talker-1 Created
 Container ros2-tutorials-selftest-talker-1 Starting
 Container ros2-tutorials-selftest-talker-1 Started
  FAIL no message crossed between compose services
  ...
  PASS workspace source survives container recreation
  PASS built overlay survives container recreation
47 passed, 1 failed
make selftest ROS_DISTRO=jazzy IMAGE_NAME=ros2-tutorials-st12  4.31s user 3.80s system 4% cpu 3:02.93 total
exit 2
```

Jazzy fails one check: "no message crossed between compose services". It is
reported, not fixed; stage 13 owns per-distribution fixes. The image-user
check passed against `ros2-tutorials-st12:jazzy`, the distribution's own
image.

### Extra, read-only: Windows PowerShell 5.1

`powershell.exe` ran the worktree's `ros2.ps1` (`-ExecutionPolicy Bypass`):

- `distros` printed the table with the `PORT` column, exit 0.
- `help ROS_DISTRO=jazzy` shows `Start-Process http://127.0.0.1:6083/vnc.html?...`
  and `Desktop: http://127.0.0.1:6083`.
- The 13 malformed tables were run through a temporary copy and through
  `scripts/distros`. The result was `agree on 13/13`: both exit 1, with
  identical problem text.

## 6. Stat, excluding this report

`git diff multi-distro --stat` before staging the report:

```
 Makefile                           |  16 +--
 distros.json                       |  12 ++-
 docker/bashrc.d/ros-workspace.sh   |  27 ++++-
 ros2.ps1                           | 138 +++++++++++++++++-------
 scripts/compose-up                 |  63 ++++++++---
 scripts/distros                    |  64 +++++++++---
 scripts/smoke-container            |  10 +-
 scripts/uninstall                  | 183 +++++++++++++++++++++++++++-----
 tests/host/fakes.py                |  67 ++++++++++++
 tests/host/test_compose_up.py      |  84 ++++++++++++++-
 tests/host/test_distros.py         | 209 +++++++++++++++++++++++++++++++++++--
 tests/host/test_ros2_ps1.py        | 151 ++++++++++++++++++++++++++-
 tests/host/test_smoke_container.py |  28 +++++
 tests/host/test_uninstall.py       | 114 ++++++++++++++++++++
 14 files changed, 1046 insertions(+), 120 deletions(-)
```

## 7. Deviations

1. **The prompt prefix is also re-applied before each prompt.** In the image,
   `/etc/bash.bashrc` sources the file, and then `/home/ros/.bashrc` (from
   `/etc/skel`, checked in `ros:jazzy-ros-base`) sets `PS1` again. A prefix
   set only when the file is sourced would never be seen. The file therefore
   also adds a `_ros_distro_prompt` hook to `PROMPT_COMMAND`, once. The hook
   adds the prefix only when `PS1` does not already start with it.
   Non-interactive shells get neither the prefix nor the hook (tested).
   Verification 2 shows the result in real containers:
   `(jazzy) ros@…:/workspace$`.
2. **`IMAGE_NAME=ros2-tutorials-st12` for Verifications 2 and 4.** Plain
   `make selftest` rebuilds `ghcr.io/durantschoon/ros2-classroom:latest`,
   which is the tag the user's running workstation uses. Retagging it would
   make their next `make up` recreate their desktop from this branch's image.
   The README's isolation recipe allows `IMAGE_NAME`, and it also means
   Verification 2 ran this branch's bashrc. The project and port were the
   self-test's defaults.
3. **Uninstall also keeps explicit settings from the environment.** Besides
   every table distribution, `scripts/uninstall` still looks for an explicit
   `COMPOSE_PROJECT_NAME`, `IMAGE_TAG`, `ROS_DISTRO` (legacy tag) and
   `ROS_BASE_DIGEST` from the environment when they are not already on the
   list. Without that, `test_image_name_and_project_overrides_are_honoured`
   (unmodified) would lose project `mine`, and a student's custom project would
   be missed. `ros2.ps1` does the same with the environment's project and
   digest, and it keeps `docker compose config --images`. The survey groups
   images as all tags, then legacy tags, then bases, the default's first. The
   legacy image in `ros2.ps1` is now always `ros2-tutorials:<name>`. It used
   to be `${IMAGE_NAME or ros2-tutorials}:<distro>`.
4. **Verification 2 cleanup.** `make down` keeps volumes by design, so "no
   `st12-*` containers or volumes remain" could not follow from `make down`
   alone. After `make down` showed the containers gone, `make reset YES=1`
   with the same variables removed the volumes, and nothing `st12-*` remained.
5. **Test 11 details:**
   - The tests live in `tests/host/test_distros.py` (`PromptTests`), because
     no test file for the bashrc is on the allow-list.
   - The host's own `/etc/bash.bashrc` also runs under `bash -i`, and
     Ubuntu's prints a sudo hint to stdout, so the test reads `PS1` after a
     marker.
   - A non-interactive bash does not import `PS1`, so that test sets it
     inside the `-c` script.
   - The `PROMPT_COMMAND` path is tested with `bash -i` reading stdin, which
     prints its prompt to stderr.
6. **Choices the prompt left open:**
   - A missing port is refused, with the same message as a non-integer one.
   - Port messages:
     - `"<d>" has no "port", an integer from 1024 to 65535`
     - `"<d>" has port 6081, which make selftest keeps for itself`
     - `"<a>" and "<b>" share port <p>`
   - The object-type message now names `"port"`.
   - The shared-port check runs after the per-entry checks and before the
     default check.
   - `ros2.ps1` now reports a JSON parse failure as `not valid JSON (...)`,
     as the script does. A read failure is still `cannot read it (...)`.
7. **The first pwsh baseline was invalid, and the fault was mine** (the same
   slip as stage 11's Deviation 1). I edited `scripts/distros` while it ran,
   and `Housekeeping.test_the_repository_is_left_untouched_by_a_run` failed
   with `' M scripts/distros'`. I set the edit aside and restored the
   committed file. `git status` was clean when I reran it: 251 tests, OK
   (skipped=7). Then I put the edit back.
8. Extra checks beyond the prompt: the Windows PowerShell 5.1 run, the image
   check in the self-test test under make's kilted exports, and the real-shell
   prompt check in Verification 2.
9. Several shell commands were refused by this session's worktree guard, so
   edits and drivers ran as Python scripts from the scratchpad. The results
   are the same.

## 8. Open questions

1. **Jazzy self-test: "no message crossed between compose services".** The
   talker service starts, but nothing reaches `ros2 topic echo --once /chatter`
   within 30 s. For stage 13. Two possibilities, neither checked: a
   `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` difference on jazzy, or the talker
   starting slower than the fixed `sleep 10`.
2. **The busy-port hint drops the distribution.** `compose-up` suggests
   `make up NOVNC_PORT=6085 && make open NOVNC_PORT=6085`. For a student who
   typed `make up ROS_DISTRO=jazzy`, that command starts the default instead.
   It should probably carry `ROS_DISTRO=<name>` when that is not the default.
   Not changed: the hint's text is pinned by existing tests.
3. **A `NOVNC_PORT` in `.env` is now overridden by the table.** Make and
   `ros2.ps1` export the table's port, and the environment beats `.env` in
   compose. Before this stage, make did not export `NOVNC_PORT`, so compose
   took it from `.env`. For the default distribution with `.env.example`'s own
   line (`NOVNC_PORT=6080`) nothing changes. A student who pinned `.env` to,
   say, 7000 loses that pin. The command line and the environment still win.
   I tried letting `.env` win and reverted it before committing: nothing ran
   against it, and the committed files match the checksums gated above. The
   reason is that `.env.example` has an uncommented `NOVNC_PORT=6080`, so
   every student who copied it would have put all four distributions on
   6080. Stage 13 should drop or comment out that line in `.env.example` and
   document the precedence.
4. **`ghcr.io/durantschoon/ros2-classroom:latest` had already been rebuilt**
   about an hour before this stage's self-tests, by something else. The
   user's desktop runs image `f23041cc97de`, which is no longer the tag's.
   Their next `make up` will recreate it. This stage did not do that
   (Deviation 2).
5. **Uninstall reads the table leniently.** `scripts/uninstall` accepts any
   table with names, a default, and digests it can use, and skips a bad digest
   rather than refusing. `scripts/distros` is the strict judge. Everything
   else refuses a malformed table before uninstall could run, so the leniency
   only matters when uninstall is run directly.
6. `PROMPT_COMMAND` as a bash 5.1+ array: the hook is prepended to element 0.
   That is fine for the images' bash, but untested with an array set by a
   user.
7. `make check` is now about 92 s without pwsh and 150 s with it. The shared
   malformed-table test alone starts pwsh 13 times.
