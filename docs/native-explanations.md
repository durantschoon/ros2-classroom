# Native recipe developer contract

`scripts/native-recipes` is a stdlib Python 3.9 developer tool. It models recipes,
collects passive local observations, classifies hosts, and selects exact matches.
It contains **no production recipes** and executes no commands. These interfaces
are not student workflows. Existing Make/PowerShell dispatch does not call them.

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
control characters.

- `known` records available evidence; it does not certify runtime usability.
- `unknown` means a consulted source could not classify a fact.
- `none` records absence within the observation's scope (e.g. no supported tools
  on PATH, no SSH session environment markers).
- `not-observed` means the detector did not inspect that property. Missing facts
  are schema errors and cannot silently become any of these states.

`detect` returns both raw `facts` and the classified `platform`. To replay it,
pass just `schema_version` and `facts` to `classify`; classification returns the
same `platform`. The platform includes every observation plus normalized `os`,
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
kernel release containing Microsoft identifies the latter. Windows remains a
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
keys below. All parameter values are nonempty strings without control characters.

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
semantic obligations. No such recipes are included yet.

## Consumer boundary

A future dispatcher should use these parser/classifier/selector functions or
invoke this CLI, rather than reimplementing OS matching. The Python file can be
loaded with `runpy.run_path`; its main guard performs no work on import.
`parse_facts`, `parse_catalog`, and `parse_request` return `Parsed(value)` or
`Error(code, message)`. `classify` accepts parsed facts and performs no I/O.
`select` accepts immutable recipes, classified facts and an `Operation`, and
returns a single `Parsed(Recipe)` or structured `Error`.

CLI selection returns `recipe` in the catalog's JSON shape plus `parameters`
unchanged as a separate object. The consumer substitutes parameter tokens as
single argv elements. A display renderer shell-quotes each resulting element
at its own boundary; parameter values never change recipe structure. Selection
is not execution authorization, and this model has no renderer, installation,
workflow dispatch, network access, or container integration.
