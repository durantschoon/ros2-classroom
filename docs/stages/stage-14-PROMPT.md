# Stage 14 — `pkg build --changed`: rebuild only the packages that changed

Branch name for this stage: `stage-14-build-changed`. Base: `pkg-helpers`.

Read `docs/stages/README.md` first, including "Added after v1.0" and the
backlog entry "Rebuild only what changed". Its gates, environment facts, and
guardrails apply and are not repeated here.

**First step, before anything else.** Run `git log --oneline -1` and **put that
line in your report**. If `docs/stages/stage-14-PROMPT.md` is missing, invoke
the Blocked protocol (tonight nothing can be fetched: see "Running alongside
stage 13").

## Motivation (measured)

The user asked (2026-09-29) for helpers such as "only building packages that
need to be rebuilt". Within one package, colcon and CMake already rebuild only
changed files, and with `--symlink-install` an edited Python file needs no
rebuild at all. What a student cannot do easily is skip the packages that did
not change: `pkg build` with no name rebuilds every package; with names, the
student has to know which ones changed and which depend on them.

Measured by the coordinator on 2026-09-29, in a throwaway container of the
jazzy trial image, with one ament_python and one ament_cmake package built by
`colcon build --symlink-install`:

- colcon writes `build/<package>/colcon_build.rc` for each package it builds,
  containing `0` after a successful build.
- `colcon list` prints one line per package, tab-separated: name, path
  relative to the workspace, and the type in parentheses, e.g.
  `demo_cpp<TAB>src/demo_cpp<TAB>(ros.ament_cmake)`. Before the first build
  there is no `build/` directory at all.
- `colcon build --help` offers `--packages-above` (the named packages and
  everything that depends on them), `--packages-select-build-failed`, and
  `--packages-skip-build-finished`, but nothing that selects by edited source.

## The change

### 1. `docker/scripts/pkg`: `pkg build --changed`

The user authorized this one new option (guardrail 5: the subcommands stay
closed; this is an option of an existing one).

- `pkg build --changed`, with no package names. Names together with
  `--changed` is a usage error, exit 2.
- It lists the workspace's packages with `colcon list` (name, path, type),
  printing the command before running it as every `pkg` command does.
- A package counts as changed when, relative to the workspace:
  - `build/<name>/colcon_build.rc` is missing (never built): "never built";
  - it holds anything other than `0` (the last build failed): "last build failed";
  - or a file under the package's source path is newer than that stamp:
    "changed: <relative path of the newest such file>".
  Skipped when looking for newer files: directories whose name starts with
  `.`, `__pycache__`, and `*.pyc`. Parse the stamp's content once into one of
  these three cases plus "up to date"; nothing downstream re-reads it.
- It prints one line per package with its case, then:
  - nothing changed: `nothing to rebuild`, runs no build, exits 0;
  - otherwise: runs, printed first,
    `colcon build --symlink-install --packages-above <changed names, sorted>`,
    so what depends on a changed package is rebuilt too, followed by the same
    closing notes `pkg build` prints today.
- `usage()` documents the option in one line.
- The file-time scan is a pure function taking the listing and the stamps
  and file times as values; the filesystem walk and `colcon` calls stay at the
  edges (guardrail 2). Argv lists only.

### 2. `docs/creating-packages.md`

A short subsection: what `pkg build --changed` does, the command it runs, why
colcon's own `--packages-select-build-failed` / `--packages-skip-build-finished`
do not cover an edited package, and that an edited Python file under
`--symlink-install` needs no rebuild at all.

## Ground rules

- `pkg build` without `--changed`, and every other `pkg` command, behave
  exactly as today (guardrail 8).
- No make target, no make variable, no `ros2.ps1` change: this is the
  in-container command. Exposing it through `make build` is a later decision
  for the user; mention it under Open questions.
- Tests never write inside the repository.

## Running alongside stage 13

Stage 13 runs at the same time on another integration branch. It does not
touch `docker/scripts/pkg` or any file on this stage's list; this stage must
not touch any other file. Your self-test must not collide with its, nor with
the user's desktop (6080), the distributions' ports (6082-6084), or the
coordinator's trial containers (6091-6093). Use exactly:

```sh
SELFTEST_PROJECT=ros2-tutorials-st14 SELFTEST_NOVNC_PORT=6095 SELFTEST_ROS_DOMAIN_ID=14 IMAGE_NAME=ros2-tutorials-st14 make selftest
```

and remove the `ros2-tutorials-st14:*` images afterwards. **Never run
`make selftest` without `IMAGE_NAME`** (README, "Every self-test, by anyone,
sets IMAGE_NAME").

The host's SSH agent refuses to sign tonight, so `git fetch` and `git push`
fail. Try the push once at the end; if it fails, say so in your final message
and stop. The coordinator merges from your local branch.

## Allowed files

- `docker/scripts/pkg`
- `docs/creating-packages.md`
- `tests/host/test_pkg_build_changed.py` (new)
- `tests/host/fakes.py` — additive, API-preserving
- `docs/stages/stage-14-REPORT.md` (new)

## Tests

`tests/host/test_pkg_build_changed.py`, black-box: `docker/scripts/pkg` runs as
a subprocess with `WORKSPACE` pointing at a temporary workspace, and a fake
`colcon` on the sandbox PATH that answers `list` from the test's layout and
records every call. Package sources and stamps are real files in the temporary
workspace, with file times set by the test (`os.utime`), never by sleeping.

1. Nothing built yet: every package "never built"; the build names all of them.
2. All stamps `0` and newer than every source file: "nothing to rebuild", no
   `colcon build` call, exit 0.
3. One source file newer than its package's stamp: that package "changed:
   <path>", `--packages-above` names only it.
4. A stamp holding `1`: "last build failed", that package rebuilt.
5. Two changed packages: both named, sorted.
6. Files under `.git/`, `__pycache__/`, and a `*.pyc` newer than the stamp do
   not count.
7. `pkg build --changed my_pkg`: exit 2, usage, no colcon call.
8. The printed commands come before they run, and match the argv the fake
   recorded (the `colcon list` and the `colcon build`).
9. A failing `colcon build`: its exit status is `pkg`'s, as for plain
   `pkg build`.
10. Plain `pkg build` and `pkg build my_pkg`: argv unchanged from today.

**Mutations**, each caught, reverted by copy-back with a checksum: treat a
failed stamp as up to date; compare with `>=` the other way (older counts as
changed); use `--packages-select` instead of `--packages-above`; count
`__pycache__`.

## Verification

1. Python 3.9 for real:
   `docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/repo:ro -w /repo docker.io/library/python:3.9-slim python -m unittest discover -s tests/host`.
2. **For real, in a throwaway container** of the image your self-test built
   (`ros2-tutorials-st14:latest`, before you remove it), run as user `ros`
   with no volume: create two packages with `pkg new`, one depending on the
   other (`--deps`); `pkg build`; `pkg build --changed` (nothing to rebuild);
   `touch` a source file of the depended-on package; `pkg build --changed`
   (both rebuilt, through `--packages-above`). Paste the transcript.
3. The isolated self-test above: 48/48.

## Definition of Done

- Baseline on the unmodified base, final: `make lint`, `make check`; report
  counts and times.
- Tests 1-10; the four mutations caught; Verification 1-3.
- `grep -n "shell=True\|os.system" docker/scripts/pkg` finds nothing.
- `git diff pkg-helpers --stat` shows only allowed files.

## Commit

One commit, the change plus `docs/stages/stage-14-REPORT.md`, subject exactly:

```
feat: pkg build --changed rebuilds only what changed and what depends on it
```

Stage by path. Quote the stat excluding the report. Never push to
`pkg-helpers`, `multi-distro`, or `main`.

## Report requirements

1. The first step's `git log --oneline -1` line.
2. A checklist echo of "The change" and the Definition of Done.
3. Baseline and final gate outputs, verbatim.
4. Tests mapped to test names; mutations with checksums; Verification 1-3.
5. Every message `pkg build --changed` can print, verbatim, run-captured.
6. The stat excluding the report.
7. **Deviations**, numbered and honest.
8. **Open questions**.

## Blocked protocol

STOP and commit only the report, with a BLOCKED section, if a gate fails on
the unmodified base; if the change cannot be made inside the allowed files; if
`colcon list` or `colcon_build.rc` do not behave as measured above; or if any
guardrail says STOP AND ASK beyond the one option this prompt authorizes. A
clean block is a successful execution.
