# Stages

Delegated implementation happens here as numbered stages. A coordinator writes
each stage prompt and reviews the result; a `stage-executor` agent implements it
in an isolated git worktree. Executors never review themselves.

## This pipeline's branches

The Python port runs on the integration branch **`python-port`**, not on `main`.
Prompts are committed to `python-port`, executors branch from it, and verified
stages merge back into it. The whole branch is promoted to `main` only when the
port is complete and verified end to end — that promotion is the user's call.

## Numbering

One global sequence: `stage-01`, `stage-02`, and so on, never reused. Each stage
has exactly two files:

- `stage-NN-PROMPT.md` — written by the coordinator, committed to `python-port`
  *before* the executor launches. Committing first reserves the number and makes
  the committed text canonical.
- `stage-NN-REPORT.md` — written by the executor, in the same single commit as
  its change.

## Gates

Every stage's Definition of Done uses these commands verbatim. Each shell that
runs them needs Podman's compose on its PATH first:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

| Gate | Command | Notes |
|---|---|---|
| Static | `make lint` | Validates `compose.yaml`; stage 01 extends it to shellcheck and Python 3.9 checks |
| Full suite (end to end) | `make selftest` | Builds the image and exercises every documented workflow, about 10 minutes. 32/32 at `1b29b66` |

`make selftest` runs as its own compose project so it can never touch real
work. Stages that may run at the same time must isolate it further, because
they would otherwise share the project, host port, and image tag:

```sh
SELFTEST_PROJECT=ros2-tutorials-stNN SELFTEST_NOVNC_PORT=60NN SELFTEST_ROS_DOMAIN_ID=NN IMAGE_NAME=ros2-tutorials-stNN make selftest
```

Known gaps, as of scaffolding:

- **CI has never run.** `.github/workflows/docker-image.yml` triggers on pushes
  to `docker/**` and on pull requests; neither has happened. Nothing it checks
  has ever been checked.
- **shellcheck and hadolint are not installed locally**, so `make lint` has
  never linted a script. Stage 01 addresses both.

## Environment facts executors need

- Rootless Podman 3.4.4 with podman-compose 1.6.0 (host: WSL 2, Ubuntu 22.04).
- zsh prints a harmless `add_to_front_of_path: no matches found` line on every
  command. Ignore it.
- The user may have their own workstation running as compose project
  `ros2-tutorials` on host port 6080. **Never stop, recreate, or exec
  destructively into it, and never touch its volumes.**
- podman-compose quirks are listed in `docs/host-requirements.md`. The ones that
  bite: `ps` takes no service argument; `logs` passes `--color`, which Podman 3
  rejects; services in a profile need `--profile` on every subcommand; `run`
  prints a container id rather than the command's output.

## Guardrails

The unifying principle: **information, once obtained, is never silently
discarded or degraded.** Each rule ends in STOP AND ASK: record the question in
the report's Blocked section instead of improvising an answer.

1. **Make illegal states unrepresentable.** Closed choices are enums or fixed
   sets, not free strings passed around and compared: the container engine
   (docker or podman), the build type (ament_cmake or ament_python), the
   template (pubsub or param). A new optional flag or make variable on the
   student-facing surface ⇒ STOP AND ASK.
2. **Functional core, imperative shell.** Pure functions take text or values
   and return text or values: shell quoting, the CMakeLists / setup.py /
   package.xml patchers, the stale-image comparison, the CNI line filter.
   Subprocesses and file I/O live at the edges, in `main()` or close to it.
3. **Explicit errors, not exceptions as control flow.** An expected condition
   (no engine found, desktop not running, package already exists) is an exit
   code and a plain-English message, never a traceback reaching a student.
   No bare `except:`.
4. **No primitive obsession.** Paths are `pathlib.Path`. Commands are argv
   lists, never shell strings. **`shell=True` ⇒ STOP AND ASK**: it reintroduces
   the quoting bugs this port exists to end.
5. **Closed sets stay closed.** The pkg subcommands, the templates, and the
   make targets are fixed. Adding one is an architect decision ⇒ STOP AND ASK.
6. **Parse, don't validate.** Arguments are parsed once, at the entry point,
   into typed values; nothing downstream re-checks them. When a tool's output
   (`podman inspect`, the registry's headers) is not in the expected shape,
   surface that — never guess ⇒ STOP AND ASK if you find yourself guessing.
7. **Student work is append-only.** Never overwrite or delete anything under a
   workspace or volume as a side effect: `pkg new` on an existing package
   refuses rather than clobbers, `init-workspace` never overwrites. Destructive
   operations stay explicit and confirmed. Changing either ⇒ STOP AND ASK.
8. **Behaviour is preserved exactly.** This is a port. User-visible output —
   messages, the printed commands, exit codes — stays the same wherever the
   suite, the docs, or a student's muscle memory depends on it, and printed
   commands stay paste-safe. An intentional user-visible change ⇒ STOP AND ASK.

## Coordinator practices

- Stage prompts land on `python-port` before launch: canonical text, and the
  number reserved.
- At most one in-flight stage touches any shared registration file. In this
  repo those are `Makefile`, `.github/workflows/docker-image.yml`, `Dockerfile`,
  `compose.yaml`, and `scripts/smoke-container`.
- **Tests before ports.** A script with no test coverage gets coverage in a
  tests-only stage *before* it is ported. Never change the tests and the code
  they judge in the same stage.
- Stages running concurrently get distinct `SELFTEST_PROJECT`,
  `SELFTEST_NOVNC_PORT`, `SELFTEST_ROS_DOMAIN_ID`, and `IMAGE_NAME`.
- Executors attempt their own push and expect credential failure; the
  coordinator pushes and merges.
- Review is the diff plus an independent rerun of the gates, never reading the
  report alone.
- A retro every 5 stages (before authoring stage 05, 10, …), plus whenever the
  user asks.

## Plan for the Python port

| Stage | Kind | Scope | Runs |
|---|---|---|---|
| 01 | Infra | Lint by shebang: real shellcheck and a Python 3.9 gate, locally and in CI; CI triggers that actually fire | alone |
| 02 | Tests only | Black-box tests for the host scripts; smoke coverage for `tutorial` and `init-workspace` | alone |
| 03 | Port | Container scripts: `pkg`, `tutorial`, `init-workspace`, `install-ros-packages` | parallel with 04 |
| 04 | Port | Host scripts: `compose-command`, `compose-up`, `check-host`, `run-quiet`, `open-url`, `base-image-digest` | parallel with 03 |
| 05 | Port | `scripts/smoke-container` itself, last (retro first) | alone |

The same names throughout, with no `.py` extension, so the Makefile, Dockerfile,
CI, and docs need no renames. What stays shell, and why, is in
[../roadmap.md](../roadmap.md#language-python-replaces-shell).
