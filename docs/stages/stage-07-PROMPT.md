# Stage 07 — The first-run question

Branch name for this stage: `stage-07-first-run-question-r2`. Base: `native-recipes`.

**Attempt 2.** Attempt 1 (`f4662ad`, branch `stage-07-first-run-question`)
blocked cleanly at its baseline: with PowerShell present, 13 more failures
than this prompt exempted, in `tests/host/test_ros2_ps1.py`. The coordinator
measured the baseline without `pwsh`, so they were skipped; that was the
coordinator's error, not the executor's. Revised below: item 0 is new, the
exemption, Verification 2, the `ros2.ps1` question text, and `desktop` are
corrected. Leave attempt 1's branch alone; link its report from yours.

Re-authored 2026-10-01. The first version of this prompt (`6127cee`, on
`native-commands`) was written for the pre-v1.0 history and a WSL host and was
never run. This version is canonical; do not read the old one.

Read `docs/stages/README.md` first: its gates, environment facts (the host is
now macOS), guardrails, "Added by the retro before stage 05", "Added after
v1.0", and "Plan for roadmap Stage 2", including the user's pixi decision
under it. Then read `docs/roadmap.md`, "Stage 2 — What you would have run": it
is the specification this stage begins.

**First step, before anything else.** Run `git log --oneline -1` and **put that
line in your report**. If `docs/stages/stage-07-PROMPT.md` is missing, run
`git fetch origin && git merge --ff-only origin/native-recipes` and record it
as a Deviation. If the file is still missing, invoke the Blocked protocol.

## Motivation (measured)

The repository's principle is convenience without a black box
(`docs/roadmap.md`). Roadmap Stage 2 will print, before each target runs, the
commands that would do the same thing natively on the student's own system. The
user has decided that a student opts into that, once, at the very beginning,
and is never asked again.

This stage builds only the question, its saved answer, and the way to change
or override it. It prints no native command: the recipes arrive in stages 08
to 10, and this work sits on the integration branch `native-recipes` until
they do, so that `main` never offers a choice that does nothing.

The coordinator prototyped the approach on this host (macOS, GNU Make 3.81 at
`/usr/bin/make`, Python 3.12 and the system's 3.9.6) before writing this
prompt, as the retro requires:

- A prerequisite target whose recipe runs a Python script **can** ask on the
  student's terminal and read the answer: under a pty, `make up` printed the
  question, accepted `2`, saved it, then ran `up`'s own recipe. Run again, it
  did not ask.
- `make -n up` printed the prerequisite's recipe line and ran nothing.
- With stdin not a terminal (`make up </dev/null | cat`), a script that checks
  `sys.stdin.isatty() and sys.stdout.isatty()` did not ask, did not block, and
  saved nothing. That matters: `scripts/smoke-container` runs `make package`,
  `make build`, and `make test` with stdout captured, and must never stop to
  ask.
- make exports command-line variables to recipes: `make up EXPLAIN=only`
  showed `EXPLAIN=only` inside the recipe.
- **Ctrl-C needs a controlling terminal.** A child started with plain
  `subprocess.Popen` on a pty's slave end never turns `\x03` into SIGINT and
  hangs at the prompt. With a `preexec_fn` that calls `os.setsid()` and then
  `fcntl.ioctl(0, termios.TIOCSCTTY, 0)`, the same keystroke made the child
  exit 130. Measured under both 3.12 and `/usr/bin/python3` (3.9.6).
- **macOS trap, new on this host.** Reading the master end returns `b""` (EOF)
  slightly *before* the child has exited, where Linux raises `EIO`. The
  coordinator's first probe called `poll()` right after EOF and reported a
  false hang. A pty runner must `wait(timeout=…)` for the child after EOF, not
  `poll()`. Output read from the master has `\r\n` line endings.
- **The `ros2.ps1` parity rule.** `tests/host/test_ros2_ps1.py` takes every
  student target from `scripts/workstation-help`'s overview and fails if
  `ros2.ps1 <target> help` says "Unknown command". So a `make choose` listed in
  `make help` must exist in `ros2.ps1` too. Those tests skip without
  PowerShell 7; this host has none installed (see Tests).
- **Baseline at `1cdff5f`, with PowerShell** (attempt 1, confirmed by the
  coordinator): `PWSH=… make check` ran 288 tests in about 173 s, 0 skipped,
  **40 failures**, all from a `/tmp` -> `/private/tmp` symlink this host has
  and Linux CI has not:
  - **27 in `tests/host/test_distros.py`.** Stage 13 fixes them on
    `multi-distro`, in parallel with you. They are expected in your baseline
    and final runs; you must not fix them (not in your allowed files).
  - **13 subtests of `SharedTableTests.test_both_refuse_every_malformed_table_alike`
    in `tests/host/test_ros2_ps1.py`.** Yours to fix, item 0.
  Re-measure; do not copy these numbers.

## The change

### 0. `test_both_refuse_every_malformed_table_alike` on macOS (attempt 2)

The test asserts that `scripts/distros` and `ros2.ps1` refuse each malformed
table in the same words. On this host they name the table differently:
`scripts/distros` the resolved path (`/private/tmp/…`, from
`Path(__file__).resolve()`), `ros2.ps1` the unresolved one (`/tmp/…`, from
`$PSScriptRoot`). Resolving the test's expected path is **not** enough; the
coordinator tried it, and the second assertion (the two outputs equal) still
failed 13 times. Both scripts are right to name the file; the spelling of a
symlinked path is not what the test guards.

Change the test, not the scripts: split each output at its first `": "`;
assert with `os.path.samefile` that each script's path names the table the
test wrote; assert the words after the path are equal; keep the status and
one-line checks. The coordinator's trial of exactly this passed 29/29 with
`pwsh`, and a negative control (changing `65535` to `65536` in `ros2.ps1`'s
port message) failed 7 subtests. Repeat both (the negative control by
copy-out and copy-back with a checksum) and report them. Add a comment in the
test saying why.

### 1. `scripts/explain-choice` (new)

A host script: **stdlib only, Python 3.9-compatible**, `#!/usr/bin/env python3`,
no `.py` extension, executable. It has exactly three modes, a closed `Enum`
parsed once at the entry point. Anything else is a usage error: exit 2, usage
on stderr.

**`--ask-once`** — what the student targets run first.

1. If the environment variable `EXPLAIN` is set and non-empty: validate it (see
   `--show`) and exit without asking. Whoever set it has already decided.
2. Else if an answer is saved: exit 0, silently.
3. Else if stdin **and** stdout are both terminals: ask, save the answer, and
   confirm it.
4. Else: exit 0, silently, and **save nothing**, so the student is asked the
   first time they do have a terminal.

**`--choose`** — what `make choose` runs. Shows the current answer when there
is one, asks the same question, saves, and confirms. Without a terminal: a
plain message that it needs one, exit 1, nothing changed.

**`--show`** — for the later stages' use. Prints exactly one word and a
newline: `off`, `on`, or `only`. `EXPLAIN=0` means `off`, `EXPLAIN=1` means
`on`, `EXPLAIN=only` means `only`; any other non-empty value is a plain message
naming the three accepted values, exit 2. With `EXPLAIN` unset or empty: the
saved answer (`off` or `on`), or `off` when nothing is saved. The modes are a
closed `Enum`; `only` can never be saved.

**The question.** These two options are the user's own wording; keep them word
for word. Wrap them to at most 78 columns.

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

- `1`, or Enter alone, saves `off`. `2` saves `on`. Surrounding whitespace is
  ignored.
- Anything else: say so in one line and ask again. After three unusable
  answers, say that option 1 is being used for now, save **nothing**, exit 0.
- End of input (Ctrl-D): the same, option 1 for now, nothing saved, exit 0.
- Ctrl-C: nothing saved, exit 130, no traceback. The make target stops, which
  is what the student asked for.
- After saving, one line confirming which option was saved and repeating
  `make choose`.

**Where the answer lives.** `.workstation/preferences.json` in the repository
root, found from the script's own location (`scripts/..`), never from the
current directory. Content: `{"version": 1, "explain": "off"}` or `"on"`,
followed by a newline. Write it atomically: a temporary file in the same
directory, then `os.replace`. Add `.workstation/` to `.gitignore`.

**A saved file that cannot be read** (not JSON, no `explain` key, an unknown
value, an unknown version) is information, and guardrail "never silently
discarded" applies: say in one line that the saved answer could not be read and
name the file, then behave as if nothing were saved. `--ask-once` with a
terminal asks again, and the new answer replaces the file. Do not delete or
rename it as a side effect otherwise.

**Shape (guardrails 1, 2, 3, 6).** Pure functions for: parsing the `EXPLAIN`
value, parsing the saved file's text, parsing one typed answer, deciding what
to do from (override, saved, has-terminal), and rendering the question. I/O at
the edges. Results are explicit values, not exceptions used for control flow.
No traceback for any expected condition, including a closed output pipe, an
unwritable directory, and Ctrl-C.

### 2. `Makefile`

- A phony target `first-run` whose recipe is `@./scripts/explain-choice --ask-once`.
- It becomes the **first** prerequisite of exactly these student targets: `up`,
  `open`, `shell`, `turtlesim`, `turtlesim-teleop`, `package`, `build`, `run`,
  `test`. Not `help`, `examples`, `engine`, `doctor`, `distros`, `image`,
  `logs`, `ps`, `down`, `reset`, `uninstall`, `selftest`, `check`, `lint`,
  `digest`, or the `teleop` pointer: diagnostics and maintenance stay
  non-interactive. If the Makefile at your base has a student target this
  list does not name, it is not asked before; record it under Open questions.
- A phony target `choose` whose recipe is `@./scripts/explain-choice --choose`.
- Both new targets join the `.PHONY` list. `make up help` and friends must
  still run nothing: they are in the other branch of the `ifneq`, so this
  should need no work, but there is a test for it below.

`choose`, `first-run`, and the `EXPLAIN` variable are additions to the
student-facing surface. Guardrails 1 and 5 would say STOP AND ASK; the
architect has decided these three, and **only** these three.

### 3. `scripts/workstation-help`

- `make help` lists `choose` as the last line of the group "Start here -- once
  per machine", with a one-line description saying it changes the answer to
  the question asked the first time. It does not list `first-run`.
- `choose` gets a `help` topic (changed 2026-10-01: `make choose help` must
  not refuse): the question in one sentence, the two answers, where the answer
  is saved, and that `EXPLAIN=0`, `EXPLAIN=1` or `EXPLAIN=only` overrides it for
  one command. No `examples` topic. The overview marks (`*` or bold) only
  targets with help **and** examples, so `choose`'s row stays unmarked, and
  the existing test that pins the marked rows stays as it is.

### 4. `ros2.ps1`

The same contract for a student on Windows without `make` or a host Python
(added 2026-10-01; the parity test requires `choose`):

- A `choose` command, listed by `.\ros2.ps1 help` in the same place `make help`
  lists it, accepting `choose help` like every command.
- The same ask-once before exactly the same student commands as item 2, and
  before `desktop`, `ros2.ps1`'s default command (`up` then `open`), which is
  what most Windows students run (attempt 1, Open question 3). Asked once,
  not once for `up` and again for `open`.
- The same file, `.workstation/preferences.json` next to `ros2.ps1`, the same
  JSON, written atomically; the same question text word for word **except**
  that wherever `scripts/explain-choice` says `make choose`, `ros2.ps1` says
  `.\ros2.ps1 choose` (attempt 1, Open question 2); the same
  answers, retries, Ctrl-D and corrupt-file behaviour; `EXPLAIN` from the
  environment or as `EXPLAIN=…` on the command line (the existing
  "assignments become environment variables" path) wins over the saved answer.
- "Both are terminals" in PowerShell is
  `-not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected`.
- A file written by either script is read by the other: a student may use
  both on one checkout (WSL and PowerShell).

### 5. Docs

- `README.md`: a short section, near the first `make up` in "Quick start",
  saying a question is asked once, what the two answers mean, that
  `make choose` (or `.\ros2.ps1 choose`) changes it, and that `EXPLAIN=0` or
  `EXPLAIN=1` overrides it for one command. Say plainly that on this branch
  option 2 does not print anything yet. Touch no other README section: stage
  13 edits "Configuration" in parallel.
- `docs/roadmap.md`, under Stage 2: mark pipeline stage 1 of 4 as done on
  `native-recipes`. Apply the user's pixi decision (README, "Plan for roadmap
  Stage 2"): the design sketch's macOS variant becomes pixi and RoboStack
  instead of "brew + native ROS or RoboStack", and the Stage 4 decision-point
  table's "Package manager" example values gain `pixi`. Do not touch the
  "Status" section at the end; nothing has reached `main`.

## Ground rules

- **Behaviour is preserved exactly for anyone who is never asked.** With no
  terminal, every existing target prints byte-for-byte what it prints today.
  The existing tests pass unmodified (the 27 known `test_distros` failures
  excepted), apart from the additions described under "Tests".
- **Tests never write inside the repository.** The script finds its root from
  its own location, so tests copy `scripts/explain-choice` (and, for the
  Makefile tests, the `Makefile` and the scripts it calls; for `ros2.ps1`,
  the script and what it reads) into a temporary tree and run it there. Do
  **not** add an environment variable or a flag to relocate the preferences
  file; that would be a fourth addition to the student-facing surface. If
  copying cannot work, that is a Blocked finding.
- `scripts/smoke-container`, `Dockerfile`, `compose.yaml` and everything under
  `docker/` do not change.
- `tests/host/fakes.py` may gain a pty runner, additively. Its existing API and
  behaviour do not change.
- Print no native command and add no recipe data. That is stage 08 onwards.
- Nothing is installed system-wide. PowerShell and anything else you need go
  in your scratchpad.

## Allowed files

- `scripts/explain-choice` (new)
- `Makefile`
- `scripts/workstation-help`
- `ros2.ps1`
- `.gitignore`
- `README.md` — the Quick start section only
- `docs/roadmap.md`
- `tests/host/test_explain_choice.py` (new)
- `tests/host/test_workstation_help.py` — additions only
- `tests/host/test_ros2_ps1.py` — additions, plus item 0's change to
  `test_both_refuse_every_malformed_table_alike` only
- `tests/host/fakes.py` — additive, API-preserving
- `tests/host/README.md`
- `docs/stages/stage-07-REPORT.md` (new)

Anything else is out of scope. Needing another file is a Blocked finding.

## Tests

Black-box, like every test here: the script runs as a subprocess. Pin at least
these. Add any observable behaviour this list misses.

`tests/host/test_explain_choice.py`:

1. On a pty, nothing saved: the question appears with both options word for
   word; typing `2` saves `{"version": 1, "explain": "on"}`; the confirmation
   names `make choose`.
2. On a pty: `1` saves `off`; Enter alone saves `off`; ` 2 ` with spaces
   saves `on`.
3. On a pty, an answer already saved: `--ask-once` prints nothing and exits 0.
4. On a pty: three unusable answers save nothing and exit 0; so does Ctrl-D.
5. On a pty: Ctrl-C (send `\x03`) saves nothing, exits 130, no traceback.
   Build the pty runner with the controlling-terminal `preexec_fn` and the
   `wait()`-after-EOF rule from the Motivation.
6. No terminal (stdin `/dev/null`, stdout a pipe): `--ask-once` prints nothing,
   exits 0, creates no file and no `.workstation` directory.
7. The self-test's shape, stdin a pty but stdout a pipe: the same as 6.
8. `EXPLAIN` set to `0`, `1`, or `only`: `--ask-once` on a pty does not ask and
   saves nothing. `EXPLAIN=maybe`: exit 2, a message naming `0`, `1`, `only`.
9. `--show`: `off` with nothing saved; the saved value otherwise; each `EXPLAIN`
   value beats a saved answer; `EXPLAIN=` (empty) does not.
10. `--choose` on a pty replaces a saved answer and shows the old one first;
    without a terminal it exits 1 and changes nothing.
11. A corrupt file, one case each (not JSON; no `explain` key; `"explain":
    "only"`; `"version": 2`): one line naming the file; `--show` prints `off`;
    `--ask-once` on a pty asks again and the answer replaces it.
12. An unwritable root: a plain message, a non-zero status, no traceback. (Skip
    when running as root, where permissions do not bind; say so in the test.)
13. No arguments, an unknown argument, two modes at once: exit 2, usage.
14. `--show | head -0` and friends: no traceback from a closed pipe.
15. Through a temporary copy of the real `Makefile`, on a pty, with `COMPOSE`
    naming a fake: `make shell` asks, saves, and then runs the fake compose;
    a second `make shell` does not ask.
16. Through the same copy, no terminal: `make up help` prints help, asks
    nothing, and runs no compose command.
17. `make -n up` on a pty, through the copy: pin that it neither asks nor
    saves.

`tests/host/test_workstation_help.py`, additions only:

18. `make help` lists `choose` as the last line of "Start here -- once per
    machine"; it does not list `first-run`. `choose help` prints the topic.

`tests/host/test_ros2_ps1.py`, additions only (they run under `PWSH`):

19. `choose` on a pty saves the same JSON test 1 pins; a file written by
    `scripts/explain-choice` is read by `ros2.ps1` and vice versa.
20. No terminal: `.\ros2.ps1 up` asks nothing, saves nothing, and its docker
    argv is what it is today.
21. `EXPLAIN=1` on the command line and in the environment: no question.
22. The four corrupt files of test 11, through `ros2.ps1`: the same one line
    naming the file, and the same fallback.

**Prove the tests have teeth.** Six temporary mutations to
`scripts/explain-choice`, one at a time, each caught by a test, each reverted
by copy-out and copy-back with a checksum: ask when only stdin is a terminal;
save on Ctrl-D; treat Enter as option 2; let a saved answer beat `EXPLAIN`;
swallow the corrupt-file message; find the root from the current directory.
Two more for `ros2.ps1`: ask when output is redirected; write a different
JSON key.

## Verification

Run each and paste the output into the report.

1. **Python 3.9 for real**: `/usr/bin/python3 --version` (expect 3.9.x), then
   `/usr/bin/python3 -m unittest discover -s tests/host`. State which tests
   skip there and why.
2. **A real terminal session, by hand**, using BSD `script` to provide the
   terminal: in a scratch copy of the repository (not your worktree, so
   nothing is saved there), `script -q /dev/null make choose`, answer 2, then
   `./scripts/explain-choice --show`. Paste the transcript. For
   `ros2.ps1 choose`: this sandbox refuses `pwsh` as a plain shell command
   (attempt 1, Open question 1) but allows Python to start it, so drive it
   through the tests' pty runner from a short Python script, and paste that
   transcript instead.
3. **Nothing changed for the unasked.** For `help`, `engine`, `doctor` and
   `distros`, and for `make -n` of `up`, `shell`, `turtlesim`,
   `package PKG=x`, `build`, `run PKG=x NODE=y`, and `test`, all with stdin
   from `/dev/null`: save the output on the unmodified base and on your
   branch, and `diff`. The only permitted differences are the `choose` line in
   `make help` and the `first-run` recipe line in the `make -n` outputs.
4. **The real suite**, isolated (stage 13 runs its own self-tests at the same
   time, on port 6096):
   `SELFTEST_PROJECT=ros2-tutorials-st07 SELFTEST_NOVNC_PORT=6097 SELFTEST_ROS_DOMAIN_ID=7 IMAGE_NAME=ros2-tutorials-st07 make selftest`
   once, at the end; then show that no `.workstation` directory exists in your
   worktree, and remove the `ros2-tutorials-st07` image. **Never run
   `make selftest` without `IMAGE_NAME`.**
5. `git status` is clean after `make check`, and no `.workstation` exists.

## Definition of Done

- Baseline on the unmodified base: `make lint`, and `make check` with
  `PWSH=<your scratchpad pwsh>`. Record count, failures, skips and time.
- Final: `make lint` passes, with `scripts/explain-choice` classified
  `python, host (3.9 grammar)`.
- Final: `PWSH=… make check` passes apart from the same 27
  `test_distros` failures (item 0 having fixed the other 13), and no
  `test_ros2_ps1` test skips. Report the new
  count. **Budget:** `python3 -m unittest discover -s tests/host -p
  'test_explain_choice.py'` under 5 seconds; `make check` as a whole no more
  than 10 seconds slower than your baseline.
- Final: the isolated `make selftest` passes every check, once, at the end.
- Item 0: the 13 subtests pass and its negative control fails them. Tests
  1–22 present; the eight mutations caught; Verification 1–5 pass.
- `grep -n "shell=True\|os.system" scripts/explain-choice` finds nothing.
- `git diff native-recipes --stat` shows only allowed files.

Never touch the compose project `ros2-tutorials`; it is the user's.

## Commit

One commit, containing the change and `docs/stages/stage-07-REPORT.md`, with
exactly this subject line (a `Co-Authored-By:` trailer is expected):

```
feat: ask once whether to show the native commands
```

Stage files by path; never `git add -A`. Do not amend the commit to perfect
the report: where the report quotes its own commit's stat, quote the stat of
the change **excluding the report file**, which is exact before you commit:
`git diff native-recipes --stat -- . ':!docs/stages/stage-07-REPORT.md'`.
Then `git push -u origin stage-07-first-run-question-r2`. Never push to
`native-recipes`, `multi-distro` or `main`.

## Report requirements

`docs/stages/stage-07-REPORT.md` must contain:

1. The `git log --oneline -1` line from the first step, before any merge.
2. A checklist echo of "The change" and the Definition of Done.
3. Baseline and final gate outputs, verbatim, with the exact commands and the
   `pwsh` and Python versions used.
4. Tests 1–22 mapped to test names; the eight mutations tabulated with
   checksums; the outputs of Verification 1–5.
5. The final text of the question and of every message either script can
   print.
6. The stat of the change excluding the report, as described under Commit.
7. **Deviations**, numbered and honest, including the boring ones.
8. **Open questions**: things you noticed but correctly did not do, and anything
   in this prompt you believe is wrong.

## Blocked protocol

STOP and commit only the report, with a BLOCKED section giving the exact
failing output and why each permitted path is closed, if:

- a gate fails on the unmodified base other than the 27 known `test_distros`
  failures and the 13 item 0 fixes;
- the question cannot be asked from a make prerequisite without changing what
  an unasked student sees;
- the tests cannot avoid writing inside the repository without a new
  environment variable or flag;
- `ros2.ps1` cannot honour the same file and question without a host Python;
- the change cannot be made inside the allowed files;
- any guardrail in `docs/stages/README.md` says STOP AND ASK, other than the
  three additions this prompt authorizes.

A clean block is a successful execution.
