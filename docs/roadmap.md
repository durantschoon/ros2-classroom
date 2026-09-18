# Purpose and roadmap

## Why this repository exists

Students should be able to start learning ROS 2 in minutes, not after a day of
installation. ROS 2 installation varies enormously by platform — different
package managers, different supported OS versions, different graphics stacks,
different failure modes — and none of that variation teaches anyone anything
about robotics. This repository absorbs that grunt work so a class can begin at
the same starting line on Linux, macOS, or Windows.

## The principle: convenience without a black box

Hiding the setup must not hide the *knowledge*. A student who only ever types
`make turtlesim` learns our Makefile, not ROS.

So every convenience target should print the commands a student would have run
natively on their own platform, before doing the equivalent thing in the
container. The claim we are making to them is:

> Here is what you would have typed on your machine. You could have pasted
> these and gotten the same result. We are running the container equivalent so
> you can get on with the tutorial.

That turns each target into a small lesson instead of a magic word, and it
means a student can graduate off this repo onto a real native install.

## Stages

### Stage 1 — Task-level make targets

**Status: done**, except `make node` (deferred, below).

Wrap the common student operations in targets named after the task, not the
tool: `make package`, `make build`, `make run`, `make test`, sitting on the `pkg`
helper, which prints each real `ros2`/`colcon` command — quoted so it pastes —
before running it.

Acceptance: a student can complete the three client-library beginner tutorials
without typing a `docker`/`podman` command:

1. Creating a workspace
2. Creating a package
3. Writing a simple publisher and subscriber (C++ and Python)

Decisions made along the way:

- **Students get the ROS meanings of `build` and `test`.** In ROS, "build" means
  `colcon build` of your code; that is what a student following a tutorial will
  type. The image and self-test targets that previously held those names became
  `make image` and `make selftest`.
- **`make node` is deferred.** Adding a node to an existing package means
  patching a `CMakeLists.txt` or `setup.py` the student may already have
  edited by hand — much riskier than generating fresh files. Revisit once
  `pkg` is ported to Python (see the language section below).
- **Two terminals, stated everywhere.** Every `make` command runs on the
  student's own computer; the terminal inside the browser desktop is for ROS
  commands. Because `make` exists inside the container, a workstation target
  typed there would fail with a baffling "No rule to make target", so a shell
  function explains instead.

### Stage 2 — "What you would have run"

Each target prints the native equivalent for the student's detected platform
before executing — for students who asked for it.

**The student chooses, once, at the very beginning.** The first time they run
a make target, they are asked:

> 1. Just run things for me in the browser workstation.
> 2. Do that, AND show me the commands that should do the same thing directly
>    on my own system — no container involved.

The answer is saved locally (gitignored) and never asked again; a make target
changes it later. With no terminal to ask on (CI, scripts), the default is
option 1 and nothing blocks. Option 2 is honest about its claim: these are
commands we *think* work natively on their OS, each with its verification
status, not a promise.

**Windows means WSL.** For a Windows student the native route shown is ROS
inside WSL 2 (Ubuntu and apt), not a pure-Windows install. WSL is already this
project's documented Windows path, the apt recipes are the ones CI can verify,
and ROS's pure-Windows install is the most fragile of all the platforms. The
first recipe a Windows student without WSL sees is therefore `wsl --install`.

Design sketch:

- A recipe per operation, with one variant per platform (Ubuntu/apt, Fedora/dnf,
  macOS/brew + native ROS or RoboStack, Windows/WSL 2).
- Platform detection reuses `scripts/compose-command`'s approach.
- Output clearly separates *what you would run natively* from *what we are
  running for you*.
- The saved choice can be overridden per command: `EXPLAIN=0` silences the
  native commands, `EXPLAIN=only` prints them without executing anything.

**The honesty problem to solve first.** We would be printing commands for
platforms we do not run. A printed command that does not actually work on
macOS is worse than printing nothing, because the student trusts it. Options,
cheapest first:

1. Mark each recipe with a verification status (`verified-in-ci`,
   `verified-by-hand`, `community-reported`) and print that status alongside.
2. CI-verify the Linux recipes for real, since GitHub runners are Linux.
3. Accept community verification for macOS/Windows via the feedback loop below.

Acceptance: a new student is asked exactly once; nothing native is printed
for a student who chose option 1; and no command is ever printed without a
verification status attached.

Planned pipeline stages, to be authored after the Python port (stages 01-05)
lands, since recipes are structured data and belong in Python:

1. The first-run question, its saved answer, and the target that changes it.
2. The recipe data model and platform detection (the Stage 4 decision points).
3. Linux/apt recipes, verified for real in CI.
4. macOS and WSL recipes, entering as `verified-by-hand` or
   `community-reported`.

### Stage 3 — Generate a runnable native script

`make script` writes `native-setup.sh` (or `.ps1`) containing the same commands
for the student's platform, so they can attempt the real install when they are
ready — on a spare machine, a VM, or after the course.

Acceptance: the generated script is the same text that Stage 2 prints; there is
one source of truth for each recipe, not two.

### Stage 4 — Failure capture and the improvement loop

*Speculative; do not build before Stages 1-3 are real.*

A student runs the generated native script, it fails, and that failure becomes
three things: a prompt they can run with an AI assistant to fix their machine,
a data point for us, and eventually a better recipe for the next student.

#### The loop

```
native script fails
  -> student sees the exact report, and sends it (their choice)
  -> we aggregate by situation + failure + attempted fix
  -> a fix that works repeatedly gets promoted to a verified recipe
  -> the next student on that platform never sees the failure
```

The whole point is that the recipes improve from real machines we do not own.
That only works if students actually send reports, and they will only do that
if the exchange is obviously fair: we say plainly what is collected, what it is
used for, and what they get back.

#### Transparency, stated up front

The README and the report command itself must say, in plain words:

- Failure reports are sent to the project maintainers.
- We keep aggregate statistics on which situations hit which failures and which
  fixes worked.
- We use those statistics to rewrite the setup instructions.
- Nothing is sent without the student pressing the button, and the exact
  payload is shown first.

No pre-ticked boxes, no "by using this software you agree", no background
submission. A student who declines still gets the fix prompt — the local help
must never be held hostage to sending data.

#### Decision points: the part worth getting right

Fixes are only reusable if we can say *which situations they apply to*. So the
schema is not free-form; it is a fixed set of enumerated decision points — the
factors that actually change which command a student should run:

| Decision point | Example values | Why it changes the answer |
|---|---|---|
| OS family + major version | `ubuntu-24.04`, `macos-15`, `windows-11` | Different package managers and ROS support |
| Architecture | `amd64`, `arm64` | Apple Silicon package availability |
| Environment | `native`, `wsl2`, `vm`, `ssh-only` | Display and device access differ |
| Package manager | `apt`, `dnf`, `brew`, `conda` | Literally different commands |
| Container engine | `docker`, `podman-3`, `podman-4`, `none` | The quirks already documented |
| Display stack | `x11`, `wayland`, `wslg`, `headless` | GUI failures cluster here |
| GPU vendor | `nvidia`, `amd`, `intel`, `none` | Driver and rendering paths |
| Network constraints | `direct`, `proxy`, `restricted` | Mirrors, certificates, blocked ports |
| ROS distribution | `lyrical`, `jazzy` | Package names |

Every value is a closed enumeration, never a free-text field. That keeps the
data comparable across students, and it keeps a stray username or hostname out
of the payload by construction rather than by scrubbing.

The recipes in Stage 2 are then indexed by these same decision points, so a
recipe, a failure, and a fix all speak one vocabulary. New decision points get
added only when the data shows a fix that applies to some students and not
others with no existing field to explain the difference — that is the signal
that we have found a real distinction rather than noise.

#### What we keep

Per report: the decision-point values, which recipe step failed, a normalised
error signature, and whether an attempted fix resolved it. Free-form error text
is shown to the student and sent only if they include it.

Aggregates we actually act on:

- Failure rate per recipe step, per situation. High rates mean the recipe is
  wrong, not that students are careless.
- Which fix resolved which failure, and how often.
- Situations with no reports at all — the platforms we are flying blind on.

#### Promoting a fix

A community fix does not silently become official. It moves:

`community-reported` -> `verified-by-hand` (a maintainer reproduced it, or
several independent students confirmed it) -> `verified-in-ci` (only where a
runner exists for that platform).

The status is printed next to the command, so a student always knows whether
they are running something proven or something plausible.

#### Build order

1. `make report-failure` — prints a scrubbed, copy-pasteable report and opens a
   pre-filled GitHub issue. Zero servers, zero background reporting, and the
   issue thread *is* the transparency.
2. Only once issue volume makes manual triage impractical: a small endpoint that
   accepts the same enumerated payload, with the same consent step.

Starting with issues also validates the schema for free. If the decision points
cannot explain the failures arriving as issues, they are the wrong decision
points, and that is much cheaper to discover before a server exists.

Acceptance for a first cut: a student can produce a report, see exactly what it
contains, choose not to send it, and still get a usable fix prompt.

## Distribution: where things live

- **The project's home is the GitHub repository.** Its README is the page a
  student lands on. Per-platform walkthrough videos (macOS, Windows with WSL,
  Linux) live on YouTube and are linked from a "watch it on your platform"
  table there. Recording a video means walking through
  `platform-test-matrix.md` on that machine, so each video also completes a
  row of the checklist.
- **A prebuilt image, on GitHub's container registry (`ghcr.io`).** Today every
  student builds a 3 GB image for about ten minutes before seeing a turtle; a
  published image makes that a download. GHCR rather than Docker Hub, because
  Docker Hub throttles anonymous pulls per IP address and a classroom behind
  one campus NAT shares a single allowance; because this repository's CI can
  publish there with its built-in token, with no second account or stored
  secret; and because students then never touch Docker Hub at all.
  The image must be published for amd64 **and** arm64, or Apple Silicon
  students get emulation and a crawling desktop. `make image` would then pull
  by default and build only on request. Sequenced after the Python port.
- **A friendlier front door (GitHub Pages)** only if the README becomes too
  dense for a first-time student.

## Language: Python replaces shell

**Decided 2026-09-18.** Tooling moves from shell to Python, not Go.

Why Python:

- It is already in the image, so the container side adds nothing.
- It is ROS's own tooling language (`ros2`, `colcon`, and `rosdep` are all
  Python), and students writing `rclpy` nodes can read the tools they use.
- `pkg` is already mostly Python: its file patching is embedded Python heredocs
  inside a bash script.
- On the host, wherever `make` works `python3` does too. macOS gets both from
  the Command Line Tools; Linux and WSL ship Python 3. So it adds no install
  burden for anyone who can already run the Makefile.

Constraints this sets:

- **Host scripts are stdlib-only and Python 3.9-compatible**, because macOS's
  Command Line Tools ship 3.9. No third-party imports: a `pip install` step
  would be exactly the setup grunt this project exists to remove.
- **Some things stay shell because they must.** The bashrc drop-in is
  *sourced* by bash, and it holds the `make` guard. The entrypoint sources
  `setup.bash` before exec. Openbox runs its autostart as shell. The Makefile
  stays as the student-facing interface; its recipes call the Python scripts.

What this gives up: Windows students without WSL still get no native tooling,
which a Go binary would have provided. WSL is already the documented Windows
route, so that is an acceptable trade.

**Porting order.** Never change the tests and the code in the same step. Port
the host and container scripts first, with the existing shell smoke suite as
the oracle, which must stay green after every script. Port the smoke suite
itself last, once everything it checks is already Python.

For the record, of the fourteen bugs found while building Stages 0 and 1, one
was a shell-language bug (`"$*"` dropping quotes). The rest were platform,
engine, and ROS semantics that any language would meet. The case for Python is
readability for students and a sane home for Stage 2's structured recipe data,
not a lower bug count.

## Non-goals

- Replacing the official ROS installation instructions. We point at them.
- Supporting every ROS distribution. Only what CI verifies.
- Hardware access as a headline feature; see `hardware-and-gpu.md`.

## Status

Stage 0 (the container workstation itself) and Stage 1 (task-level make
targets) are done and verified. Stages 2-4 are not started.
