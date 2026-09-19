# Stage 04 report — Port the host scripts to Python

Branch: `stage-04-port-host-scripts`. Base: `python-port` at `fac72a9`.
Ran in parallel with stage 03; nothing under `docker/scripts/` was touched.

## 1. Checklist echo

### The change

| Asked for | Result |
|---|---|
| `scripts/compose-command` ported to Python, in place | yes |
| `scripts/compose-up` ported to Python, in place | yes |
| `scripts/check-host` ported to Python, in place | yes |
| `scripts/run-quiet` ported to Python, in place | yes |
| `scripts/open-url` ported to Python, in place | yes |
| `scripts/base-image-digest` ported to Python, in place | yes |
| Same file names, no `.py`, `#!/usr/bin/env python3`, executable bit kept | yes — all six `-rwxrwxr-x`, all six still classified `python, host (3.9 grammar)` |
| Makefile, CI, docs, `scripts/smoke-container` need no change | yes — none of them is in the diff |
| Stdlib only, Python 3.9-compatible | yes — imports are `ast`-free stdlib only; the whole suite passes on real 3.9 (section 3, test 1) |
| `run-quiet`: stdout inherited, never piped | yes — test 6 shows `isatty()` is `True` through the wrapper |
| `run-quiet`: only stderr filtered, line by line as it arrives | yes — test 5 shows `one` two seconds before `two` |
| `run-quiet`: wrapped command's exit status returned | yes — pinned by `test_the_exit_status_is_preserved` |
| `run-quiet`: `VERBOSE=1` replaces the process (`os.execvp`) | yes |
| `run-quiet`: Ctrl-C stops the child and returns its status, no traceback | yes — test 3: exit 130, empty stderr |
| `run-quiet`: a child killed by a signal returns `128 + signal` | yes — test 4: 143 |
| `open-url`: URL printed and flushed before anything is launched | yes — `print(url, flush=True)` |
| `open-url`: `wslview`/`powershell.exe`/`open`/`xdg-open`/`$BROWSER` replace the process | yes — `os.execvp` on all five paths |
| `open-url`: `explorer.exe` is run and its status ignored | yes |
| `open-url`: WSL from `WSL_DISTRO_NAME` **or** `/proc/version` | yes — `looks_like_wsl()` |
| `open-url`: `xdg-open` never used on WSL | yes — pinned by `test_xdg_open_is_never_used_on_wsl` |
| `compose-command`: any unrecognised argument means the default mode | yes — `parse_mode()` falls through |
| `compose-up`: multi-word `COMPOSE` split into words | yes — `compose.split()` |
| `compose-up`: the `+ … up -d` line echoed before running | yes, and flushed before `execvp` |
| `compose-up`: compose replaces the process | yes — `os.execvp` |
| `check-host`: calls `scripts/compose-command` next to itself, by path | yes — `Path(__file__).resolve().parent / "compose-command"` |
| `check-host`: colour escapes printed unconditionally | yes |
| `base-image-digest`: fetches with `curl`, as a subprocess, same arguments | yes — argv pinned by `test_the_token_is_requested_for_the_ros_repository` |
| Engine and output modes are `Enum`s parsed once at the entry point | yes — `Engine` in `compose-command`, `compose-up`, `check-host`; `Mode` in `compose-command` |
| Decisions in pure functions | yes — every file has a `--- pure core ---` / `--- imperative shell ---` split |
| Every command an argv list; no `shell=True`, no `os.system` | yes — `grep -n "shell=True\|os.system"` over the six exits 1 (section 3, DoD) |
| No shared module; each script self-contained | yes — no new files under `scripts/` |
| Nothing outside the allow-list touched | yes — section 7 |

### Behaviour change 1 — `compose-up` finds the desktop of the project in use

| Asked for | Result |
|---|---|
| Precedence: `-p`/`--project-name` in `COMPOSE`, then `COMPOSE_PROJECT_NAME`, then `ros2-tutorials` | yes — `project_name()` |
| All four flag spellings (`-p N`, `-p=N`, `--project-name N`, `--project-name=N`) | yes |
| `test_it_looks_for_the_desktop_of_this_compose_project` keeps passing unmodified | yes — untouched, still passes |
| Added tests for each of the four spellings | yes — 4 tests |
| Added test for rule 2 | yes — `test_compose_project_name_names_the_project` |
| Added test for rule 1 beating rule 2 | yes — `test_a_project_flag_beats_the_environment_variable` |
| Added test that a stale image *is* detected under `-p other` | yes — `test_a_stale_image_is_detected_under_a_project_override` |
| Additions only to `tests/host/test_compose_up.py` | yes — 60 insertions, 0 deletions |

All seven fail against the base's shell `compose-up` (section 5), so they pin
the change rather than merely describing it.

### Behaviour change 2 — `base-image-digest` matches the header case-insensitively

| Asked for | Result |
|---|---|
| Header name matched case-insensitively | yes — `parse_digest()` lower-cases the prefix |
| `test_an_all_uppercase_header_is_not_matched_today` replaced by one asserting it **is** matched | yes |
| One added test for a mixed case the old pattern also missed | yes, with a correction — see Deviation 2 |
| No other test in that file changed | yes — the diff is one replacement plus one addition |

### Definition of Done

| Asked for | Result |
|---|---|
| Baseline `make lint` on the unmodified base | pass — 25 files, 25 ok, 0 advisory, 0 FAIL |
| Baseline `make check` (104 expected) | pass — **104** tests, OK (skipped=4) |
| Baseline isolated `make selftest` (45/45 expected) | pass — **45 passed, 0 failed** |
| Final `make lint` passes | pass — 25 files, 25 ok, 0 FAIL |
| Final `make lint` classifies all six as `python, host (3.9 grammar)` | yes — all six |
| Final `make check` passes, count rises by exactly the added tests | pass — **112**; arithmetic in section 2 |
| Final isolated `make selftest`, same count and same check names | pass — **45 passed, 0 failed**; set difference empty |
| Tests 1–8 pass, output in the report | yes — section 3 |
| `grep -n "shell=True\|os.system"` over the six finds nothing | yes — grep exits 1 |
| `git diff python-port --stat` shows only allowed files | yes — section 7 |
| The two test files' diffs show only the authorized edits | yes — sections 5 and 7 |

## 2. Gate outputs, baseline and final

Every command below was run with `export PATH="$HOME/.local/bin:$PATH"` first,
from the stage worktree. The harmless zsh `add_to_front_of_path` line is
omitted throughout.

### `make lint`

Baseline, on the unmodified base `fac72a9`:

```
podman-compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: podman run --rm -v <worktree>:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
ok       docker/bashrc.d/ros-workspace.sh      bash (sourced), enforced
ok       docker/desktop/openbox-autostart      shell, enforced
ok       docker/entrypoint.sh                  shell, enforced
ok       docker/scripts/init-workspace         shell, advisory
ok       docker/scripts/install-ros-packages   shell, advisory
ok       docker/scripts/pkg                    shell, advisory
ok       docker/scripts/turtlesim-teleop       python, container
ok       docker/scripts/tutorial               shell, advisory
ok       scripts/base-image-digest             shell, advisory
ok       scripts/check-host                    shell, advisory
ok       scripts/compose-command               shell, advisory
ok       scripts/compose-up                    shell, advisory
ok       scripts/lint-scripts                  python, host (3.9 grammar)
ok       scripts/open-url                      shell, advisory
ok       scripts/run-quiet                     shell, advisory
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

Final:

```
podman-compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: podman run --rm -v <worktree>:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
ok       docker/bashrc.d/ros-workspace.sh      bash (sourced), enforced
ok       docker/desktop/openbox-autostart      shell, enforced
ok       docker/entrypoint.sh                  shell, enforced
ok       docker/scripts/init-workspace         shell, advisory
ok       docker/scripts/install-ros-packages   shell, advisory
ok       docker/scripts/pkg                    shell, advisory
ok       docker/scripts/turtlesim-teleop       python, container
ok       docker/scripts/tutorial               shell, advisory
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

The only change is the six `shell, advisory` rows becoming
`python, host (3.9 grammar)`. `scripts/smoke-container` is the one shell script
left under `scripts/`; it is stage 05's.

### `make check`

Baseline:

```
python3 -m unittest discover -s tests/host
.............................................................ssss.......................................
----------------------------------------------------------------------
Ran 104 tests in 4.161s

OK (skipped=4)
```

Final:

```
python3 -m unittest discover -s tests/host
.....................................................................ssss.......................................
----------------------------------------------------------------------
Ran 112 tests in 6.546s

OK (skipped=4)
```

The arithmetic:

| | tests |
|---|---|
| baseline | 104 |
| `test_an_all_uppercase_header_is_not_matched_today` removed | −1 |
| `test_an_all_uppercase_header_is_matched` added (its replacement) | +1 |
| `test_a_mixed_case_header_is_matched` added | +1 |
| seven project-name tests added to `test_compose_up.py` | +7 |
| **final** | **112** |

Net +8, and 104 + 8 = 112. The four skips are unchanged: the same four
`open-url` macOS/Linux tests that skip on a WSL host by design.

### `make selftest`, isolated

Both runs used exactly:

```sh
SELFTEST_PROJECT=ros2-tutorials-st04 SELFTEST_NOVNC_PORT=6084 \
SELFTEST_ROS_DOMAIN_ID=84 IMAGE_NAME=ros2-tutorials-st04 make selftest
```

The bare `make selftest` was never run. The projects `ros2-tutorials`,
`ros2-tutorials-selftest`, and `ros2-tutorials-st03` were never stopped,
recreated, or altered.

Baseline result line:

```
== Result
45 passed, 0 failed
```

Final result line:

```
== Result
45 passed, 0 failed
```

Both runs exited 0. The check names were extracted from each log with
`grep -E '^  (PASS|FAIL) '` (45 lines each) and compared as sets:

```
$ diff <(sort baseline-checks.txt) <(sort final-checks.txt)
(no output)
```

**The set difference is empty**: no check was added, removed, renamed, or
turned from PASS to FAIL. All 45, in run order, were:

```
PASS image builds
PASS desktop container accepts commands
PASS the image defaults to the non-root ros user
PASS desktop programs run as the non-root ros user
PASS ROS_DISTRO is set
PASS the self-test runs in its own ROS domain, not the student default
PASS ros2 is on PATH
PASS rosdep is on PATH
PASS colcon is on PATH
PASS turtlesim_node and turtle_teleop_key are installed
PASS turtlesim stays alive for 5s on the virtual display
PASS noVNC answers inside the container
PASS noVNC answers on the host at http://localhost:6084
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
PASS a second init-workspace reports the workspace is already initialized
PASS init-workspace leaves the existing workspace marker untouched
PASS tutorial with no arguments exits 2 and prints usage
PASS tutorial clone echoes the real git command and succeeds
PASS the clone lands in /workspace/src
PASS tutorial list names the cloned repository
PASS tutorial build echoes colcon build --packages-select and succeeds
PASS pkg with no arguments exits 2 and prints usage
PASS pkg new --python --interfaces is refused with an explanation
PASS the refused interface package was never created
PASS pkg new refuses to create a package that already exists
PASS the existing package is byte-identical after the refusal
PASS workspace source survives container recreation
PASS built overlay survives container recreation
```

Worth naming: the "Student make targets" section runs `make package`,
`make build`, and `make test` from the host, as a student would. Each of those
is `$(QUIET) $(COMPOSE) exec …` in the Makefile, so it goes through the ported
`run-quiet`, with `COMPOSE` and `ENGINE` coming from the ported
`compose-command --make`. Those two scripts were therefore exercised against
the real Podman, end to end, and not only against the fakes in `tests/host`.
`compose-up`, `open-url`, `check-host`, and `base-image-digest` are not
reached by the self-test; they are covered by `make check` and by tests 7 and 8
above.

## 3. Tests 1–8

### Test 1 — Python 3.9 for real

```
$ podman run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo \
      docker.io/library/python:3.9-slim python -m unittest discover -s tests/host
.....................................................................ssss.................sssss.................
----------------------------------------------------------------------
Ran 112 tests in 7.152s

OK (skipped=9)
```

All 112 tests run; 9 skip and none fails. The nine skips, from the `-v` run:

- 4 × `test_open_url` macOS/Linux branches — "this host's /proc/version says
  microsoft"; the container shares the WSL kernel, so it inherits the skip.
- 5 × `test_workstation_help.MakeHelpModeTests` — "make is not installed" in
  `python:3.9-slim`, which is the documented reason those tests skip.

**Extra, beyond what was asked.** Because the four `open-url` skips hide two
branches I rewrote, I reached them by giving the same container a
`/proc/version` that does not say microsoft:

```
$ podman run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro \
      -v <a file reading "Linux version 6.1.0-generic ...">:/proc/version:ro \
      -w /repo docker.io/library/python:3.9-slim \
      python -m unittest discover -s tests/host -k OpenUrl -v
test_linux_uses_xdg_open (test_open_url.OpenUrlTests) ... ok
test_linux_without_xdg_open_exits_zero_with_the_fallback_message (test_open_url.OpenUrlTests) ... ok
test_macos_uses_open (test_open_url.OpenUrlTests) ... ok
test_macos_without_open_falls_back_to_the_message (test_open_url.OpenUrlTests) ... ok
...
Ran 15 tests in 0.652s

OK
```

All 15 `open-url` tests, including the four that skip on this host, pass on
real 3.9. That is why the port keeps calling `uname -s` as a subprocess rather
than reading `platform.system()`: the tests fake `uname` on the sandbox PATH.

### Test 2 — Mutations

Procedure: apply one mutation to the real script, run that script's own test
module, restore the file from a byte-identical copy kept outside the
repository, and confirm the restore by md5. All six mutations differ from the
ones in `stage-02-REPORT.md`.

| # | Script | Mutation | Tests that failed | Reverted |
|---|---|---|---|---|
| 1 | `scripts/compose-command` | Swapped the last two `CANDIDATES`, so the `docker-compose` binary is probed before `podman-compose` | `test_podman_compose_binary_is_third` (1 failure) | md5 back to `5eb661de…` |
| 2 | `scripts/compose-up` | `bare()` stopped stripping the `sha256:` prefix (`return image_id`) | 2 failures: `test_a_sha256_prefix_on_one_side_still_counts_as_equal`, `test_a_sha256_prefix_on_the_current_image_still_counts_as_equal` | md5 back to `c00d396a…` |
| 3 | `scripts/run-quiet` | `is_noise()` used `PATTERN.match` instead of `PATTERN.search`, so the filter only fires at the start of a line | 4 failures: `test_the_cni_warning_is_dropped_from_stderr`, `test_the_shared_mount_warning_is_dropped_from_stderr`, `test_every_other_stderr_line_passes_through`, `test_a_verbose_value_other_than_one_still_filters` | md5 back to `8b66a514…` |
| 4 | `scripts/open-url` | Moved the WSL branch ahead of the `$BROWSER` branch | `test_browser_wins_when_the_command_exists` (1 failure) | md5 back to `0375330b…` |
| 5 | `scripts/check-host` | `engine_version()` dropped the `--version` fallback and returned only the `--format` result | `test_the_version_falls_back_to_the_plain_version_flag` (1 failure) | md5 back to `7f648ed7…` |
| 6 | `scripts/base-image-digest` | Removed `application/vnd.oci.image.index.v1+json` from `INDEX_MEDIA_TYPES` | `test_both_multi_arch_index_media_types_are_accepted` (1 failure) | md5 back to `a8ed81fe…` |

Verbatim failure line from each run, in order:

```
FAIL: test_podman_compose_binary_is_third (test_compose_command.ComposeCommandTests)
AssertionError: 'podman-compose\n' != 'docker-compose\n'

FAIL: test_a_sha256_prefix_on_one_side_still_counts_as_equal (test_compose_up.ComposeUpTests)
AssertionError: 'The image was rebuilt since this desktop started, so it will be recreated.' unexpectedly found in ...

FAIL: test_the_cni_warning_is_dropped_from_stderr (test_run_quiet.RunQuietTests)

FAIL: test_browser_wins_when_the_command_exists (test_open_url.OpenUrlTests)
AssertionError: Lists differ: [['http://localhost:6080/vnc.html?autoconnect=1&resize=remote&reconnect=true']] != []

FAIL: test_the_version_falls_back_to_the_plain_version_flag (test_check_host.CheckHostTests)
AssertionError: '  ok    engine:  docker Docker version 24.0.7, build afdd53b' not found in 'Container engine\n  ok    compose: docker compose\n  ok    engine:  docker \n...'

FAIL: test_both_multi_arch_index_media_types_are_accepted (test_base_image_digest.BaseImageDigestTests)
AssertionError: 'Accept: application/vnd.oci.image.index.v1+json' not found in ['-fsS', '-I', '-H', 'Authorization: Bearer TOK123', '-H', 'Accept: application/vnd.docker.distribution.manifest.list.v2+json', 'https://registry-1.docker.io/v2/library/ros/manifests/lyrical-ros-base']
```

After all six, `git status --porcelain` showed exactly the eight files this
stage is allowed to change and no others, and `make check` was green again:

```
$ git status --porcelain
 M scripts/base-image-digest
 M scripts/check-host
 M scripts/compose-command
 M scripts/compose-up
 M scripts/open-url
 M scripts/run-quiet
 M tests/host/test_base_image_digest.py
 M tests/host/test_compose_up.py

$ md5sum scripts/compose-command scripts/compose-up scripts/check-host \
         scripts/run-quiet scripts/open-url scripts/base-image-digest
5eb661de349b8c0917bfa3a6df5d7f16  scripts/compose-command
c00d396a2ac4d5189cf30361db47cacd  scripts/compose-up
7f648ed74d7ff26e6a321433006c373a  scripts/check-host
8b66a514af04dfcc7458bb4189853bcc  scripts/run-quiet
0375330b446ae21b49eba13c77f3765d  scripts/open-url
a8ed81fe19912fdebf2a61df779e8b1d  scripts/base-image-digest

$ make check
Ran 112 tests in 6.546s

OK (skipped=4)
```

(Mutation 1 was first reverted with `git checkout -- scripts/compose-command`,
which restored the *committed shell* script rather than the uncommitted port.
It was caught immediately and the port rewritten; see Deviation 3. Every later
revert used the copy-and-md5 procedure above.)

### Test 3 — Ctrl-C through `run-quiet`

A terminal sends SIGINT to the whole foreground process group, so the harness
puts `run-quiet` in its own group with `os.setsid` and signals the group:

```
$ python3 <harness>  # runs `scripts/run-quiet sleep 30`, then killpg(SIGINT)
returncode: 130
returned after: 0.00s (the child was a 30s sleep)
stdout: ''
stderr: ''
traceback in stderr: False
```

No traceback, an immediate return rather than the child's remaining 29
seconds, and exit 130 = 128 + SIGINT.

### Test 4 — A signal-killed child

```
$ scripts/run-quiet sh -c 'kill -TERM $$'
exit=143
```

143 = 128 + SIGTERM.

### Test 5 — Streaming

```
$ scripts/run-quiet sh -c 'echo one >&2; sleep 2; echo two >&2' 2>&1 \
    | while IFS= read -r l; do printf '%s %s\n' "$(date +%s.%N)" "$l"; done
1789763643.560321268 one
1789763645.573310186 two
```

2.013 s apart: stderr is forwarded as it arrives, not buffered until exit.

### Test 6 — Interactive stdout

This session has no controlling terminal, so the harness supplies one with
`pty.spawn` (the `script -qc` the prompt suggests was unavailable here):

```
$ python3 <pty harness>  # pty.spawn(["scripts/run-quiet", "python3", "-c",
                         #             "import sys; print(sys.stdout.isatty())"])
True
wait status: 0
```

`True`: stdout reaches the wrapped command as the real terminal, never a pipe.

### Test 7 — Closed pipe

```
$ scripts/check-host | head -1
Container engine
pipeline rc=0

$ scripts/compose-command --explain | head -1
using podman-compose (engine: podman)
pipeline rc=0
```

No traceback and no `Exception ignored in: <_io.TextIOWrapper ...>` noise. Each
script sets `SIGPIPE` back to `SIG_DFL` at the entry point, so a closed pipe
kills it exactly as it killed the shell.

### Test 8 — The real thing

`make doctor`, `make engine`, and `make digest` were captured before and after.
For a byte-exact comparison the base tree was extracted with
`git archive fac72a9 | tar -x` into a scratch directory outside the repository,
so both versions ran against the same real Podman, in the same minute.

`make doctor` (before and after are the same bytes; escapes shown with `cat -v`):

```
Container engine
  ^[[32mok^[[0m    compose: podman-compose
  ^[[32mok^[[0m    engine:  podman 3.4.4
  ^[[33mwarn^[[0m  podman 3.4.4 predates `podman compose`; using podman-compose
        -> pip install --user -r requirements-host.txt   (already satisfied)
  ^[[32mok^[[0m    podman is running rootless

Resources
  ^[[32mok^[[0m    disk free: 910 GB
  ^[[32mok^[[0m    memory: 15 GB

Ready: run `make image`, then `make up`.
```

`make engine`:

```
using podman-compose (engine: podman)
```

`make digest`:

```
sha256:0c19f326a339ed770ef1d4c0646a8b53bdb49dd5ff74b6de41ebdb8ac21e1806
```

`diff -u` of the three before/after captures reported no difference other than
the `before rc=0` / `after rc=0` marker line the capture itself appended. All
three exited 0 both times.

**Extra.** `compose-up` was also exercised against the real engine, read-only,
by giving it `COMPOSE=true` so that nothing is started or recreated:

```
$ COMPOSE=true ENGINE=podman <base>/scripts/compose-up      # shell
The image was rebuilt since this desktop started, so it will be recreated.
Kept: /workspace and /home/ros (your code, builds, and settings).
Lost: anything added with apt or install-ros-packages inside the old container.

+ true up -d --force-recreate
exit=0

$ COMPOSE=true ENGINE=podman ./scripts/compose-up            # python
The image was rebuilt since this desktop started, so it will be recreated.
Kept: /workspace and /home/ros (your code, builds, and settings).
Lost: anything added with apt or install-ros-packages inside the old container.

+ true up -d --force-recreate
exit=0
```

Identical, including the stale-image verdict on the user's own
`ros2-tutorials` desktop. Nothing was stopped, recreated, or removed: the
compose command was `true`.

## 4. Line counts

| Script | Shell | Python | Change |
|---|---|---|---|
| `scripts/compose-command` | 64 | 162 | +98 |
| `scripts/compose-up` | 46 | 226 | +180 |
| `scripts/check-host` | 63 | 243 | +180 |
| `scripts/run-quiet` | 39 | 111 | +72 |
| `scripts/open-url` | 56 | 130 | +74 |
| `scripts/base-image-digest` | 26 | 122 | +96 |
| **total** | **294** | **994** | **+700** |

The growth is mostly comments, docstrings, type annotations, and the
`pure core` / `imperative shell` split the guardrails ask for; `compose-up`
also carries the new project-name rule. No script gained a feature.

## 5. The exact test edits

### `tests/host/test_base_image_digest.py` — one replacement, one addition

```diff
-    def test_an_all_uppercase_header_is_not_matched_today(self):
-        """Pins current behaviour: the match varies only the first letter of each word."""
+    def test_an_all_uppercase_header_is_matched(self):
+        """HTTP header names are case-insensitive, so the match is too."""
         self.curl(header_block=headers("DOCKER-CONTENT-DIGEST: " + DIGEST))
         run = self.run_script()
-        self.assertNotEqual(0, run.status, run.report())
-        self.assertHas(run, "no digest for ros:lyrical-ros-base", where="stderr")
+        self.assertStatus(run, 0)
+        self.assertEqual(DIGEST + "\n", run.stdout)
+
+    def test_a_mixed_case_header_is_matched(self):
+        """Mixed case, including a spelling the old pattern missed.
+
+        The old [Dd]ocker-[Cc]ontent-[Dd]igest varied only the FIRST letter of
+        each word, so Docker-content-Digest happened to match while
+        Docker-Content-DIGEST did not.  Both must match now.
+        """
+        for spelling in ("Docker-content-Digest", "Docker-Content-DIGEST"):
+            with self.subTest(header=spelling):
+                self.setUp()
+                self.curl(header_block=headers(spelling + ": " + DIGEST))
+                run = self.run_script()
+                self.assertStatus(run, 0)
+                self.assertEqual(DIGEST + "\n", run.stdout)
```

No other test in the file changed.

### `tests/host/test_compose_up.py` — seven added tests, nothing else

60 insertions, 0 deletions (`git diff python-port --numstat` → `60  0`). Added
in a new `--- which compose project's desktop it looks for ---` section,
immediately before `test_the_image_name_and_distro_can_be_overridden`: two
helpers (`project_filter`, `run_with`) and

- `test_a_short_project_flag_in_compose_names_the_project` (`-p other`)
- `test_a_short_project_flag_with_an_equals_names_the_project` (`-p=other`)
- `test_a_long_project_flag_in_compose_names_the_project` (`--project-name other`)
- `test_a_long_project_flag_with_an_equals_names_the_project` (`--project-name=other`)
- `test_compose_project_name_names_the_project` (rule 2)
- `test_a_project_flag_beats_the_environment_variable` (rule 1 beats rule 2)
- `test_a_stale_image_is_detected_under_a_project_override` (the point of the change)

### Both new tests actually pin the change

The base tree was extracted with `git archive fac72a9`, the two edited test
files copied into it, and the suite run there — new tests against the old shell
scripts:

```
$ (in the extracted base tree) python3 -m unittest discover -s tests/host -k test_compose_up
Ran 21 tests in 1.092s
FAILED (failures=7)

$ (in the extracted base tree) python3 -m unittest discover -s tests/host -k test_base_image_digest
FAIL: test_a_mixed_case_header_is_matched (...) (header='Docker-Content-DIGEST')
FAIL: test_an_all_uppercase_header_is_matched (...)
Ran 16 tests in 0.508s
FAILED (failures=2)
```

Exactly the seven new `compose-up` tests fail, and exactly the two changed
digest assertions fail — and the `subTest` label names which spelling was the
real miss (see Deviation 2). The other 14 `compose-up` tests and the other 14
digest tests pass unchanged against the old shell, which is the evidence that
nothing else moved.

## 6. Every place the Python output differs from the shell output

Six differences, all outside the paths the tests, the docs, the Makefile, and
`scripts/smoke-container` depend on. Two are the sanctioned behaviour changes;
four are error messages that used to carry `sh`'s interpreter noise.

| # | Where | Shell | Python | Why acceptable |
|---|---|---|---|---|
| 1 | `compose-up`, `COMPOSE` or `ENGINE` unset | `scripts/compose-up: 14: COMPOSE: COMPOSE is not set; run this through make`, exit 2 | `compose-up: COMPOSE is not set; run this through make`, exit 2 | Same sentence, same exit status; only `sh`'s `<path>: <line>: <var>:` prefix is gone. The test pins the sentence and a non-zero status, both preserved. Guardrail 3 wants a plain message, not interpreter noise. |
| 2 | `open-url` with no argument | `scripts/open-url: 13: 1: usage: open-url URL`, exit 2 | `usage: open-url URL`, exit 2 | As above. `test_a_missing_url_is_a_usage_error` pins the sentence and non-zero; both hold, and exit 2 matches dash exactly. |
| 3 | `run-quiet` with a command that does not exist (both plain and `VERBOSE=1`) | `scripts/run-quiet: 36: definitely-not-a-command: not found`, exit 127 | `run-quiet: definitely-not-a-command: No such file or directory`, exit 127 | Exit status identical (127); the wording is the OS's `strerror` instead of dash's. Same for `compose-up` and `open-url` when an `exec` fails. |
| 4 | `compose-up` with `ENGINE` set to something other than `docker` or `podman` | silently degraded: both `image inspect` calls failed into `/dev/null`, so it printed `+ <compose> up -d` and started the desktop with the stale-image check quietly disabled, exit 0 | `compose-up: ENGINE is 'not-an-engine', which is neither docker nor podman`, exit 2 | Guardrail 1 makes the engine a closed set and guardrail 3 makes an unexpected value an explicit error. The old behaviour was the failure mode this script exists to prevent, arrived at silently. `ENGINE` only ever comes from `compose-command --make`, so no supported path reaches it. Not covered by any test either way. |
| 5 | `compose-up` project label | always `com.docker.compose.project=ros2-tutorials` | the project actually in use (flag, then `COMPOSE_PROJECT_NAME`, then `ros2-tutorials`) | Sanctioned behaviour change 1. Under the default it is byte-identical, which `test_it_looks_for_the_desktop_of_this_compose_project` still pins unmodified. |
| 6 | `base-image-digest` header match | `^[Dd]ocker-[Cc]ontent-[Dd]igest: ` | case-insensitive | Sanctioned behaviour change 2. Every header spelling the old pattern matched is still matched; strictly more are. |

Checked and found **identical**, byte for byte: `make doctor` (including every
colour escape and both resource numbers), `make engine`, `make digest`,
`compose-command` in all four modes and in the nothing-found case,
`compose-up`'s stale-image paragraph and `+ …` line, `run-quiet`'s filtering
and exit statuses, and `open-url`'s printed URL and both fallback messages.

Two places where the port matches a shell subtlety that no test covers, noted
so a reviewer need not rediscover them:

- `run-quiet` appends a newline to a final stderr line that lacks one, because
  GNU `grep -v` does (`printf 'abc' | grep -v x` emits `abc\n`). `terminated()`
  reproduces that.
- `check-host` still shells out to `df -Pk .` rather than using `os.statvfs`.
  On this host the two disagree by 4 kB (954594748 vs 954594744), which rounds
  to the same `910 GB` — but only `df` guarantees the number can never drift.

## 7. `git diff python-port --stat`

```
 scripts/base-image-digest            | 136 +++++++++++++---
 scripts/check-host                   | 306 +++++++++++++++++++++++++++--------
 scripts/compose-command              | 226 ++++++++++++++++++--------
 scripts/compose-up                   | 272 +++++++++++++++++++++++++------
 scripts/open-url                     | 184 ++++++++++++++-------
 scripts/run-quiet                    | 150 ++++++++++++-----
 tests/host/test_base_image_digest.py |  23 ++-
 tests/host/test_compose_up.py        |  60 +++++++
 8 files changed, 1066 insertions(+), 291 deletions(-)
```

Eight files, every one on the allow-list, plus this report. Nothing under
`docker/scripts/` (stage 03's), and no change to `Makefile`, `compose.yaml`,
`Dockerfile`, `.github/workflows/docker-image.yml`, `scripts/smoke-container`,
`scripts/lint-scripts`, or `scripts/workstation-help`.

## 8. Deviations

1. **The worktree started at a stale commit, as the prompt predicted.**
   `git rev-parse HEAD` gave `8256560 docs: record the teaching purpose,
   roadmap, and platform checklist`, and `docs/stages/` did not exist. Per the
   prompt's "First step" I ran `git fetch origin && git merge --ff-only
   origin/python-port`, which fast-forwarded to `fac72a9`, then renamed the
   branch to `stage-04-port-host-scripts`. All baselines were measured after
   that, on an otherwise unmodified `fac72a9`.

2. **The prompt's example of a missed mixed-case header was wrong, so the added
   test covers both it and a spelling that really was missed.** The prompt asks
   for "a mixed case the old pattern also missed (`Docker-content-Digest`)".
   The old pattern `^[Dd]ocker-[Cc]ontent-[Dd]igest: ` varies the first letter
   of each word, and `Docker-content-Digest` varies only first letters, so it
   **was** matched:

   ```
   $ printf 'Docker-content-Digest: sha256:abc\r\n' | tr -d '\r' \
       | sed -n 's/^[Dd]ocker-[Cc]ontent-[Dd]igest: //p'
   sha256:abc
   $ printf 'Docker-Content-DIGEST: sha256:abc\r\n' | tr -d '\r' \
       | sed -n 's/^[Dd]ocker-[Cc]ontent-[Dd]igest: //p'
   (nothing)
   ```

   A test using only the prompt's spelling would have passed against the old
   shell too, and so would have pinned nothing. Minimal resolution: one added
   test that `subTest`s over both `Docker-content-Digest` (the prompt's
   spelling, kept) and `Docker-Content-DIGEST` (one the old pattern genuinely
   missed). That is still "one added test", and section 5 shows it failing
   against the old shell on exactly the second spelling. Flagging rather than
   silently substituting.

3. **Mutation 1 was reverted with `git checkout --`, which was wrong here, and
   the file had to be rewritten.** Stage 02 could revert mutations that way
   because its scripts were committed; in this stage the ports are uncommitted,
   so `git checkout -- scripts/compose-command` restored the *shell* script.
   Caught within one command, the Python file was rewritten from the content
   just authored, and its md5 (`5eb661de…`) then matched a fresh copy. Every
   later mutation used copy-out / copy-back with an md5 check, and `make check`
   after all six was green at 112. No trace remains — `git diff python-port`
   contains no shell.

4. **`check-host` keeps two subprocesses it could have dropped.** `df -Pk .`
   stays a subprocess (see section 6) so the GB figure can never drift from
   what `make doctor` printed yesterday; `uname -s` in `open-url` stays one
   because `test_macos_uses_open` fakes `uname` on PATH and would otherwise be
   unreachable. `awk` and `sed`, by contrast, are gone: `/proc/meminfo` and the
   8-space indent are parsed in Python.

5. **`check-host` no longer dies if `df` prints something unparseable.** In
   `sh`, an empty `disk_kb` would have reached `$((disk_kb / 1024 / 1024))` and
   aborted the script under `set -e`, losing the memory line and the verdict.
   The port omits just that one line. No test covers either behaviour; a
   traceback-or-abort for an expected condition is what guardrail 3 forbids.

6. **`compose-up` word-splits `COMPOSE` with `str.split()`, not `shlex.split`.**
   That is what the shell's unquoted `${compose}` did: split on whitespace with
   no quote processing. `shlex.split` would have been a behaviour change for a
   `COMPOSE` containing quotes.

7. **Usage and unset-environment errors exit 2, not 1.** Chosen to match dash's
   `${var:?}`, which was measured at 2 on this host for both scripts, rather
   than the more conventional 1. The tests require only non-zero.

8. **The report's `<worktree>` placeholder.** The `make lint` transcripts above
   have the absolute worktree path replaced with `<worktree>` in the
   `shellcheck via:` line, as `stage-02-REPORT.md` also did. Nothing else in
   any pasted output is elided.

9. **Test 6 used `pty.spawn`, not `script -qc`.** The prompt allows a
   substitute if no terminal is available and asks that it be said; this
   session has no controlling terminal, and `script` invocations were refused
   by the sandbox, so a `pty.spawn` harness supplied the terminal instead. It
   proves the same thing: `sys.stdout.isatty()` is `True` inside the wrapped
   command.

10. **Two verifications were run that the prompt did not ask for**, both
    read-only and both reported above: the `open-url` non-WSL branches under a
    faked `/proc/version` (test 1), and `compose-up` against the real Podman
    with `COMPOSE=true` (test 8). Neither changed any file.

## 9. Open questions

1. **`-pNAME` (attached, no space, no `=`) is not recognised.** The prompt
   named four spellings and `project_name()` implements exactly those. Both
   Docker Compose and podman-compose also accept `-pNAME`, and a student who
   wrote `COMPOSE='podman-compose -pmine'` would silently get the old failure
   back. One line to add; deliberately not added, since the closed set of
   spellings was the architect's.

2. **`COMPOSE_PROJECT_NAME` is read but never passed on.** `compose-up` now
   consults it to find the desktop, but the compose command it execs inherits
   it from the environment as before. That is consistent, but it means the
   project name is decided in two places; a single `--project-name` appended to
   the exec'd argv would make it one. Out of scope.

3. **Repeated project flags: last one wins.** `COMPOSE='c -p a -p b'` resolves
   to `b`, matching how compose's own argument parsing behaves. Not specified
   in the prompt and not covered by a test.

4. **`run-quiet` handles SIGINT but not SIGTERM or SIGHUP.** Ctrl-C was the
   named requirement. A `make run` killed with `kill` still leaves the child to
   the default disposition and the parent dies first, which is also what the
   shell did — but if the pipeline ever wants "stop the child, then report",
   SIGTERM and SIGHUP want the same treatment as SIGINT.

5. **The two `--explain` paragraphs in `compose-command` are still prose in the
   script.** They are the only user-facing text in this stage that a
   non-developer would want to reword, and they are now in a pure function
   (`explain_nothing_found`) that returns a list of lines — easy to move to
   `scripts/workstation-help` or a data file later if the docs and the script
   should stop repeating each other.

6. **`scripts/smoke-container` still calls `$ENGINE image inspect` with the
   same `localhost/` fallback that `compose-up` now has as a pure function.**
   Stage 05 ports it; the duplication is worth a look then, though "each script
   stays self-contained" means it should probably stay duplicated.

7. **Nothing exercises `compose-command`'s `docker compose` branch on this
   host.** The tests fake it thoroughly, but every real run here resolves to
   `podman-compose`. The Docker paths in all six scripts have only ever been
   tested against fakes; CI on real Linux with Docker would be the first real
   exercise.
