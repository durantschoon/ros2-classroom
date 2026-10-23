# Native recipe developer contract

`scripts/native-recipes` is a stdlib Python 3.9 developer tool. It models recipes,
collects passive local observations, classifies hosts, and selects exact matches.
It never executes recipes. Make and PowerShell share `recipes/native/ubuntu-apt.json`
for opt-in explanations. The initial Ubuntu 26.04/Lyrical amd64 and arm64 groups
carry synthetic candidate evidence and are refused by normal dispatch until an
actual successful native CI run is recorded. Developer interfaces can inspect
and render candidates; they confer no execution or verification authority.

Run from any directory with Python 3.9 or later:

```text
python3 scripts/native-recipes detect --ros-distro lyrical
python3 scripts/native-recipes classify FACTS.json
python3 scripts/native-recipes validate CATALOG.json
python3 scripts/native-recipes select CATALOG.json FACTS.json REQUEST.json
```

Each success emits one JSON object with `outcome: "ok"` and `schema_version: 1`.
Exit 0 means success; exit 1 returns `outcome: "unsupported"` and an `error`
object with `code` and `message`; invalid JSON/schema/request exits 2 with
`outcome: "error"`. Argparse usage errors use stderr and exit 2. Missing files,
duplicate JSON object keys, NaN/Infinity, unexpected keys, bool-as-version,
unsupported versions and unknown domain cases are errors. No file is written.

## Facts and classification

Facts input has exactly `schema_version` (integer 1) and `facts`. `facts` contains
exactly these keys: `system`, `version`, `machine`, `os_id`, `os_version`,
`kernel_release`, `ssh`, `vm`, `tools`, `display`, `gpu`, `network`, `ros_distro`.
Each observation is `{"state": "known", "values": ["value"]}` or a state
`unknown`, `none`, or `not-observed` with an empty `values` array. Only `tools`
allows more than one value. Values must be unique nonempty strings without
control characters (C0, DEL, or C1).

- `known` records available evidence; it does not certify runtime usability.
- `unknown` means a consulted source could not classify a fact.
- `none` records absence within the observation's scope (e.g. no supported tools
  on PATH, no SSH session environment markers).
- `not-observed` means the detector did not inspect that property. Missing facts
  are schema errors and cannot silently become any of these states.

`detect` returns both raw `facts` and the classified `platform`. To replay it,
pass just `schema_version` and `facts` to `classify`; classification returns the
same `platform`. Collected facts pass through the same parser before detection
can succeed, so malformed detector inputs produce structured errors rather than
unreplayable success output. The platform includes every observation plus normalized `os`,
`architecture`, `context`, `route`, and `engine`; its `version` is the actual
OS version (Linux VERSION_ID, macOS ProductVersion, Windows major.minor.build).
Unknown OS identifiers are retained, rather than inferred from installed tools.
Architecture aliases x86_64/AMD64 become amd64; aarch64/arm64 become arm64;
other architectures become unknown while the original machine is retained.

The collector reads OS identity/version files, `os.uname` where available,
Windows system version, limited environment marker presence, DMI product name
for recognized VM families, and executable availability on PATH. It never runs
subprocesses or engine/GPU/network/WSL probes. It never reads usernames or
hostnames or returns environment values containing display/SSH addresses.
GPU and network remain not-observed. No display environment marker means
not-observed, since a desktop can exist without these markers. Unrecognized or
unavailable VM evidence means unknown, not a claim of physical hardware.

`context` distinguishes host-native execution from a WSL Linux guest; a Linux
kernel release containing Microsoft identifies the latter. Linux context requires
a known kernel release: unknown/none kernel evidence yields unknown context,
while not-observed kernel evidence yields not-observed context. These contexts
cannot select a native recipe. Windows remains a
Windows bootstrap host even if wsl.exe is installed. VM and SSH observations
are retained separately and can coexist with WSL or host-native execution;
`context: native` is not a claim of physical hardware or a local terminal.
These observations do not alter recipe matching until an operation needs a
material restriction. A later consumer must check display/session requirements
before claiming GUI guidance is suitable for a remote/headless environment.

Recognized installed tools are apt-get, dnf, brew, pixi, docker, podman, and wsl.
`engine` lists observed docker/podman executables, without claiming a daemon is
working. The **recipe route** is independently derived from OS identity:
Ubuntu uses apt, macOS uses pixi/RoboStack, Windows uses wsl2 bootstrap.
Debian/Fedora have no route, even if apt is installed. An absent pixi does not
block selecting a pixi installation recipe. The OS/version/ROS distribution
combination is supported only when an exact evidenced recipe exists.

`--ros-distro` must be supplied from the caller's resolved project configuration.
The detector does not assume an installed ROS distribution, parse Makefiles,
choose a default, or silently substitute another distribution. A recorded fixture
can explicitly represent an unknown configured ROS distribution.

## Recipe JSON version 1

A catalog has exactly `{"schema_version": 1, "recipes": []}`. Every recipe has
exactly `id`, `platform`, `operation`, `verification`, `commands`, `guidance`.
Identities are nonempty identifiers composed of letters, digits, dots, dashes,
and underscores, beginning with an alphanumeric character; duplicates fail.

`platform` has exactly `os`, `version`, `architecture`, `route`, `ros_distro`,
`context`. OS is ubuntu/macos/windows; architecture is amd64/arm64; route is
apt/pixi/wsl2 respectively. Version and distro are identifiers. Context is
native/wsl; wsl is allowed only for Ubuntu guest recipes. These are immutable
typed values, with closed enums for OS, architecture, route, context, operation,
and verification status. Matching uses all six fields exactly. Versions are
not ranges and there is no preferred match, OS fallback, or distro fallback.
Zero matches and unknown mandatory facts return structured unsupported results;
multiple matches return `ambiguous-selection`, never first-match wins.

`verification` has exactly `status`, `reference`, `date`, `procedure`, `subject`,
`provenance`. All textual fields must be nonempty. Reference is an HTTPS
permalink; date is a real ISO YYYY-MM-DD date; subject equals the recipe id;
procedure describes reproducible steps and expected results for that recipe.
Provenance is exactly one nonempty field selected by status:

| Status | Provenance | Required external evidence |
| --- | --- | --- |
| verified-in-ci | `{"ci_run": "run identity"}` | Reproducible CI run against the selected platform/recipe |
| verified-by-hand | `{"environment": "tested OS/version/architecture details"}` | Recorded actual run on that environment |
| community-reported | `{"report": "report identity"}` | An attributable community report with reproduction details |

Validation establishes evidence shape and recipe identity binding; it cannot
establish that a URL is truthful or its contents match the claim. Evidence must
be reviewed before admitting production recipes. There is no unchecked/draft
status and no invented evidence fallback. Tests use example.invalid references
explicitly labeled synthetic; these are schema fixtures, never shipped recipes.

`commands` is a nonempty array of objects with exactly `argv`, a nonempty array
of tokens. Tokens are either `{"literal": "fixed text"}` or
`{"parameter": "workspace"}`. The executable token must be literal. Parameter
references must belong to the operation contract, and every required parameter
must be represented. Missing/extra token fields, control characters, empty
values, unknown references and shell-string commands fail validation. These
are structured data, **never evaluated or executed**. No string interpolation
or placeholder scanning occurs. `guidance` is an array of nonempty strings.

## Operations and parameters

Request JSON has exactly `operation` and `parameters`, with exactly the required
keys below. All parameter values are nonempty strings without control characters (C0, DEL, or C1).

| Operation | Parameters | Semantic obligation for future recipe authors |
| --- | --- | --- |
| install | none | Bootstrap the exact OS/route/ROS distribution |
| session | workspace | Setup environment and source the workspace overlay |
| shell | workspace | Enter an appropriately configured native shell |
| turtlesim | workspace | Run turtlesim with a suitable display |
| teleop | workspace | Run turtlesim keyboard teleoperation in an interactive terminal |
| package | workspace, package, build_type | Bare package creation only |
| package-template | workspace, package, build_type, template | Complete pubsub/param source files and build metadata |
| package-interfaces | workspace, package | Complete msg/srv definitions and generator/dependency wiring |
| build-workspace | workspace | Build the entire workspace and provide overlay guidance |
| test-workspace | workspace | Test the entire workspace and report all workspace results |
| build | workspace, package | Package selection and subsequent overlay guidance |
| run | workspace, package, node | Source overlay and run the requested executable |
| test | workspace, package | Package-scoped tests and matching package-scoped test-result reporting |
| container-maintenance | none | Explicitly unsupported; cannot have a native recipe |

An omitted Make PKG maps to build-workspace/test-workspace. Single-package
build/test never matches these cases; multiple-package requests are explicitly
unmodeled and rejected rather than joined into shell text.

Build type is ament_cmake/ament_python; template is pubsub/param. Full template
and interface operations cannot match a bare creation recipe. JSON shape alone
cannot verify completeness of source files, correct overlay setup, test-result
paths, or GUI suitability: recipe admission and verification must cover these
semantic obligations. Template and interface recipes are not included.

## Consumer boundary

Python dispatch uses these parser/classifier/selector functions. Other consumers should use them or
invoke this CLI, rather than reimplementing OS matching. The Python file can be
loaded with `runpy.run_path`; its main guard performs no work on import.
`parse_facts`, `parse_catalog`, and `parse_request` return `Parsed(value)` or
`Error(code, message)`. `classify` accepts parsed facts and performs no I/O.
`select` accepts immutable recipes, classified facts and an `Operation`, and
returns a single `Parsed(Recipe)` or structured `Error`.

CLI selection returns `recipe` in the catalog's JSON shape plus `parameters`
unchanged as a separate object. The consumer substitutes parameter tokens as
single argv elements. A display renderer shell-quotes each resulting element
at its own boundary; parameter values never change recipe structure. Selection is not execution authorization. Rendering and opt-in dispatch are described below; the model never installs software or accesses the network.


## Student dispatch and current coverage

`make choose` or `.\ros2.ps1 choose` saves the preference. OFF runs the existing
container workflow; ON prints evidenced native Bash commands before it. ONLY
prints and exits before workflow prerequisites, engine detection, desktop checks,
network, WSL or browser actions. Unsupported ONLY exits nonzero; unsupported ON
continues the container workflow. Invalid parameters stop before workflow effects.
Multiple Make goals share one explanation/validation prerequisite, including
parallel builds. Help remains read-only. Selftest and its nested Make invocations
explicitly use `EXPLAIN=0` so saved preferences cannot alter its transcript.

Only exact Ubuntu 26.04/Lyrical native amd64/arm64 apt groups are candidates.
No distro or OS fallback is permitted. macOS retains the planned pixi/RoboStack
route; Windows retains WSL 2, with no verified Windows bootstrap recipe yet.
Turtlesim/teleop GUI commands, full templates/interfaces and container maintenance
currently have no admitted equivalents. A bare package recipe never substitutes
for source/configuration generated by a template. The deprecated `teleop` alias
retains its container rename guidance.

`image`/`up` correspond to installing the native system; `open` explains a native
session; `shell` enters a Bash environment; package/build/run/test use the actual
ROS CLI. Omitted PKG selects explicit workspace build/test operations. A package
name selects one package, including matching `build/PACKAGE` test results.
Multiple package names and option-like names are rejected. Ubuntu rendering requires
an absolute POSIX workspace; Windows drive paths are rejected for Ubuntu. Build uses
`--symlink-install`; run/test source the built overlay. After building, source
`install/setup.bash` in each native terminal as the guidance states.
`NATIVE_WORKSPACE` defaults to an absolute `ros2_ws` under the user's home; set an
absolute path to use another workspace. Paths with spaces, Unicode or shell
metacharacters remain single quoted argv elements. Commands are intended for
Bash on Ubuntu, including when inspected through PowerShell.

Effective ROS_DISTRO follows CLI/environment, then `.env`, then project default
`lyrical`. Literal quoted `.env` assignments are accepted. Unresolved expansion
such as `${OTHER}` is rejected rather than guessing its value. Make's default
is not exported over Compose's `.env` configuration. Wrapper parameter dollar
signs are retained as data rather than evaluated as Make expressions.

## Developer rendering and JSON integration

The existing CLI additionally supports:

```text
python3 scripts/native-recipes render CATALOG.json FACTS.json REQUEST.json
python3 scripts/native-recipes render CATALOG.json FACTS.json REQUEST.json --candidate
python3 scripts/native-recipes protocol INPUT.json
python3 scripts/native-recipes request GOAL VALUES.json
python3 scripts/native-recipes configuration VALUES.json ENV_FILE
.\ros2.ps1 -NativeRecipeRequest INPUT.json
```

The protocol input has exactly `schema_version` (integer 1), `catalog`, `facts`
and `request`, containing the documented complete objects. Success emits one
JSON object with `outcome`, `schema_version`, `recipe`, `parameters`, `rendered`,
`fingerprint` and `admitted`. Unsupported selection exits 1; invalid JSON, schema
or request exits 2. Errors contain a diagnostic; the Python boundary additionally
provides its structured error code. Both boundaries reject duplicate keys,
nonfinite numbers, unknown fields/cases, invalid evidence and malformed requests.
They use the same selection/rendering functions as student dispatch and never
execute the commands. Protocol rendering deliberately permits synthetic fixtures;
`admitted` distinguishes production eligibility. No platform-spoof environment
variable or Python installation is required for the PowerShell protocol.
`request` accepts a JSON string mapping of wrapper environment values and returns
the operation/parameters. `configuration` resolves a JSON string mapping against
literal ROS_DISTRO assignments in the supplied `.env` text file. These are
developer interfaces, not new student workflows.

Each rendered command group includes verification status, reference, date and
procedure. Every argv word is single quoted, with embedded single quotes escaped
for Bash. Static literal `bash -c` snippets receive all supplied values only as
positional arguments. Supplied values never become executable script text.

CI candidates use `https://example.invalid/` evidence and cannot be admitted.
Actual CI admission requires a GitHub Actions run permalink, matching numeric
`ci_run`, and `Recipe SHA-256: HASH` in the procedure. The hash covers id, platform,
operation, commands and guidance, serialized as UTF-8 JSON with sorted object
keys, no whitespace and unescaped Unicode; verification metadata is excluded.
Changing recipe data invalidates admission. The native workflow starts with ROS
absent, executes the same rendered setup/package/build/run/test groups, bounds
process lifetimes, and publishes exact recipe fingerprints. A green run is
reviewed before evidence is recorded. No setup commands execute on a user's host
when explanations are printed.
