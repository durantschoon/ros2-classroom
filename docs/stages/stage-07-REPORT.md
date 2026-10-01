# Stage 07 — REPORT (attempt 2)

## First step

`git log --oneline -1` in the worktree, before anything else:

```
11c8a64 docs(stages): stage 07 attempt 2 -- the ros2.ps1 shared-table test on macOS, and attempt 1's open questions
```

After `git fetch origin` the worktree was already at `11c8a64` =
`origin/native-recipes`. `docs/stages/stage-07-PROMPT.md` was present and
begins "**Attempt 2.**". I created the branch with
`git checkout -b stage-07-first-run-question-r2 origin/native-recipes`.
Attempt 1's blocked report is `docs/stages/stage-07-REPORT.md` on branch
`stage-07-first-run-question`, commit `f4662ad`. I did not touch that branch.

## Checklist echo

The change:

- [x] 0. `test_both_refuse_every_malformed_table_alike` splits each refusal at
  its first `": "`. It checks each script's path with `os.path.samefile`
  against the table the test wrote, and compares the words after the path.
  The status and one-line checks stay. A comment says why. 13/13 subtests
  pass with `pwsh`, and the negative control fails 7.
- [x] 1. `scripts/explain-choice`:
  - stdlib only, 3.9 grammar, executable, no extension, `#!/usr/bin/env python3`.
  - A `Mode` enum (`--ask-once`, `--choose`, `--show`) parsed once. Anything
    else prints usage on stderr and exits 2.
  - An `Explain` enum (`off`, `on`, `only`). `only` is never saved.
  - The question word for word, with retries, Ctrl-D, and Ctrl-C (exit 130).
  - `.workstation/preferences.json`, found from the script's own location and
    written atomically (`mkstemp` in the same directory, then `os.replace`).
  - A file that cannot be read is reported in one line naming the file, then
    treated as not saved.
  - Pure functions `parse_mode`, `parse_override`, `parse_saved`,
    `parse_answer`, `decide` and `render_question` (plus other `render_*`),
    with I/O at the edges.
- [x] 2. `Makefile`:
  - Phony `first-run` (`@./scripts/explain-choice --ask-once`) is the first
    prerequisite of `up open shell turtlesim turtlesim-teleop package build
    run test`, and of nothing else.
  - Phony `choose` (`@./scripts/explain-choice --choose`).
  - Both are in `.PHONY`.
  - Every student target in the base Makefile is named in one of the prompt's
    two lists, so no target is left unlisted.
- [x] 3. `scripts/workstation-help`:
  - `make choose` is the last row of "Start here -- once per machine".
    `first-run` is not listed.
  - `choose` has a `help` topic: the question, the two answers, where the
    answer is saved, and `EXPLAIN=0/1/only`. There is no examples topic.
  - The row is unmarked, and the test that pins the marked rows is unchanged.
- [x] 4. `ros2.ps1`:
  - A `choose` command. `.\ros2.ps1 help` lists it right after `distros`,
    which is where `make help` has it (after `make distros`). `choose help`
    is accepted.
  - It asks once before the same nine commands, and before `desktop` (once).
  - The same file and JSON bytes, written atomically.
  - The same question, saying `.\ros2.ps1 choose`.
  - The same retries, Ctrl-D and corrupt-file messages.
  - `EXPLAIN` from the environment or an `EXPLAIN=…` argument wins.
  - The terminal test is exactly `-not [Console]::IsInputRedirected -and -not
    [Console]::IsOutputRedirected`.
  - Each script reads the other's file; tested both ways.
- [x] 5. Docs:
  - `README.md`: one paragraph in Quick start, nothing else.
  - `docs/roadmap.md` Stage 2: pipeline stage 1 of 4 marked done on
    `native-recipes`; the macOS variant is now pixi and RoboStack; `pixi`
    added to the package-manager values. "Status" untouched.
  - `tests/host/README.md` (allowed) documents the pty runner and the copy
    rule.
  - `.gitignore` gains `.workstation/`.

Definition of Done:

- [x] Baseline `make lint` and `PWSH=… make check` on the unmodified base,
  recorded below: 288 tests, 40 failures (27 in `test_distros` plus the 13
  of item 0), 0 skipped, 155.7 s.
- [x] Final `make lint` passes. `scripts/explain-choice` is classified
  `python, host (3.9 grammar)`.
- [x] Final `PWSH=… make check`: 338 tests, exactly the 27 `test_distros`
  failures, 0 skipped (no `test_ros2_ps1` test skips), 153.0 s.
- [x] Budget for `make check`: final 153.0 s against a baseline of 155.7 s.
  Run back to back under the same load: base copy 160.3 s, branch 159.3 s.
  Within +10 s.
- [~] Budget for `python3 -m unittest discover -s tests/host -p
  'test_explain_choice.py'`, under 5 s: measured 4.92 s, 4.95 s and 5.27 s,
  with load average 4.7-5.5 throughout because stage 13 runs in parallel.
  Borderline; see Deviation 6.
- [x] Isolated `make selftest`: 48 passed, 0 failed, run once at the end.
  No `.workstation` afterwards. Image `ros2-tutorials-st07:latest` removed.
- [x] Item 0: the 13 subtests pass, and the negative control fails 7 of them.
- [x] Tests 1–22 present (map below). All eight mutations caught (table
  below). Verification 1–5 pass.
- [x] `grep -n "shell=True\|os.system" scripts/explain-choice` finds nothing
  (exit 1).
- [x] `git diff native-recipes --stat` shows only allowed files.

## Versions

- PowerShell 7.6.6: the portable `powershell-7.6.6-osx-arm64` build that
  attempt 1 unpacked at
  `/private/tmp/claude-502/-Users-durant-Repos-ds-ros2-classroom/e3623267-f0a1-48b5-a713-2a2021ccb28c/scratchpad/st07/ps/pwsh`
  (written `<scratchpad>/st07/ps/pwsh` below). Nothing installed
  system-wide.
- `python3` 3.12.0 (pyenv); `/usr/bin/python3` 3.9.6; GNU Make 3.81; Docker
  29.4.0 (OrbStack).

## Baseline gates (unmodified base `11c8a64`)

### `make lint` passes

```
$ make lint
docker compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: docker run --rm -v /Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-a06b12c5a1d81389f:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
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

### `PWSH=… make check`: 288 tests, 40 failures, 0 skipped, 155.7 s

Command: `env PWSH=<scratchpad>/st07/ps/pwsh /usr/bin/time -p make check`

```
python3 -m unittest discover -s tests/host
....................................................................................................................FFFFFFFFFFFF..FFFFFFFFFFFFF..FF.......................................................FFFFFFFFFFFFF.......................................................................................................
[failure tracebacks elided; the FAIL lines, verbatim:]
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
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port that is a string')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port with a fraction')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port written as a float')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port that is true')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='no port')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port below 1024')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port above 65535')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='two distributions sharing a port')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case="the self-test's port")
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a digest of the wrong shape')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a name of the wrong shape')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='no default')
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a default not in the table')
----------------------------------------------------------------------
Ran 288 tests in 155.701s

FAILED (failures=40)
make: *** [check] Error 1
real 155.97
user 56.98
sys 25.98
```

27 failures are in `test_distros`: expected, and stage 13's to fix. The other
13 are the subtests of
`SharedTableTests.test_both_refuse_every_malformed_table_alike` (item 0).
That is exactly the prompt's exemption, so the stage did not block.

## Final gates

### `make lint` passes

```
$ make lint
docker compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: docker run --rm -v /Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-a06b12c5a1d81389f:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
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
ok       scripts/explain-choice                python, host (3.9 grammar)
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
ok       tests/host/test_explain_choice.py     python, host (3.9 grammar)
ok       tests/host/test_open_url.py           python, host (3.9 grammar)
ok       tests/host/test_ros2_ps1.py           python, host (3.9 grammar)
ok       tests/host/test_run_quiet.py          python, host (3.9 grammar)
ok       tests/host/test_smoke_container.py    python, host (3.9 grammar)
ok       tests/host/test_uninstall.py          python, host (3.9 grammar)
ok       tests/host/test_workstation_help.py   python, host (3.9 grammar)
lint-scripts: 36 files: 36 ok, 0 advisory, 0 FAIL
```

### `PWSH=… make check`: 338 tests, 27 failures (all in `test_distros`), 0 skipped, 153.0 s

Command: `env PWSH=<scratchpad>/st07/ps/pwsh /usr/bin/time -p make check`

```
python3 -m unittest discover -s tests/host
....................................................................................................................FFFFFFFFFFFF..FFFFFFFFFFFFF..FF.................................................................................................................................................................................................................
[failure tracebacks elided; the FAIL lines, verbatim:]
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
----------------------------------------------------------------------
Ran 338 tests in 152.998s

FAILED (failures=27)
make: *** [check] Error 1
real 153.25
user 63.49
sys 26.82
```

Timing under the same load, back to back, load average about 5.5:

| Run | Tests | Time | Failures | Skipped |
|---|---|---|---|---|
| Base: a `git archive 11c8a64` copy in the scratchpad | 288 | 160.258 s | 40 | 1 (the copy has no `.git`) |
| Branch | 340 | 159.337 s | 27, all `test_distros` | 0 |

The branch run still had two `test_explain_choice` tests that I later removed
for the time budget.

### `test_explain_choice.py` alone

```
$ python3 -m unittest discover -s tests/host -p 'test_explain_choice.py'
Ran 35 tests in 5.265s   OK
Ran 35 tests in 4.945s   OK
Ran 35 tests in 4.924s   OK
```

## Item 0: trial and negative control

Trial, with `pwsh`:

```
$ PWSH=… python3 -m unittest discover -s tests/host -p test_ros2_ps1.py -k SharedTableTests -v
test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) ... ok
Ran 1 test in 9.745s
OK
```

All 13 subtests pass; they failed at baseline. The whole of
`test_ros2_ps1.py` passes (29 tests at base plus 8 new): under 3.12 in the
final `make check`, and under 3.9 (Verification 1).

Negative control: I changed `an integer from 1024 to 65535` to `… 65536` in
`ros2.ps1`'s port message only, leaving the comparison `-le 65535` alone.
The file was copied out, edited, and copied back, with SHA-256 checksums:

```
== N0 item 0 negative control: 65535 -> 65536 in ros2.ps1's port message
   file ros2.ps1  before 513b1107728ed67b  mutated 345ae8d048787ae9  restored 513b1107728ed67b  restored OK
   tests: -p test_ros2_ps1.py -k SharedTableTests  -> exit 1  Ran 1 test in 9.299s / FAILED (failures=7)
   failing subtests: 7
```

The 7 are the seven port cases: string, fraction, float, true, no port,
below 1024 and above 65535. That matches the coordinator's count.

## Tests 1–22

`tests/host/test_explain_choice.py` (35 tests):

| # | Test(s) |
|---|---|
| 1 | `AskOnceTests.test_the_question_word_for_word_then_2_saves_on` (also checks no temp file is left and nothing lands in the current directory); `test_the_question_fits_78_columns` |
| 2 | `AskOnceTests.test_1_and_enter_alone_save_off_and_spaces_are_ignored` |
| 3 | `AskOnceTests.test_an_answer_already_saved_means_no_question_and_no_output` |
| 4 | `AskOnceTests.test_three_unusable_answers_save_nothing`, `test_ctrl_d_means_option_1_for_now_and_saves_nothing`, `test_an_unusable_answer_then_a_usable_one_is_saved` |
| 5 | `AskOnceTests.test_ctrl_c_saves_nothing_and_exits_130_without_a_traceback` |
| 6 | `AskOnceTests.test_no_terminal_asks_nothing_and_saves_nothing` |
| 7 | `AskOnceTests.test_a_terminal_for_input_but_captured_output_is_no_terminal` |
| 8 | `AskOnceTests.test_explain_set_means_no_question_and_nothing_saved`, `test_explain_with_another_value_is_refused` |
| 9 | `ShowTests.test_off_when_nothing_is_saved`, `test_the_saved_answer`, `test_each_explain_value_beats_a_saved_answer`, `test_an_empty_explain_does_not`, `test_explain_with_another_value_names_the_three_accepted` |
| 10 | `ChooseTests.test_choose_shows_the_old_answer_and_replaces_it`, `test_choose_with_nothing_saved_says_so`, `test_choose_without_a_terminal_changes_nothing`, `test_choose_ctrl_d_keeps_the_old_answer` |
| 11 | `CorruptFileTests.test_show_says_so_in_one_line_and_prints_off`, `test_ask_once_says_so_asks_again_and_replaces_it`, `test_ask_once_without_a_terminal_says_so_and_leaves_it` (four corrupt cases each, as subtests) |
| 12 | `ErrorTests.test_an_unwritable_root_is_a_plain_message` (skips when run as root, and says why) |
| 13 | `ErrorTests.test_a_usage_error_is_exit_2` |
| 14 | `ShowTests.test_a_closed_output_pipe_is_no_traceback` (stdout is a pipe whose read end is closed before the script starts, so the failure is deterministic) |
| 15 | `MakefileTests.test_make_shell_asks_saves_then_runs_and_asks_only_once`; also `test_make_choose_replaces_the_answer`, `test_ctrl_c_at_the_question_stops_the_target`, `test_explain_on_the_command_line_means_no_question`, `test_no_terminal_runs_the_target_unasked_and_saves_nothing` |
| 16 | `MakefileTests.test_make_up_help_asks_nothing_and_runs_nothing`, `test_make_shell_help_prints_help_and_asks_nothing` |
| 17 | `MakefileTests.test_make_n_up_neither_asks_nor_saves` |

`tests/host/test_workstation_help.py`, additions only (class `ChooseRowTests`, 7 tests):

| # | Test(s) |
|---|---|
| 18 | `test_choose_is_the_last_line_of_start_here`, `test_first_run_is_not_listed`, `test_choose_is_not_marked`, `test_choose_help_prints_the_topic`, `test_choose_help_fits_a_terminal`, `test_choose_has_no_examples_and_says_so`, `test_examples_alone_does_not_offer_choose` |

`tests/host/test_ros2_ps1.py`, additions (class `FirstRunTests`, 8 tests, run under `PWSH`):

| # | Test(s) |
|---|---|
| 19 | `test_choose_on_a_pty_saves_what_explain_choice_saves` (byte-identical JSON, and explain-choice reads it); `test_a_file_explain_choice_wrote_is_read_by_ros2_ps1` (after which `up` does not ask); `test_desktop_asks_once_before_it_starts_anything` |
| 20 | `test_up_without_a_terminal_asks_nothing_and_runs_as_before` (docker argv: `info`, `compose pull --ignore-pull-failures`, `compose up -d`); `test_a_terminal_for_input_but_captured_output_is_no_terminal` |
| 21 | `test_explain_on_the_command_line_or_in_the_environment_means_no_question` |
| 22 | `test_a_corrupt_file_is_said_in_explain_choices_words_and_asked_again` (four cases; the words after the path are compared with explain-choice's own line); `test_a_corrupt_file_without_a_terminal_is_said_and_left_alone` |

`tests/host/fakes.py` gains `run_on_pty`. It is additive; nothing existing
changed. It provides:

- a controlling terminal for the child, through a `preexec_fn` that calls
  `os.setsid()` and then `TIOCSCTTY`;
- `wait()` for the child after EOF, rather than `poll()`;
- `\r\n` turned into `\n`;
- escape sequences stripped: colour, and pwsh's `\x1b[?1h\x1b=`.

## Mutations

Each mutation was applied to the working file, then the named test file was
run, then the file was restored by copying the saved copy back. SHA-256
values (first 16 hex digits) are recorded before, mutated and after. The
`explain-choice` mutations were rerun against the final 35-test file.

| Mutation | File | before | mutated | after | Tests run | Result | Caught by |
|---|---|---|---|---|---|---|---|
| M1 ask when only stdin is a terminal | `scripts/explain-choice` | 8d007eaff5c95f31 | 435c15f6f5a6faf9 | 8d007eaff5c95f31 | `test_explain_choice.py` | 1 failure | test 7 |
| M2 save on Ctrl-D (`return Explain.OFF`) | `scripts/explain-choice` | 8d007eaff5c95f31 | fcbbf7e1e38793ba | 8d007eaff5c95f31 | same | 2 failures | `test_ctrl_d_…`, `test_choose_ctrl_d_…` |
| M3 Enter is option 2 | `scripts/explain-choice` | 8d007eaff5c95f31 | 06622b282d9f6214 | 8d007eaff5c95f31 | same | 1 failure (1 subtest) | test 2 |
| M4 saved answer beats EXPLAIN (`--show`) | `scripts/explain-choice` | 8d007eaff5c95f31 | d35ff45d5b3e55c9 | 8d007eaff5c95f31 | same | 4 subtests | test 9, `test_each_explain_value_beats_a_saved_answer` |
| M5 swallow the corrupt-file message | `scripts/explain-choice` | 8d007eaff5c95f31 | fcb4b5b014cd31ba | 8d007eaff5c95f31 | same | 8 failures, 1 error | test 11 (all three) |
| M6 root from the current directory (`Path.cwd()`) | `scripts/explain-choice` | 8d007eaff5c95f31 | ee9b251628e8c71c | 8d007eaff5c95f31 | same | 16 failures, 4 errors | tests 1, 2, 3, 9, 10, 11, 12 and others |
| P1 ask when output is redirected | `ros2.ps1` | 513b1107728ed67b | def8004499a3a91d | 513b1107728ed67b | `-k FirstRunTests` | 1 failure | test 20, `test_a_terminal_for_input_but_captured_output_is_no_terminal` |
| P2 a different JSON key (`explained`) | `ros2.ps1` | 513b1107728ed67b | 063c3806528acd84 | 513b1107728ed67b | `-k FirstRunTests` | 7 failures | tests 19 (×3) and 22 |
| N0 item 0 negative control | `ros2.ps1` | 513b1107728ed67b | 345ae8d048787ae9 | 513b1107728ed67b | `-k SharedTableTests` | 7 subtests | item 0 |

After the mutations, `git status` showed only this stage's changes.

## Verification

### 1. Python 3.9

```
$ /usr/bin/python3 --version
Python 3.9.6
$ /usr/bin/python3 -m unittest discover -s tests/host
....................................................................................................................FFFF....FF..............................................................sssssssssssssssssssssssssssssssssssss..............................................................................................................
…
Ran 338 tests in 98.823s

FAILED (failures=27, skipped=37)
```

The 27 failures are the known `test_distros` ones. The 37 skips are the whole
of `test_ros2_ps1.py` (29 existing tests plus 8 new). This exact command does
not set `PWSH`, and there is no `pwsh` on PATH, so they skip with "pwsh
(PowerShell 7) is not installed; set PWSH to one". I ran the two affected
files again under 3.9 with `PWSH` set:

```
$ PWSH=… /usr/bin/python3 -m unittest discover -s tests/host -p 'test_[re][ox]*.py'
Ran 72 tests in 73.959s

OK
```

### 2. A real terminal, by hand

`script -q /dev/null make choose`, in a scratch copy of the branch's working
tree (`<scratchpad>/st07r2/branch-tree`, not the worktree). A short Python
script drove it and typed `2` once the prompt appeared:

```
$ cd branch-tree  # a scratch copy of the branch
$ script -q /dev/null make choose     # typing '2' at the prompt
Nothing is saved yet.

One question before we start. You will only be asked once.

  1. Just run things for me in the browser workstation.
  2. Do that, AND show me the commands that should do the same thing directly
     on my own system - no container involved.

Option 2 shows commands we think work on your system, each marked with how
well it has been checked. It is not a promise.
You can change your answer at any time with: make choose

Choose 1 or 2 [1]: 2
Saved: option 2. You can change it at any time with: make choose
[exit 0]
$ ./scripts/explain-choice --show
on
[exit 0]
$ cat .workstation/preferences.json
{"version": 1, "explain": "on"}
```

`ros2.ps1 choose`, through the tests' pty runner (`fakes.run_on_pty`), driven
from a short Python script in a second scratch copy, answering 2 and then 1:

```
$ pwsh -NoProfile -File ./ros2.ps1 choose     # on a pty, typing '2'
Nothing is saved yet.

One question before we start. You will only be asked once.

  1. Just run things for me in the browser workstation.
  2. Do that, AND show me the commands that should do the same thing directly
     on my own system - no container involved.

Option 2 shows commands we think work on your system, each marked with how
well it has been checked. It is not a promise.
You can change your answer at any time with: .\ros2.ps1 choose

Choose 1 or 2 [1]: 2
2
Saved: option 2. You can change it at any time with: .\ros2.ps1 choose
[exit 0]
$ ./scripts/explain-choice --show
on
$ cat .workstation/preferences.json
{"version": 1, "explain": "on"}
$ pwsh -NoProfile -File ./ros2.ps1 choose     # on a pty, typing '1'
Your current answer: option 2.

One question before we start. You will only be asked once.

  1. Just run things for me in the browser workstation.
  2. Do that, AND show me the commands that should do the same thing directly
     on my own system - no container involved.

Option 2 shows commands we think work on your system, each marked with how
well it has been checked. It is not a promise.
You can change your answer at any time with: .\ros2.ps1 choose

Choose 1 or 2 [1]: 1
1
Saved: option 1. You can change it at any time with: .\ros2.ps1 choose
[exit 0]
$ ./scripts/explain-choice --show
off
$ cat .workstation/preferences.json
{"version": 1, "explain": "off"}
```

The `2` appears twice because both the terminal and .NET echo it; see Open
question 3.

### 3. Nothing changed for the unasked

I saved the output of each of these, with stdin from `/dev/null`, in a
`git archive 11c8a64` copy and in a copy of the branch, run back to back:

- `make help`, `make engine`, `make doctor`, `make distros`;
- `make -n` of `up`, `shell`, `turtlesim`, `package PKG=x`, `build`,
  `run PKG=x NODE=y` and `test`.

```
$ diff -r v3-base v3-branch
diff -r v3-base/help.txt v3-branch/help.txt
20a21
>   make choose    Change your answer to the question asked the first time
diff -r v3-base/n-build.txt v3-branch/n-build.txt
0a1
> ./scripts/explain-choice --ask-once
diff -r v3-base/n-package.txt v3-branch/n-package.txt
0a1
> ./scripts/explain-choice --ask-once
diff -r v3-base/n-run.txt v3-branch/n-run.txt
0a1
> ./scripts/explain-choice --ask-once
diff -r v3-base/n-shell.txt v3-branch/n-shell.txt
0a1
> ./scripts/explain-choice --ask-once
diff -r v3-base/n-test.txt v3-branch/n-test.txt
0a1
> ./scripts/explain-choice --ask-once
diff -r v3-base/n-turtlesim.txt v3-branch/n-turtlesim.txt
0a1
> ./scripts/explain-choice --ask-once
diff -r v3-base/n-up.txt v3-branch/n-up.txt
0a1
> ./scripts/explain-choice --ask-once
```

The only differences are the `choose` line in `make help` and the
`first-run` recipe line in the `make -n` outputs. Neither copy gained a
`.workstation`.

### 4. The real suite, isolated

```
$ SELFTEST_PROJECT=ros2-tutorials-st07 SELFTEST_NOVNC_PORT=6097 SELFTEST_ROS_DOMAIN_ID=7 IMAGE_NAME=ros2-tutorials-st07 make selftest
./scripts/smoke-container
using: docker compose -p ros2-tutorials-st07  (isolated project; host port 6097)
…
== Result
48 passed, 0 failed

== cleaning up
```

Exit 0. It ran once, after every code change. Afterwards:

- `ls -a | grep -c workstation` in the worktree printed `0`.
- `docker image rm ros2-tutorials-st07:latest` printed
  `Untagged: ros2-tutorials-st07:latest` and `Deleted: sha256:57024ebf…`.
- Compose project `ros2-tutorials` was not touched.

### 5. Clean after `make check`

After the final `make check`, `git status --short` listed only this stage's
modified and new files, with no stray file, and `ls -a | grep -c workstation`
printed `0`. After the commit, `git status --short` is empty.

## Every message

### The question

This is `scripts/explain-choice`'s text. `ros2.ps1` prints the same, except
that it says `.\ros2.ps1 choose` where this says `make choose`.

```
One question before we start. You will only be asked once.

  1. Just run things for me in the browser workstation.
  2. Do that, AND show me the commands that should do the same thing directly
     on my own system - no container involved.

Option 2 shows commands we think work on your system, each marked with how
well it has been checked. It is not a promise.
You can change your answer at any time with: make choose

Choose 1 or 2 [1]:
```

### Other messages

Both scripts print these unless marked otherwise.

- `"<answer>" is not 1 or 2.`, then the question is asked again.
- `Using option 1 for now. Nothing was saved, so you will be asked again.`,
  after three unusable answers or after Ctrl-D (which first prints a
  newline).
- `Saved: option 1. You can change it at any time with: make choose`, or
  `option 2`. `ros2.ps1` says `.\ros2.ps1 choose`.
- `--choose` (or `choose`) first prints `Your current answer: option 1.` (or
  2), or `Nothing is saved yet.`, then a blank line and the question.
- `make choose asks a question, so it needs a terminal. Nothing was changed.`,
  exit 1. `ros2.ps1` says `.\ros2.ps1 choose asks a question, …`.
- `EXPLAIN=<value> is not understood. Use EXPLAIN=0, EXPLAIN=1 or EXPLAIN=only.`, exit 2.
- `<path>: the saved answer could not be read: <reason>; treating it as not saved.`
  `<reason>` is one of:
  - `it is not JSON`
  - `it is not an object with "version" and "explain"`
  - `its "version" is not 1`
  - `it has no "explain"`
  - `its "explain" is neither "off" nor "on"`
  - `it cannot be opened`
- `Could not save the answer in <path>: <system error>.`, exit 1.
  `ros2.ps1` prints `… <path>: <.NET exception message>`, exit 1.
- explain-choice only: usage on stderr, exit 2:
  ```
  usage: explain-choice --ask-once | --choose | --show
    --ask-once  ask the first-run question if it has never been answered
    --choose    ask it again, showing the current answer
    --show      print off, on or only
  ```
- explain-choice only: `--show` prints `off`, `on` or `only` and a newline.
- explain-choice only: Ctrl-C prints a newline and exits 130, with no
  traceback.
- `workstation-help`:
  - the overview row `make choose    Change your answer to the question
    asked the first time`;
  - the `make choose help` topic, below;
  - `make choose examples` refuses on stderr, exit 2:
    ```
    No examples for: choose
    Nothing was run.

      make choose help   says what it does
    ```

`make choose help`:

```
make choose -- change your answer to the first-run question

  The question
    The first time you run make up, make shell or another target that
    does something, you are asked whether to see, as well, the commands
    that should do the same thing directly on your own system, with no
    container involved.

  The two answers
    1  Just run things for me in the browser workstation.
    2  Do that, AND show me the native commands, each marked with how
       well it has been checked.

  make choose shows your current answer and asks again. Without a
  terminal to ask on, nothing is asked and nothing is saved.

  Where it is saved
    .workstation/preferences.json in this checkout. Nothing else reads
    or sends it.

  For one command only
    EXPLAIN=0      as answer 1
    EXPLAIN=1      as answer 2
    EXPLAIN=only   show the native commands without running anything
    e.g.  make build EXPLAIN=1
```

## Stat of the change, excluding this report

The files were staged first, so the new files are counted.

```
$ git diff --cached native-recipes --stat -- . ':!docs/stages/stage-07-REPORT.md'
 .gitignore                          |   3 +
 Makefile                            |  34 ++-
 README.md                           |  13 +
 docs/roadmap.md                     |  12 +-
 ros2.ps1                            | 159 ++++++++++++
 scripts/explain-choice              | 327 +++++++++++++++++++++++++
 scripts/workstation-help            |  53 +++-
 tests/host/README.md                |  22 ++
 tests/host/fakes.py                 | 110 +++++++++
 tests/host/test_explain_choice.py   | 470 ++++++++++++++++++++++++++++++++++++
 tests/host/test_ros2_ps1.py         | 196 ++++++++++++++-
 tests/host/test_workstation_help.py |  56 +++++
 12 files changed, 1439 insertions(+), 16 deletions(-)
```

## Deviations

1. The worktree's own branch was already at `11c8a64`. I ran
   `git fetch origin && git checkout -b stage-07-first-run-question-r2
   origin/native-recipes`; no merge was needed.
2. The sandbox refuses several plain command forms: shell variables,
   `python3 -m unittest` with a computed operand, and `pwsh` run directly. So
   I ran the tests through small Python wrappers in the scratchpad, which
   call `python3 -m unittest discover -s tests/host …` with `PWSH` set. The
   gates ran as `env PWSH=… /usr/bin/time -p make check`. The commands are
   the same; only the launcher differs.
3. Test 16, `make up help`: the prompt says it "prints help". With the base
   Makefile it prints the refusal "No extra help for: up … Nothing was run."
   and exits 2, because `up` has no help topic. The test pins that refusal,
   plus no question, no compose call and nothing saved. `make shell help` is
   pinned separately as the case that does print help.
4. `make choose examples` refuses (exit 2, "No examples for: choose / Nothing
   was run.") rather than printing something. The prompt only said "No
   examples topic". `examples` on its own still lists only the five targets
   that have both help and examples. Pinned by
   `test_choose_has_no_examples_and_says_so`.
5. My first try at Verification 2, `printf '2\n' | script -q /dev/null make
   choose`, saw end of input before the `2`: BSD `script` forwarded EOF as
   `^D`. So it took the Ctrl-D path ("Using option 1 for now. Nothing was
   saved"), and `--show` printed `off`. That is the specified behaviour. The
   transcript above types the answer only once the prompt is on screen.
6. Time budget for `test_explain_choice.py` alone: 4.92 to 5.27 s over three
   runs, against "under 5 seconds", with load average 4.7 to 5.5 throughout
   (stage 13 runs in parallel). Nearly all of the time is the Makefile tests,
   because each `make` parse starts four Python processes. To get this far I
   dropped three tests while iterating:
   - a separate current-directory test, folded into test 1;
   - `make choose help` through the Makefile, covered by test 18 and
     Verification 3;
   - a "`make distros` never asks" test, covered by Verification 3.

   It should be well under 5 s on an idle machine, but I have not measured
   one.
7. `make check` grew from 288 to 338 tests but measured faster: 153.0 s
   against 155.7 s, and 159.3 s against 160.3 s back to back. That is noise
   under load. All that can honestly be said is that it is within the budget,
   and the difference is smaller than the noise.
8. The ros2.ps1 tests' pty runs omit `-NonInteractive`, because a student's
   PowerShell must be able to ask; the existing piped runs keep it. ros2.ps1
   reads the answer with `[Console]::In.ReadLine()`, not `Read-Host`: I
   measured that `Read-Host` does not return on Ctrl-D, so it cannot detect
   end of input.
9. `[System.IO.File]::Replace(..., $null)` fails in PowerShell, which turns
   `$null` into `""`. The code uses `[NullString]::Value`, with a comment.
   Test 19 found it.
10. Messages beyond the prompt's list, all in plain words:
    - The corrupt-file reasons are a fixed set shared by both scripts
      (listed above).
    - A file that cannot be read for other reasons, such as permissions,
      gets the reason "it cannot be opened".
    - explain-choice prints the corrupt-file line on stderr, so `--show`
      stays one word on stdout. ros2.ps1 prints it on stdout, because
      `Write-Host` has no stderr.
11. With no terminal and a corrupt file, `--ask-once` prints the one-line
    corrupt-file message (to stderr) on every run. The ground rule's
    "byte-for-byte" covers an unasked student with no file. For a corrupt
    file I took the "never silently discarded" guardrail to win.
12. Extra tests beyond 1–22, all listed in the map: Ctrl-C through make,
    `EXPLAIN` on the make command line, `choose` through make, `desktop`
    asks once, and a corrupt file through `ros2.ps1` with no terminal.
13. The base copy I used for timing had 1 skipped test that the real base
    did not, because the copy has no `.git`. It is only a timing reference.
14. I ran mutations M1–M6 twice: first against a 37-test file, then against
    the final 35-test file. The table shows the second run; the failure
    counts were the same.

## Open questions

1. **Ctrl-C at ros2.ps1's question hangs under pwsh on macOS and Linux.** On
   a pty, `\x03` at `[Console]::In.ReadLine()` (and at `Read-Host`) printed
   `^C`, and the process kept waiting until it was killed. The prompt does
   not ask for Ctrl-C handling in `ros2.ps1`, and nothing is saved before an
   answer. But a pwsh user on Unix would have to press Enter or Ctrl-D. On
   Windows' console host Ctrl-C normally stops the script; I could not test
   that here.
2. **`desktop` asking once is only tested as far as `up`**, by making
   `docker info` fail. Past that point, `open` waits up to 60 s for a desktop
   and then calls `Start-Process`, which would open a real browser on this
   host. So the test stops `desktop` in its first step.
3. **The answer is echoed twice on a pty with pwsh** (`2`, then `2`): once by
   the terminal and once by .NET. It is cosmetic. I saw it only on a Unix
   pty and did not check a Windows console.
4. Every student target in the base Makefile is named in one of the prompt's
   two lists, so none is left without the question.
5. `make choose` with `EXPLAIN` set still asks and saves, because `EXPLAIN`
   only overrides the command it is given to. It could say so; the prompt
   does not specify this.
6. The 27 `test_distros` failures remain for stage 13, as instructed.
