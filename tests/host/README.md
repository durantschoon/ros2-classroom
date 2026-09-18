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

## Skips

`open-url` decides it is on WSL by reading `/proc/version` as well as
`WSL_DISTRO_NAME`, so its macOS and plain-Linux branches cannot be reached from
outside the script on a WSL host. Those tests skip there, with that reason, and
run in CI, which is real Linux.
