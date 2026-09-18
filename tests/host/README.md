# Host-script tests

Black-box tests for the scripts in `scripts/`, the ones that run on your own
computer rather than inside the container.

```sh
make check                                  # the same thing, via make
python3 -m unittest discover -s tests/host -v
```

They need no container engine, no network, and no containers, and they finish in
a couple of seconds.

## The one rule

**Each test runs a script as a subprocess and asserts only on stdout, stderr,
and exit status.** Nothing here imports, sources, or greps a script's text, so
the same tests must keep passing when a script is rewritten in another language.
That is the point: they exist so the Python port
([../../docs/roadmap.md](../../docs/roadmap.md)) can be proved equivalent.

## How a script sees the world

`fakes.py` builds a throwaway directory per test and makes it the *only* entry
on `PATH`. Into it go:

- **fakes** — small generated `python3` programs standing in for `docker`,
  `podman`, `curl`, `wslview`, and friends. Each records its argv to a file and
  replies with a canned stdout, stderr, and exit status, optionally depending on
  the arguments it was given.
- **real system tools** — `sed`, `grep`, `awk` and the like, symlinked in by
  name, one explicit `link()` call at a time.

Because the sandbox is the whole `PATH`, a real `docker` or `podman` installed
on the machine can never leak into a test.

### What a fake records

One JSON object per line, in `<sandbox>/calls/<name>`:

```json
{"argv": ["-p", "ros2-tutorials-selftest", "build"], "env": {"ROS_DOMAIN_ID": "99"}}
```

JSON rather than NUL-joined text because an argument may itself contain
newlines — `scripts/smoke-container` passes whole multi-line shell scripts as a
single argument to `bash -lc`, and a line-per-call format would split one such
call into a dozen phantom ones.

`sandbox.argv(name)` and `sandbox.last_argv(name)` read the argv back.
`sandbox.fake(..., record_env=("ROS_DOMAIN_ID", "NOVNC_PORT"))` also captures
those variables from each call's environment, read back with
`sandbox.recorded_envs(name)` and `sandbox.last_recorded_env(name)`. Recording
the environment is how a test can tell that a script *exported* something,
rather than only that it printed a claim about it.

### How a fake decides what to reply

`rule(args, stdout=…, stderr=…, exit_code=…, match=…, times=…)` builds one
canned reply; the first rule that matches wins, and anything unmatched gets the
fake's default reply. The three match modes:

| `match` | fires when |
|---|---|
| `prefix` (default) | argv *starts with* `args` |
| `all` | every word in `args` is a whole argument somewhere in argv |
| `contains` | every string in `args` is a *substring* of some argument |

`contains` is what addresses a command sent as one argument, as in
`compose exec … bash -lc '<a whole script>'`. `all` is what addresses a bare
word exactly: `"tutorial"` is a substring of the project name
`ros2-tutorials-selftest`, which is on every compose call, so only `all` can
single out the check that runs `tutorial` with no arguments.

`times=N` spends a rule after N matching calls, after which the identical call
falls through to the rules below it. That is the only way to model a command
that fails a few times and then starts working — a readiness probe repeated
with an unchanging argv.

## The self-test's own tests

`test_smoke_container.py` runs `scripts/smoke-container`, the suite behind
`make selftest`, as a subprocess with `COMPOSE` naming a fake, plus fakes for
`podman`, `podman-compose`, `sleep` and `curl`. It pins the three properties
that exist because of real incidents — the isolated compose project, the
isolated host port, the isolated `ROS_DOMAIN_ID` — along with the suite's
accounting, its cleanup, and `--keep`.

Two things about that file are worth knowing before editing it:

- **The all-pass scenario is a table, not code.** `HAPPY_COMPOSE_RULES` is a
  list of `contains` rules; every check in the suite passes under it, and
  `HAPPY_TRANSCRIPT` is the resulting ordered list of step titles and check
  names. That transcript is the contract a rewritten suite has to reproduce.
  **Order matters** in the table: a row whose text is contained in a longer
  command must come after that longer command's row.
- **One run of the suite is the unit of work,** costing about a second, so each
  distinct scenario is run once by `scenario(key, …)` and shared, read-only, by
  the tests that inspect it.

The suite `cd`s to the repository root and runs the real `Makefile`, so these
tests need `make`, `bash`, `seq`, `awk` and a few other system tools. Where one
is missing — the Python 3.9 container used for the grammar check, for instance —
the whole file skips.

## Skips

`open-url` decides it is on WSL by reading `/proc/version` as well as
`WSL_DISTRO_NAME`, so its macOS and plain-Linux branches cannot be reached from
outside the script on a WSL host. Those tests skip there, with that reason, and
run in CI, which is real Linux.
