# Stage 07 — The first-run question

Branch name for this stage: `stage-07-first-run-question`. Base: `native-commands`.

Read `docs/stages/README.md` first, including "Added by the retro before stage
05" and "Plan for roadmap Stage 2". Its gates, environment facts, and
guardrails apply and are not repeated here. Then read `docs/roadmap.md`,
"Stage 2 — What you would have run": it is the specification this stage begins.

**First step, before anything else.** Executor worktrees have been created at a
stale commit in every stage so far. Run `git log --oneline -1` and **put that
line in your report** (the coordinator is measuring whether a settings change
fixed this). If `docs/stages/stage-07-PROMPT.md` is missing, run
`git fetch origin && git merge --ff-only origin/native-commands` and record it
as a Deviation. If the file is still missing, invoke the Blocked protocol.

## Motivation (measured)

The repository's principle is convenience without a black box
(`docs/roadmap.md`). Roadmap Stage 2 will print, before each target runs, the
commands that would do the same thing natively on the student's own system. The
user has decided that a student opts into that, once, at the very beginning,
and is never asked again.

This stage builds only the question, its saved answer, and the way to change
or override it. It prints no native command: the recipes arrive in stages 08
to 10, and this work sits on the integration branch `native-commands` until
they do, so that `main` never offers a choice that does nothing.

The coordinator prototyped the approach before writing this prompt, as the
retro requires. Measured on this host:

- A prerequisite target whose recipe runs a Python script **can** ask on the
  student's terminal and read the answer: run under a pty, `make up` printed
  the question, accepted `2`, saved it, and then ran `up`'s own recipe. Run
  again, it did not ask.
- With stdin not a terminal (`make up </dev/null | cat`), a script that checks
  `sys.stdin.isatty() and sys.stdout.isatty()` did not ask and did not block.
- In the self-test's shape, stdin a terminal but stdout captured, the same
  check did not ask. That matters: `scripts/smoke-container` runs
  `make package`, `make build`, and `make test` with stdout captured and stdin
  inherited, and must never stop to ask.
- make exports command-line variables to recipes: with `make show EXPLAIN=only`
  the recipe saw `EXPLAIN=only`; without it, an empty value.
- A test can drive all of this with the standard library alone: `pty.openpty()`,
  the slave end as the child's stdin, stdout, and stderr, `select` on the
  master, and `os.write` of the answer once the prompt text has been seen.
  Output read back from the master has `\r\n` line endings.
- `make check` takes about **28 seconds** on this host (173 tests), so the old
  30-second budget has no room left. This stage's budget is below.

## The change

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
  `test`. Not `help`, `examples`, `engine`, `doctor`, `image`, `logs`, `ps`,
  `down`, `reset`, `selftest`, `check`, `lint`, `digest`, or the `teleop`
  pointer: diagnostics and maintenance stay non-interactive.
- A phony target `choose` whose recipe is `@./scripts/explain-choice --choose`.
- Both new targets join the `.PHONY` list. `make up help` and friends must
  still run nothing: they are in the other branch of the `ifneq`, so this
  should need no work, but there is a test for it below.

`choose`, `first-run`, and the `EXPLAIN` variable are additions to the
student-facing surface. Guardrails 1 and 5 would say STOP AND ASK; the
architect has decided these three, and **only** these three.

### 3. `scripts/workstation-help`

`make help` lists `choose` as the last line of the group "Start here -- once
per machine", after `make image`, with a one-line description saying it changes
the answer to the question asked on the first `make up`. It does not list
`first-run`. No `help`/`examples` topic for `choose`.

### 4. Docs

- `README.md`: a short section, near the first `make up`, saying a question is
  asked once, what the two answers mean, that `make choose` changes it, and
  that `EXPLAIN=0` or `EXPLAIN=1` overrides it for one command. Say plainly
  that on this branch option 2 does not print anything yet.
- `docs/roadmap.md`: under Stage 2, mark pipeline stage 1 of 4 as done on
  `native-commands`. Do not touch the "Status" section at the end; nothing has
  reached `main`.

## Ground rules

- **Behaviour is preserved exactly for anyone who is never asked.** With no
  terminal, every existing target prints byte-for-byte what it prints today.
  The 173 existing tests pass unmodified, apart from the one addition described
  under "Tests" for `test_workstation_help.py`.
- **Tests never write inside the repository.** The script finds its root from
  its own location, so tests copy `scripts/explain-choice` (and, for the
  Makefile tests, the `Makefile` and the scripts it calls) into a temporary
  tree and run it there. Do **not** add an environment variable or a flag to
  relocate the preferences file; that would be a fourth addition to the
  student-facing surface. If copying cannot work, that is a Blocked finding.
- `scripts/smoke-container` and everything under `docker/` do not change.
- `tests/host/fakes.py` may gain a pty runner, additively. Its existing API and
  behaviour do not change.
- Print no native command and add no recipe data. That is stage 08 onwards.

## Allowed files

- `scripts/explain-choice` (new)
- `Makefile`
- `scripts/workstation-help`
- `.gitignore`
- `README.md`
- `docs/roadmap.md`
- `tests/host/test_explain_choice.py` (new)
- `tests/host/test_workstation_help.py` — additions only
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
   **Measured trap:** a child started with plain `subprocess.Popen` on the
   slave end has no controlling terminal, so `\x03` is never turned into
   SIGINT and the child hangs at the prompt. With a `preexec_fn` that calls
   `os.setsid()` and then `fcntl.ioctl(0, termios.TIOCSCTTY, 0)`, the same
   keystroke delivered SIGINT. Build the pty runner that way.
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
17. `make -n up` on a pty, through the copy: report what happens and pin it.
    If it asks or saves during a dry run, fix that with make's own means (the
    recipe has no `+` prefix, so it should not run) and pin the fix.

`tests/host/test_workstation_help.py`, additions only:

18. `make help` lists `choose`, after `make image` and before `make up`; it
    does not list `first-run`.

**Prove the tests have teeth.** Six temporary mutations to
`scripts/explain-choice`, one at a time, each caught by a test, each reverted
by copy-out and copy-back with a checksum: ask when only stdin is a terminal;
save on Ctrl-D; treat Enter as option 2; let a saved answer beat `EXPLAIN`;
swallow the corrupt-file message; find the root from the current directory.

## Verification

Run each and paste the output into the report.

1. **Python 3.9 for real**:
   `podman run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo
   docker.io/library/python:3.9-slim python -m unittest discover -s tests/host`.
   State which tests skip there and why. The image has no `make`.
2. **A real terminal session, by hand**, using `script -qc` to provide the
   terminal: in a scratch copy of the repository (not your worktree, so
   nothing is saved there), `make choose`, answer 2, then
   `./scripts/explain-choice --show`. Paste the transcript.
3. **Nothing changed for the unasked.** For `help`, `engine`, and `doctor`, and
   for `make -n` of `up`, `shell`, `turtlesim`, `package PKG=x`, `build`, `run
   PKG=x NODE=y`, and `test`, all with stdin from `/dev/null`: save the output
   on the unmodified base and on your branch, and `diff`. The only permitted
   differences are the `choose` line in `make help` and the `first-run` recipe
   line in the `make -n` outputs.
4. **The real suite**: one `make selftest` at the end, 48/48, and show that no
   `.workstation` directory exists in your worktree afterwards.
5. `git status` is clean after `make check`, and no `.workstation` exists.

## Definition of Done

- Baseline on the unmodified base: `make lint` and `make check` (173 tests
  expected, about 28 s). The coordinator measured `make selftest` at 48/48 on
  this base, in CI and locally, so do not re-measure it as a baseline.
- Final: `make lint` passes, with `scripts/explain-choice` classified
  `python, host (3.9 grammar)`.
- Final: `make check` passes. Report the new count. **Budget:** the new module
  `python3 -m unittest discover -s tests/host -p 'test_explain_choice.py'`
  takes under 5 seconds, and `make check` as a whole under 40.
- Final: `make selftest` 48/48, once, at the end.
- Tests 1–18 present; the six mutations caught; Verification 1–5 pass.
- `grep -n "shell=True\|os.system" scripts/explain-choice` finds nothing.
- `git diff native-commands --stat` shows only allowed files.

No other stage is running, so `make selftest` may use its defaults. Never touch
the project `ros2-tutorials`; it is the user's.

## Commit

One commit, containing the change and `docs/stages/stage-07-REPORT.md`, with
exactly this subject line (a `Co-Authored-By:` trailer is expected):

```
feat: ask once whether to show the native commands
```

Stage files by path; never `git add -A`. Do not amend the commit to perfect
the report: where the report quotes its own commit's stat, quote the stat of
the change **excluding the report file**, which is exact before you commit:
`git diff native-commands --stat -- . ':!docs/stages/stage-07-REPORT.md'`.
Then `git push -u origin stage-07-first-run-question`. Never push to
`native-commands` or `main`.

## Report requirements

`docs/stages/stage-07-REPORT.md` must contain:

1. The `git log --oneline -1` line from the first step, before any merge.
2. A checklist echo of "The change" and the Definition of Done.
3. Baseline and final gate outputs, verbatim.
4. Tests 1–18 mapped to test names; the six mutations tabulated with
   checksums; the outputs of Verification 1–5.
5. The final text of the question and of every message the script can print.
6. What `make -n` does, from test 17.
7. The stat of the change excluding the report, as described under Commit.
8. **Deviations**, numbered and honest, including the boring ones.
9. **Open questions**: things you noticed but correctly did not do, and anything
   in this prompt you believe is wrong.

## Blocked protocol

STOP and commit only the report, with a BLOCKED section giving the exact
failing output and why each permitted path is closed, if:

- a gate already fails on the unmodified base;
- the question cannot be asked from a make prerequisite without changing what
  an unasked student sees;
- the tests cannot avoid writing inside the repository without a new
  environment variable or flag;
- the change cannot be made inside the allowed files;
- any guardrail in `docs/stages/README.md` says STOP AND ASK, other than the
  three additions this prompt authorizes.

A clean block is a successful execution.
