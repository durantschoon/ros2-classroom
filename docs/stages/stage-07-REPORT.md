# Stage 07 — REPORT (BLOCKED)

## First step

`git log --oneline -1` in the worktree, before anything else (no merge was
needed; the worktree was already at the prompt's commit):

```
1cdff5f docs(stages): stage 07 prompt re-authored -- the first-run question, on native-recipes
```

`docs/stages/stage-07-PROMPT.md` was present. The worktree branch
`worktree-agent-af19fb4136a2021ba`, already at `1cdff5f` =
`origin/native-recipes`, was renamed in place with
`git branch -m stage-07-first-run-question`.

## BLOCKED

Blocking condition (the prompt's Blocked protocol, first bullet): **a gate
fails on the unmodified base other than the 27 known `test_distros`
failures.**

The Definition of Done's baseline gate is `make check` with
`PWSH=<scratchpad pwsh>`. On the unmodified base `1cdff5f` it fails with
**40** failures, not 27: the 27 known ones in `tests/host/test_distros.py`
plus **13 in `tests/host/test_ros2_ps1.py`**, which are all the subtests of
`SharedTableTests.test_both_refuse_every_malformed_table_alike`.

The coordinator measured its baseline (288 tests, 29 skipped, 27 failures)
*without* PowerShell, so the `test_ros2_ps1` tests skipped and these 13
never ran. With PowerShell they run, and they fail.

### Exact command and summary

```
$ PWSH=/private/tmp/claude-502/-Users-durant-Repos-ds-ros2-classroom/e3623267-f0a1-48b5-a713-2a2021ccb28c/scratchpad/st07/ps/pwsh make check
python3 -m unittest discover -s tests/host
....................................................................................................................FFFFFFFFFFFF..FFFFFFFFFFFFF..FF.......................................................FFFFFFFFFFFFF.......................................................................................................
[27 test_distros failure blocks, the known ones, omitted here]
----------------------------------------------------------------------
Ran 288 tests in 172.588s

FAILED (failures=40)
make: *** [check] Error 1
```

Failures by file: 27 in `test_distros` and 13 in `test_ros2_ps1`. Skipped: 0.

### The 13 failures outside the exemption, verbatim

```
FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port that is a string')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "jazzy" has no "port", an integer from 1024 to 65535

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port with a fraction')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "jazzy" has no "port", an integer from 1024 to 65535

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port written as a float')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "jazzy" has no "port", an integer from 1024 to 65535

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port that is true')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "jazzy" has no "port", an integer from 1024 to 65535

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='no port')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "jazzy" has no "port", an integer from 1024 to 65535

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port below 1024')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "humble" has no "port", an integer from 1024 to 65535

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a port above 65535')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "kilted" has no "port", an integer from 1024 to 65535

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='two distributions sharing a port')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "humble" and "jazzy" share port 6082

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case="the self-test's port")
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "kilted" has port 6081, which make selftest keeps for itself

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a digest of the wrong shape')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: "humble" has no "digest" of the form sha256:<64 hex digits>

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a name of the wrong shape')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: 'Jazzy 2' is not a distribution name

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='no default')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: missing "default", the name of the default distribution

FAIL: test_both_refuse_every_malformed_table_alike (test_ros2_ps1.SharedTableTests.test_both_refuse_every_malformed_table_alike) (case='a default not in the table')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba/tests/host/test_ros2_ps1.py", line 427, in test_both_refuse_every_malformed_table_alike
    self.assertTrue(script_err.startswith(prefix), script_err)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : /private/tmp/ros2-host-test-eu1dybf7/tree/distros.json: the default, "rolling", is not in "distros"
```

### Root cause (diagnosed, not fixed)

It is the same as the 27. On this host `TMPDIR=/tmp`, and `/tmp` is a symlink
to `/private/tmp`. `scripts/distros` resolves its own path and names
`/private/tmp/ros2-host-test-…/tree/distros.json`. The test builds its
expected prefix from `tempfile`'s unresolved `/tmp/ros2-host-test-…`, so
`startswith(prefix)` is false. The refusal messages themselves are correct.

As a read-only check, I ran the same gate with only the temp directory
changed, and everything passed:

```
$ TMPDIR=/private/tmp PWSH=/private/tmp/claude-502/-Users-durant-Repos-ds-ros2-classroom/e3623267-f0a1-48b5-a713-2a2021ccb28c/scratchpad/st07/ps/pwsh make check
python3 -m unittest discover -s tests/host
[dots elided]
----------------------------------------------------------------------
Ran 288 tests in 179.806s

OK
```

### Why each permitted path is closed

- **Fix the test.** `tests/host/test_ros2_ps1.py` is allowed for *additions
  only*. The failing assertion is in an existing test, and the executor
  contract ("never modify an existing test file") forbids changing it.
- **Fix the script.** The prefix comes from `scripts/distros`, which is not
  in the allowed files.
- **Count the 13 as part of the known 27.** The prompt's exemption is
  exactly "27 failures, all in `tests/host/test_distros.py`". The final DoD
  repeats "the same 27 `test_distros` failures, and no `test_ros2_ps1` test
  skips". PowerShell has to be present for no `test_ros2_ps1` test to skip,
  and with it present the final gate cannot meet that wording, whatever this
  stage does.
- **Run the gates with `TMPDIR=/private/tmp`.** That makes the gate pass.
  But it is not the gate command that the prompt and the README specify
  verbatim, and choosing it would mean improvising the exemption.

### What would unblock

Any one of these:

- The coordinator widens the exemption to "the 27 in `test_distros.py` plus
  the 13 subtests of `test_ros2_ps1.SharedTableTests`" (same root cause).
- The coordinator adds `TMPDIR=/private/tmp` to this host's gate commands.
- Stage 13's fix, which covers `test_distros.py`, is extended to
  `test_ros2_ps1.py` and merged into `native-recipes` first.

## Baseline gates (unmodified base `1cdff5f`)

Versions: GNU Make 3.81; `python3` 3.12.0; `/usr/bin/python3` 3.9.6;
PowerShell 7.6.6, the portable `powershell-7.6.6-osx-arm64.tar.gz` from GitHub
releases, unpacked into the scratchpad. Nothing was installed system-wide.

### `make lint` passes (4.4 s wall)

```
$ make lint
docker compose config --quiet && echo 'compose config: ok'
compose config: ok
./scripts/lint-scripts
shellcheck via: docker run --rm -v /Users/durant/Repos/ds/ros2-classroom/.claude/worktrees/agent-af19fb4136a2021ba:/mnt:ro -w /mnt docker.io/koalaman/shellcheck:v0.11.0
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
make lint  0.35s user 0.23s system 13% cpu 4.442 total
```

### `PWSH=… make check` fails: 288 tests, 40 failures, 0 skipped, 172.6 s

See BLOCKED above.

## Checklist echo

The change was not started; the stage blocked at the baseline gate.

- [ ] 1. `scripts/explain-choice`: not started
- [ ] 2. `Makefile`: not started
- [ ] 3. `scripts/workstation-help`: not started
- [ ] 4. `ros2.ps1`: not started
- [ ] 5. Docs: not started

Definition of Done:

- [x] Baseline `make lint`: recorded, passes.
- [x] Baseline `PWSH=… make check`: recorded. It **fails beyond the
  exemption (BLOCKED)**.
- [ ] Final gates, tests 1–22, mutations, Verification 1–5: not run.

## Stat

The commit contains only this report, `docs/stages/stage-07-REPORT.md`.

## Deviations

1. The worktree branch was renamed to `stage-07-first-run-question` in place.
   It was already at `origin/native-recipes` = `1cdff5f`, so no fetch or merge
   was needed.
2. Extra read-only diagnosis beyond the prompt: one full `make check` run
   with `TMPDIR=/private/tmp`, in which all 288 tests pass. It shows that the
   13 failures share the 27's root cause. It wrote nothing in the worktree:
   `git status` was clean afterwards and there was no `.workstation`.
3. PowerShell is 7.6.6, the latest release on 2026-10-01, fetched into
   `scratchpad/st07/ps/`.
4. `make check` with PowerShell took 172.6 s. The README says "about 79 s"
   with pwsh, and the prompt measured 71 s without it.

## Open questions

1. This sandbox's worktree guard refuses to run `pwsh` as a plain shell
   command ("cannot be shown not to run git"). It allowed `PWSH=… make
   check`, where Python starts pwsh. So an executor here may not be able to
   run Verification 2 (`script -q /dev/null pwsh ./ros2.ps1 choose`) as
   written. A Python pty driver started from the tests would work.
2. The question text says "make choose", and the prompt asks `ros2.ps1` to
   show the same question word for word. A Windows student would then be told
   `make choose`. This needs a decision before the re-run. ros2.ps1's help
   already says that every `make X` is `.\ros2.ps1 X` there.
3. `ros2.ps1 desktop` (the default command: `up`, then `open`) is not in the
   prompt's list of commands that ask first. It probably should ask, since it
   is what most Windows students run.
4. `scripts/workstation-help`'s overview uses the star or bold mark for
   "targets that have help *and* examples", and an existing test pins exactly
   five marked rows. `choose` gets help but no examples, so its row would stay
   unmarked.
