# Stage 06 report — Port the self-test to Python

Branch: `stage-06-port-the-selftest`. Base: `python-port` at
`bab77e197e73fdc69115b014ec5a60b817942208`.

`scripts/smoke-container` is now Python. It was the last file the roadmap's
"Language: Python replaces shell" listed, so `make lint` reports no
`shell, advisory` file at all.

## 1. Checklist echo

### The change

| Required | Done | Evidence |
|---|---|---|
| Ported in place: same file name, no `.py` extension | yes | the diff shows one modified path, not a rename |
| `#!/usr/bin/env python3` | yes | first line of the file |
| Executable bit kept | yes | `-rwxrwxr-x`; git records no mode change |
| `make selftest`, CI, and the docs need no change | yes | nothing else is in the diff; `make selftest` still runs `./scripts/smoke-container` |
| Stdlib only, Python 3.9-compatible | yes | imports are `os`, `signal`, `subprocess`, `sys`, `pathlib`, `typing`; Verification 2 runs on real 3.9 |
| Output byte for byte: banner, `== <step>`, `  PASS`/`  FAIL` with their colour escapes, `N passed, M failed`, `failed checks:`, `== cleaning up`, the `--keep` hint | yes | Verification 1 diffs a real run against the base: no difference |
| Step titles and check names match `HAPPY_TRANSCRIPT` exactly, in order | yes | `test_the_ordered_transcript_is_what_stage_06_must_reproduce`, `test_the_step_titles_are_in_this_order`, `test_the_check_names_are_in_this_order` |
| `COMPOSE` gains `-p <project>` and is exported | yes | `ProjectIsolation` (7 tests) |
| `NOVNC_PORT` and `ROS_DOMAIN_ID` exported with their `SELFTEST_*` overrides | yes | `PortIsolation`, `RosGraphIsolation` (10 tests) |
| `IMAGE_NAME` / `ROS_DISTRO` name the image | yes | `EngineDetection.test_the_engine_is_used_to_inspect_the_image_by_name` |
| Cleanup on success, failure, early abort, Ctrl-C and SIGTERM; `--keep` suppresses all of them | yes | `Cleanup` (5), `KeepFlag` (5), Verification 5 |
| `try`/`finally` plus handlers turning SIGTERM and SIGHUP into an orderly exit | yes | `main()`'s `try/except/finally`; `die_on_signal` installed for both |
| Exit status 0 only when every check passed | yes | `step_result` returns 1 whenever `failed > 0` |
| Every wait runs `sleep`, every HTTP probe runs `curl`; no `time.sleep`, no `urllib` | yes | `Suite.wait` shells out to `sleep`; both curl probes are argv lists; the DoD grep finds nothing |
| Python's stdout flushed before any child starts | yes | `Suite.run` flushes first, and is the only place a child is started |
| The Xvfb ownership check still waits for Xvfb to exist, up to 30 tries | yes | `XVFB_TRIES = 30`, the loop in `step_image_and_environment` |
| Each check's verdict is a pure function of the command's result, separate from running it | yes | the "pure core" section: `contains`, `starts_a_line`, `has_line`, `tail`, `grep_last`, `first_field`, `squeezed_first_line`, `spaces_for_newlines`, `substitution`, `here_lines`, `image_reference` |
| Commands are argv lists; container snippets are single ordinary arguments | yes | `compose_argv` / `desktop_argv`; `BUILD_SCRIPT`, `BROKEN_TEST_SCRIPT`, `UPSTREAM_SCRIPT` each travel as one argument |
| No `shell=True`, no `os.system` | yes | the DoD grep |
| An expected failure is a FAIL line or a message, never a traceback — including a closed pipe | yes | `Abort` for control flow, no bare `except`, `OSError` handled where children start; Verifications 5 and 6 |
| One self-contained file; a script, not a `unittest` suite | yes | no imports from the repository, no `unittest` |

### Behaviour change 1 — a missing engine is a failed check

| Required | Done |
|---|---|
| The check FAILs with the name `no container engine found to inspect the image` | yes |
| The suite carries on with the remaining checks | yes — `== Turtlesim` through `== Persistence across container recreation` still run |
| Summary, `failed checks:` list, exit 1 and cleanup happen as for any other failure | yes |
| `EngineDetection`: `test_a_missing_engine_aborts_the_suite_with_no_summary` replaced, class docstring updated | yes — §5 |
| `test_a_missing_engine_still_cleans_up` and `test_the_engine_is_used_to_inspect_the_image_by_name` unchanged | yes — untouched in the diff |

### Behaviour change 2 — nothing is written to the host's `/tmp`

| Required | Done |
|---|---|
| The two `pkg new … --build` logs are captured in memory | yes — `out="capture", err="merge"` |
| A failing check prints the last five lines, indented, under its FAIL line | yes — `Suite.show_tail` |
| Nothing is written on the host | yes — no host-side redirection remains |
| `Housekeeping`: `test_it_writes_two_log_files_into_the_hosts_own_tmp` replaced by two tests | yes — §5 |
| No other test changed | yes — the test diff is those two replacements plus the fixture the new test needs |

### Definition of Done

| Item | Result |
|---|---|
| Baseline on the unmodified base: `make lint`, `make check` (162), one real `make selftest` (48/48) | done — §2 |
| Final `make lint` passes, `scripts/smoke-container` classified `python, host (3.9 grammar)` | done — §2 |
| Final `make check` passes under 30 s; count is 162 − 2 + 3 = 163 | done — 163 tests in 26.5 s (28.0 s wall); the margin is thin, see §9.3 |
| Final real `make selftest` passes 48/48 | done — §2, §3 |
| Verifications 1–7 pass, with output in the report | done — §3 |
| The `shell=True` / `os.system` / `time.sleep` / `urllib` grep finds nothing | done — §3 |
| `git diff python-port --stat` shows only allowed files | done — §7 |

## 2. Gates, baseline and final

### `make lint`

Baseline, on the unmodified base `bab77e1` — 26 files, the last shell one still
listed:

```
ok       scripts/run-quiet                     python, host (3.9 grammar)
ok       scripts/smoke-container               shell, advisory
ok       scripts/workstation-help              python, host (3.9 grammar)
…
lint-scripts: 26 files: 26 ok, 0 advisory, 0 FAIL
```

Final:

```
ok       scripts/run-quiet                     python, host (3.9 grammar)
ok       scripts/smoke-container               python, host (3.9 grammar)
ok       scripts/workstation-help              python, host (3.9 grammar)
…
lint-scripts: 26 files: 26 ok, 0 advisory, 0 FAIL
```

No file is classified `shell, advisory` any more. The three remaining shell
files — `docker/entrypoint.sh`, `docker/desktop/openbox-autostart`,
`docker/bashrc.d/ros-workspace.sh` — stay shell on purpose and are `enforced`.

### `make check`

| | Baseline | Final |
|---|---|---|
| command | `python3 -m unittest discover -s tests/host` | same |
| tests | `Ran 162 tests in 20.669s` | `Ran 163 tests in 26.460s` |
| result | `OK (skipped=4)` | `OK (skipped=4)` |
| wall clock | 20.9 s | 28.0 s |

Both figures are from the exact files being committed. Arithmetic:
162 − 2 replaced + 3 replacing = **163**. The 4 skips are the `open-url` tests
that skip on WSL by design, in both runs.

The ~6 s gained is two extra whole runs of `scripts/smoke-container` against
the fakes: each new `Housekeeping` test uses a scenario no other test shares,
so neither can pass on a cached run. That leaves under 2 s of headroom against
the 30 s the Definition of Done allows — read §9.3 before merging.

### `make selftest`

| | Baseline (shell) | Final (Python) |
|---|---|---|
| verdict | `48 passed, 0 failed` | `48 passed, 0 failed` |
| exit | 0 | 0 |

## 3. Verifications

### 1. The transcript, against the real system

Both sides are the `== ` and `PASS`/`FAIL` lines of a real `make selftest`,
colour stripped: 62 lines each — 13 step titles, 48 checks, and the
`== cleaning up` the cleanup path prints.

```
$ diff baseline-transcript.txt final-transcript.txt
$ echo $?
0
```

**No difference.**

### 2. Python 3.9 for real

```
$ podman run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo \
      docker.io/library/python:3.9-slim python -m unittest discover -s tests/host
.......................................................................ssss.................ssssssssssssssssssssssssssssssssssssssssssssssssssssss.................
----------------------------------------------------------------------
Ran 163 tests in 5.618s

OK (skipped=58)
```

The 58 skips, by reason:

| Count | Reason | Why |
|---|---|---|
| 49 | `scripts/smoke-container is bash and drives the real Makefile; this machine is missing make` | every test in `test_smoke_container.py`. `python:3.9-slim` has no `make`, and the suite's "Student make targets" step runs the real Makefile, so `MISSING_TOOLS` skips the class. Not caused by the port: the same 49 skipped here before it |
| 5 | `make is not installed` | the `workstation-help` and `compose-up` tests that shell out to `make` |
| 4 | the `open-url` WSL skip | `/proc/version` inside the container is still the WSL kernel's |

105 tests really ran on 3.9 and passed. `scripts/smoke-container` itself is
parsed against the 3.9 grammar by `make lint` on every run
(`python, host (3.9 grammar)`).

### 3. The suite still catches a real break

`docker/templates/cpp/pubsub/src/talker.cpp`, `hello from` → `greetings from`,
then a full `make selftest` on the ported suite:

```
  FAIL templated pubsub node did not publish on /chatter
== Result
47 passed, 1 failed
failed checks:
  - templated pubsub node did not publish on /chatter

== cleaning up
make: *** [Makefile:252: selftest] Error 1
```

**47 passed, 1 failed, failing exactly `templated pubsub node did not publish
on /chatter`** — the same verdict the coordinator measured from the shell suite
before this stage started.

Reverted by copy-back, not `git checkout --`:

```
$ md5sum docker/templates/cpp/pubsub/src/talker.cpp
1a0815af75be808551edd8d108d1cb6c  docker/templates/cpp/pubsub/src/talker.cpp
expected: 1a0815af75be808551edd8d108d1cb6c
```

### 4. Mutations of the port

Five mutations of the Python file, each applied by exact string replacement,
each reverted by copy-back from a pristine copy and confirmed with md5. The
pristine md5 throughout was `247fceb6901591b1c2da713fd5cadc61`; every restore
matched it exactly, and the runner refused to start a mutation unless the file
matched it first.

| # | Mutation | Tests run | Caught by |
|---|---|---|---|
| 1 | `compose_text = "{} -p {}".format(base, project)` → `compose_text = base` — the isolated project is dropped | `ProjectIsolation` | 6 of 7 failed, incl. `test_every_compose_call_carries_the_selftest_project` and `test_the_exported_compose_already_carries_the_project_flag` |
| 2 | a check is renamed: `"ros2 is on PATH"` → `"ros2 is on the PATH"` | `HappyPath` | `test_the_ordered_transcript_is_what_stage_06_must_reproduce`, `test_the_check_names_are_in_this_order` |
| 3 | the teardown loses `-v`: `["down", "-v", "--remove-orphans"]` → `["down", "--remove-orphans"]` | `Cleanup` | 4 of 5 failed, incl. `test_the_teardown_deletes_volumes_only_inside_the_selftest_project` |
| 4 | `EXEC_TRIES = 30` → `EXEC_TRIES = 5` | `Readiness` | `test_it_gives_up_rather_than_retrying_forever` |
| 5 | behaviour change 1 undone: `suite.bad("no container engine found to inspect the image")` → `raise Abort(1)` | `EngineDetection` | `test_a_missing_engine_fails_one_check_and_the_run_carries_on` |

All five were caught; none is one of stage 05's five, and mutations 2 and 5
have no shell counterpart at all.

### 5. Ctrl-C and SIGTERM clean up

Run against the fakes with the **real** `sleep` on the sandbox PATH, so the
Xvfb wait loop gives a window; the signal is delivered 4 s in, mid-run.

```
--- SIGINT: sending SIGINT to pid 861283 after 4s
exit status: 130
last 4 lines of stdout:
    | == Image and environment
    |   PASS the image defaults to the non-root ros user
    |
    | == cleaning up
stderr: ''
traceback in output: False
last compose call: ['-p', 'ros2-tutorials-selftest', 'down', '-v', '--remove-orphans']
teardown seen: True

--- SIGTERM: sending SIGTERM to pid 861299 after 4s
exit status: 143
last 4 lines of stdout:
    | == Image and environment
    |   PASS the image defaults to the non-root ros user
    |
    | == cleaning up
stderr: ''
traceback in output: False
last compose call: ['-p', 'ros2-tutorials-selftest', 'down', '-v', '--remove-orphans']
teardown seen: True
```

The fake compose received `down -v --remove-orphans` as its last call in both
cases, and nothing printed a traceback.

### 6. A closed pipe

```
--- closed pipe: scripts/smoke-container --keep | head -3
head -3 saw:
    | using: compose -p ros2-tutorials-selftest  (isolated project; host port 6081)
    |
    | == Build
suite exit status: -13 (negative means killed by that signal)
stderr: ''
traceback in stderr: False
BrokenPipeError mentioned: False
```

Signal 13 is `SIGPIPE`: the run ends the way the shell version ended, because
`main` installs `signal.SIG_DFL` for `SIGPIPE` — the same line
`scripts/compose-command` already used for the same reason.

### 7. `make lint` reports no `shell, advisory` file

```
lint-scripts: 26 files: 26 ok, 0 advisory, 0 FAIL
```

The only labels present are `bash (sourced), enforced`, `shell, enforced`,
`python, container` and `python, host (3.9 grammar)`.

### The Definition of Done's grep

```
$ grep -n "shell=True\|os.system\|time.sleep\|urllib" scripts/smoke-container
$ echo $?
1
```

Nothing found.

## 4. Line counts

| | Lines |
|---|---|
| `scripts/smoke-container` before (bash) | 507 |
| `scripts/smoke-container` after (Python) | 945 |

It grew by 438 lines without gaining a single check. Where they went: about 90
lines of docstrings (the shell's 60 lines of comments are all kept as well);
13 named step functions with signatures and separating blank lines, where the
shell had bare top-level code; a `Suite` class whose small methods replace four
one-line shell helpers; a pure-core section of twelve functions that did not
exist because the shell delegated all of it to `grep`, `tail`, `awk`, `tr` and
`head`; and the line breaking that a 96-column style imposes on argv lists that
used to be single shell words. The executable part is roughly 600 lines.

## 5. The exact test edits

Only the two replacements the prompt authorises, plus the one fixture the
second new test needs.

### `EngineDetection`

The class docstring, which described the `set -e` death as pinned-but-not-
endorsed, is replaced by one describing the new behaviour, and
`test_a_missing_engine_aborts_the_suite_with_no_summary` is replaced by
`test_a_missing_engine_fails_one_check_and_the_run_carries_on`. It asserts:
exit 1; `== Image and environment` reached; the new FAIL name present; that
`== Turtlesim` and `== Persistence across container recreation` still ran; that
the summary line is printed and agrees with the PASS/FAIL lines; that the new
name appears in the `failed checks:` list; and that `compose-command`'s
`no working docker or podman compose found` still reaches stderr.

`test_a_missing_engine_still_cleans_up` and
`test_the_engine_is_used_to_inspect_the_image_by_name` are untouched.

### `Housekeeping`

`test_it_writes_two_log_files_into_the_hosts_own_tmp` is replaced by:

* `test_a_run_writes_no_log_files_into_the_hosts_own_tmp` — removes both paths
  first, then runs the scenario `no_host_tmp_writes`, which no other test uses,
  so a cached run cannot make it pass by accident, then asserts that neither
  file exists.
* `test_a_failing_pkg_new_shows_the_tail_of_its_output` — a compose rule makes
  `pkg new pkg_smoke_pubsub --template pubsub --build` fail with seven lines of
  output, and the test asserts that the five lines printed under the FAIL line
  are lines 3–7, each indented by four spaces.

The fixture `PUBSUB_BUILD_FAILS` was added beside the other rule sets, for the
second test. `SESSION_START` and the `time` import, which only the removed test
used, were deliberately **left in place** so the test file's diff stays at the
two authorised replacements; see §9.

## 6. Every place the output differs from the shell suite's

On the pinned transcript and on a real 48/48 run there is **no difference at
all**: Verification 1 diffs them and finds none, and
`test_the_ordered_transcript_is_what_stage_06_must_reproduce` compares all 62
entries. Every difference is outside that transcript.

1. **A missing engine (intended — behaviour change 1).** The shell printed
   `== Image and environment` and then died under `set -e`: no PASS/FAIL line
   for the image user, no further steps, no `N passed, M failed`, no
   `failed checks:`. The port prints
   `  FAIL no container engine found to inspect the image`, runs the remaining
   eleven steps, and prints the summary and the list. `compose-command`'s own
   stderr line is unchanged in both.

2. **A failing `pkg new … --build` (intended — behaviour change 2).** The shell
   printed only the FAIL line and dropped the command's output into
   `/tmp/pkg-smoke-pubsub.log` and `/tmp/pkg-smoke-msgs.log` on the host. The
   port prints up to five extra lines under the FAIL line, each indented four
   spaces, and writes no host file. On a passing run there is no visible
   difference: both discard the output.

3. **Exit status after Ctrl-C (unintended, strictly better, disclosed).**
   Measured on this host rather than assumed: bash ran its `EXIT` trap on
   SIGINT, SIGTERM and SIGHUP alike, so cleanup was never the problem — but on
   SIGINT the trap saw `$? = 0`, and the shell suite therefore **exited 0**
   after an interrupted run. The port exits 130. For SIGTERM and SIGHUP the
   shell re-raised the signal after its trap, which a waiting shell reports as
   143 and 129; the port exits 143 and 129 normally, which is what `$?` shows
   either way. Only the SIGINT status changes, from "success" to "interrupted".

4. **A host missing `curl`, `sleep` or `make` (unreachable on a working host).**
   bash printed `scripts/smoke-container: line N: curl: command not found` on
   stderr; the port prints `curl: No such file or directory`. The check fails
   identically (status 127) either way, and the wording only differs on a host
   that cannot run the suite at all.

Nothing else. The colour escapes (`\033[32m`, `\033[31m`), the two spaces in the
banner, the two-space indent on PASS/FAIL lines, the blank line before every
`== ` title, the `  - ` bullets in the failure list, and the `--keep` hint are
character-identical, and the tests assert them as such.

## 7. `git diff python-port --stat`

```
 scripts/smoke-container            | 1354 ++++++++++++++++++++++++------------
 tests/host/test_smoke_container.py |   79 ++-
 2 files changed, 958 insertions(+), 475 deletions(-)
```

Both are on the allow-list; `docs/stages/stage-06-REPORT.md` is new in the same
commit. Nothing under `docker/` changed, no other script changed, and
`tests/host/fakes.py` is untouched.

## 8. Deviations

1. **The worktree was created at a stale commit, for the fifth stage running.**
   `git log --oneline -1` gave `cca3884 docs(roadmap): record where the project,
   image, and videos live`, and `docs/stages/` did not exist at all. Followed
   the prompt's "First step": `git fetch origin && git merge --ff-only
   origin/python-port` brought the worktree to `bab77e1`, after which the prompt
   file was present.

2. **Branch renamed, not created**: `git branch -m stage-06-port-the-selftest`
   from the harness-generated `worktree-agent-a129fc304e2ba9bd3`, so no nested
   worktree was made.

3. **A `Co-Authored-By:` trailer** is on the commit, under standing
   instructions. The README's retro section says that is expected rather than a
   deviation; noted for completeness.

4. **One module-level fixture was added to the test file** beyond the two
   replacements: `PUBSUB_BUILD_FAILS`, the compose rule the new
   `test_a_failing_pkg_new_shows_the_tail_of_its_output` needs. It belongs to
   that replacement, but the prompt did not spell it out.

5. **Three real `make selftest` runs, not two.** The first 48/48 run was made
   before I noticed that a docstring in `Suite.wait` contained the literal
   string `time.sleep` and so tripped the Definition of Done's grep. I reworded
   the docstring — a comment-only change with no executable effect — and then
   re-ran both the negative control and a clean `make selftest`, so that every
   number in §2 and §3 comes from the exact file being committed. The first
   run's transcript was byte-identical to the final one's.

6. **Extra read-only verification beyond the prompt**, which the README invites:
   * measured what bash actually did with `trap cleanup EXIT` under SIGINT,
     SIGTERM and SIGHUP rather than assuming it, which is where difference 3 in
     §6 comes from;
   * ran the whole of `test_smoke_container.py` against the ported script
     *before* touching either test, confirming that exactly the two tests the
     prompt authorises replacing were the only ones that had to change — 46 of
     48 passed unmodified;
   * checked the classification of every file in `make lint`, not only
     `scripts/smoke-container`.

7. **`/tmp/pkg-smoke-pubsub.log` and `/tmp/pkg-smoke-msgs.log` were deleted from
   this host's `/tmp`** by the new `Housekeeping` test, as its design requires.
   They were the shell suite's own litter; nothing else reads them.

## 9. Open questions

Noticed, and deliberately not done.

1. **`NEEDS_TOOLS` in `test_smoke_container.py` still says "scripts/smoke-
   container is bash"**, and `REAL_TOOLS` still links `grep`, `tail`, `head`,
   `tr`, `awk` and `dirname` "for" a script that no longer spawns any of them —
   `make` is the one that really gates the class now. Correcting the reason
   string and pruning `REAL_TOOLS` would change tests the prompt did not
   authorise, so both are left alone. Worth a small follow-up: that skip reason
   is the first thing a contributor on a thin machine reads.

2. **`SESSION_START` and the `time` import are now dead** in
   `test_smoke_container.py` — only the replaced test used them — and the
   comment above `SESSION_START` still describes the redirections this stage
   removed. Left in place to keep the test diff to the two authorised
   replacements.

3. **`make check` went from 20.7 s to 26.5 s — the thinnest result here.** It
   is inside the 30 s the Definition of Done allows, but only by about 3.5 s on
   an idle machine (28.0 s of wall clock against 30), and a reviewer re-running
   it on a loaded machine could see it miss. The cost is the two extra whole
   runs of the suite against the fakes that stop the new tests passing on a
   cached scenario. Three ways out, none of which an executor should pick:
   * let the two new `Housekeeping` tests share one scenario, with the file
     removal hoisted into a `setUpClass` so it still provably precedes the run
     — saves about 2 s, at the cost of a third edit to a file the prompt
     limited to two replacements;
   * shorten the 30-iteration Xvfb wait loop, in which every one of the
     thirteen scenarios spends about a second calling a fake that will never
     answer — but that means the script reading a test-only environment
     variable, which guardrail 1 would call a new flag on the surface;
   * raise the budget, now that one `make check` really does run the whole
     self-test suite thirteen times over.

4. **`COMPOSE` is split on whitespace, not word-split by a shell.** bash
   expanded `$COMPOSE` unquoted, which also glob-expanded it; the port uses
   `str.split()`. For every value this project produces — `docker compose`,
   `podman compose`, `podman-compose` — the two agree exactly, and losing glob
   expansion removes a quoting hazard rather than adding one. Still a behaviour
   difference in the input, and nothing tests it.

5. **The readiness give-up path still exits without a summary.** It is preserved
   exactly, and `Cleanup.test_an_early_abort_still_removes_the_project` pins it
   — but it is the same "stops counting" shape that behaviour change 1 has just
   removed from the engine path. Making it print a summary too would be a second
   user-visible change, so it was not done.

6. **`Suite.run` takes its stream disposition as strings** (`"inherit"`,
   `"capture"`, `"null"`, `"merge"`). Guardrail 1 would rather that were an
   enum. It is internal to one file and never crosses a boundary, so I left it
   readable rather than adding a fourth enum; a reviewer may reasonably differ.

7. **The `pkg new --interfaces` check shows its tail as well.** Behaviour change
   2 names both redirections, but the test the prompt specifies covers only the
   pubsub one. Both are implemented; only the pubsub one is pinned by a test.

8. Everything still open from the stage 05 report is still open; nothing here
   touched the backlog in `docs/stages/README.md`.
