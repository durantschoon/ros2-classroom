"""Black-box tests for scripts/smoke-container, the suite that judges everything else.

`make selftest` is the oracle every port in this project is measured against, and
nothing measured *it*.  These tests do, from outside: the suite runs as a
subprocess on a sandbox PATH where the compose command, the container engine,
`sleep` and `curl` are all fakes, so no container, no engine and no network is
needed, and one whole run of the suite takes about a second.

Three properties exist because of real incidents and are pinned hardest:

* **Project isolation.**  The suite once ran in a student's own compose project,
  and its cleanup, which is `down -v`, destroyed the student's /workspace.  Every
  compose call must now carry `-p ros2-tutorials-selftest`.
* **ROS graph isolation.**  The suite once shared the student's ROS domain, so a
  student's own talker could satisfy the suite's DDS check.  It must run with its
  own `ROS_DOMAIN_ID`.
* **Cleanup.**  It must always end with `down -v --remove-orphans` -- and never
  when `--keep` was asked for.

A full run of the suite is the unit of work here, so each distinct scenario is
run once and shared by the tests that read it; see `scenario()`.  What the fakes
stand in for, and why each real tool is on the sandbox PATH, is in
tests/host/README.md.  Stdlib only, Python 3.9-compatible.
"""

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from fakes import REPO, Run, Sandbox, rule, strip_ansi

SCRIPT = REPO / "scripts" / "smoke-container"

# The suite's own defaults, as scripts/smoke-container sets them.
PROJECT = "ros2-tutorials-selftest"
STUDENT_PROJECT = "ros2-tutorials"
HOST_PORT = "6081"
CONTAINER_PORT = "6080"
DOMAIN = "99"
STUDENT_DOMAIN = "42"

# The real tools the suite reaches for on the host.  Found by running it under an
# almost-empty PATH and reading the "command not found" lines, not by reading the
# script.  `python3` is linked by Sandbox itself, for the fakes' own shebang.
REAL_TOOLS = (
    "bash",  # the suite's own interpreter, via /usr/bin/env
    "dirname",  # cd "$(dirname "$0")/.."
    "seq",  # the readiness loop
    "grep",  # every output assertion the suite makes
    "tail",  # truncating captured output
    "head",  # the Xvfb user probe
    "tr",  # the Xvfb user probe, and tutorial list's error text
    "awk",  # the md5sum probes
    "make",  # the "student make targets" step runs the real Makefile
)

# Environment variables recorded with every compose call: the suite's isolation
# is expressed by exporting these before it runs compose at all.
RECORDED = ("ROS_DOMAIN_ID", "NOVNC_PORT", "COMPOSE")

MISSING_TOOLS = [name for name in REAL_TOOLS if shutil.which(name) is None]
NEEDS_TOOLS = (
    "scripts/smoke-container is bash and drives the real Makefile; this machine "
    "is missing {}".format(", ".join(MISSING_TOOLS) or "nothing")
)

# Two of the suite's redirections land in the HOST's /tmp.  Recorded at import so
# a test can tell files this session wrote from ones left by an earlier run.
SESSION_START = time.time()


def git_status() -> Optional[str]:
    """The repository's porcelain status, or None where git is unavailable."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace")


# Taken before any scenario has run, so the comparison is "did a run of the
# suite change anything", not "is the working tree clean right now".
GIT_STATUS_AT_IMPORT = git_status()


# --- the all-pass scenario, as data -----------------------------------------
#
# One row per canned reply.  The suite sends each container command as a single
# argument to `bash -lc`, often a whole multi-line script, so rows match by
# substring ("contains") rather than by argv position.  ORDER MATTERS: the first
# matching row wins, so a row whose text is contained in a longer command has to
# come after that longer command's row.  Anything not listed gets the default
# reply -- exit 0, no output -- which is what most checks want.

HAPPY_COMPOSE_RULES: Sequence[Dict[str, object]] = (
    # The source-workspace build script mentions `init-workspace` and `colcon
    # build ... smoke_pkg`, so it must be answered before the rows for those.
    rule(["mkdir -p /workspace/src/smoke_pkg"], match="contains"),
    # `pkg test pkg_smoke_pubsub` appears inside the deliberately-broken script
    # too, and that one has to fail; answer the broken one first.
    rule(["/tmp/pkg-smoke-broken.log"], exit_code=1, match="contains"),
    rule(["ps", "-o", "user=", "-C", "Xvfb"], stdout="ros\n", match="all"),
    rule(
        ["ros2 pkg executables turtlesim"],
        stdout="turtlesim turtlesim_node\nturtlesim turtle_teleop_key\n",
        match="contains",
    ),
    rule(
        ["timeout 30 ros2 topic echo --once /chatter"],
        stdout="data: hello from the talker service\n---\n",
        match="contains",
    ),
    rule(["install-ros-packages definitely-not-a-package"], exit_code=1, match="contains"),
    rule(
        ["ros2 run smoke_pkg smoke_node"],
        stdout="smoke_pkg overlay works\n",
        match="contains",
    ),
    rule(
        ["nohup ros2 run pkg_smoke_pubsub talker"],
        stdout="data: hello from pkg_smoke_pubsub\n---\n",
        match="contains",
    ),
    rule(
        ["pkg test pkg_smoke_scoped"],
        stdout="Summary: 3 tests, 0 errors, 0 failures, 0 skipped\n",
        match="contains",
    ),
    rule(
        ["pkg test pkg_smoke_pubsub"],
        stdout="Summary: 3 tests, 0 errors, 0 failures, 0 skipped\n",
        match="contains",
    ),
    # The three `make` targets, reached through the real Makefile and run-quiet.
    rule(
        ["pkg new make_smoke"],
        stdout=(
            "+ ros2 pkg create make_smoke --build-type ament_cmake "
            "--maintainer-name 'ROS Developer' --maintainer-email dev@example.com\n"
            "next: make build PKG=make_smoke\n"
        ),
        match="contains",
    ),
    rule(
        ["pkg build make_smoke"],
        stdout=(
            "+ colcon build --symlink-install --packages-select make_smoke\n"
            "next: make run PKG=make_smoke\n"
        ),
        match="contains",
    ),
    rule(
        ["pkg test make_smoke"],
        stdout="Summary: 3 tests, 0 errors, 0 failures, 0 skipped\n",
        match="contains",
    ),
    rule(
        ["cd /workspace && make turtlesim"],
        stdout="make: 'turtlesim' runs on your own computer, not inside the container\n",
        exit_code=1,
        match="contains",
    ),
    rule(
        ["md5sum /workspace/.ros-workstation"],
        stdout="9f86d081884c7d659a2feaa0c55ad015  /workspace/.ros-workstation\n",
        match="contains",
    ),
    rule(
        ["md5sum /workspace/src/smoke_pkg/package.xml"],
        stdout="0a1b2c3d4e5f60718293a4b5c6d7e8f9  /workspace/src/smoke_pkg/package.xml\n",
        match="contains",
    ),
    rule(["init-workspace"], stdout="/workspace is already initialized\n", match="contains"),
    rule(
        ["tutorial clone /tmp/smoke-upstream smoke_clone"],
        stdout=(
            "+ git -C /workspace/src clone /tmp/smoke-upstream smoke_clone\n"
            "Cloning into 'smoke_clone'...\n"
        ),
        match="contains",
    ),
    rule(["tutorial list"], stdout="smoke_clone\n", match="contains"),
    rule(
        ["tutorial build smoke_pkg"],
        stdout="+ colcon build --symlink-install --packages-select smoke_pkg\n",
        match="contains",
    ),
    rule(
        ["tutorial deps"],
        stdout=(
            "+ rosdep update --rosdistro lyrical\n"
            "+ rosdep install --from-paths /workspace/src --ignore-src "
            "--rosdistro lyrical -r -y\n"
        ),
        match="contains",
    ),
    # Bare `tutorial` and bare `pkg` match the whole argument, not a substring:
    # "tutorial" is a substring of the project name "ros2-tutorials-selftest",
    # which is on every single compose call.
    rule(
        ["tutorial"],
        stdout="usage: tutorial clone URL [DIRECTORY]\n",
        exit_code=2,
        match="all",
    ),
    rule(["pkg"], stdout="usage: pkg new NAME [options]\n", exit_code=2, match="all"),
    rule(
        ["pkg new smoke_bad_msgs"],
        stdout="interface packages must be ament_cmake\n",
        exit_code=1,
        match="contains",
    ),
    rule(
        ["pkg new smoke_pkg"],
        stdout="The directory already exists\n",
        exit_code=1,
        match="contains",
    ),
)

# `scripts/compose-command` probes the engines in order; with docker absent it
# settles on podman, and `image inspect` then has to name the image's user.
PODMAN_RULES: Sequence[Dict[str, object]] = (
    rule(["compose", "version"], stdout="podman-compose version 1.6.0\n"),
    rule(["image", "inspect"], stdout="ros\n"),
)

# Readiness probes: `in_desktop true` sends "true" as its own argument, so an
# exact-argument rule addresses the probe and nothing else.
NEVER_READY = (rule(["true"], exit_code=1, match="all"),)


def ready_after(tries: int) -> Sequence[Dict[str, object]]:
    """Fail the readiness probe `tries` times, then let it through."""
    return (rule(["true"], exit_code=1, match="all", times=tries),)


# The templated-pubsub build fails, noisily: seven lines, of which the suite
# prints the last five under the FAIL line.
PUBSUB_BUILD_FAILS: Sequence[Dict[str, object]] = (
    rule(
        ["pkg new pkg_smoke_pubsub --template pubsub --build"],
        stdout="".join("build log line {}\n".format(n) for n in range(1, 8)),
        exit_code=1,
        match="contains",
    ),
)


# --- running a scenario once, and sharing it --------------------------------


class Scenario(NamedTuple):
    run: Run
    sandbox: Sandbox

    def calls(self, name: str = "compose") -> List[List[str]]:
        return self.sandbox.argv(name)

    def envs(self, name: str = "compose") -> List[Dict[str, str]]:
        return self.sandbox.recorded_envs(name)

    def downs(self) -> List[List[str]]:
        return [argv for argv in self.calls() if "down" in argv]

    def marked(self, mark: str) -> List[str]:
        """The names on every `PASS`/`FAIL` line, in order."""
        out = []
        for raw in self.run.stdout.splitlines():
            line = strip_ansi(raw).strip()
            if line.startswith(mark + " "):
                out.append(line[len(mark) + 1 :])
        return out

    def transcript(self) -> List[Tuple[str, str]]:
        """Every step title and check line, in the order they were printed."""
        out = []
        for raw in self.run.stdout.splitlines():
            line = strip_ansi(raw).strip()
            if line.startswith("== "):
                out.append(("step", line[3:]))
            elif line.startswith("PASS "):
                out.append(("PASS", line[5:]))
            elif line.startswith("FAIL "):
                out.append(("FAIL", line[5:]))
        return out

    def summary(self) -> Tuple[int, int]:
        """The (passed, failed) pair the suite prints, as integers."""
        for line in self.run.out_lines:
            if " passed, " in line and line.endswith(" failed"):
                head, tail = line.split(" passed, ")
                return int(head.strip()), int(tail[: -len(" failed")].strip())
        raise AssertionError("no 'N passed, M failed' line\n" + self.run.report())

    def report(self) -> str:
        return self.run.report()


_CACHE: Dict[str, Scenario] = {}
_TMPDIRS: List[tempfile.TemporaryDirectory] = []


def tearDownModule() -> None:
    while _TMPDIRS:
        _TMPDIRS.pop().cleanup()
    _CACHE.clear()


def scenario(
    key: str,
    args: Sequence[str] = (),
    compose_rules: Sequence[Dict[str, object]] = (),
    curl_exit: int = 1,
    no_engine: bool = False,
    **env: Optional[str]
) -> Scenario:
    """One whole run of the suite, built and run once per distinct `key`.

    A run costs about a second, so scenarios are shared rather than repeated;
    each is read-only afterwards.
    """
    if key in _CACHE:
        return _CACHE[key]

    tmp = tempfile.TemporaryDirectory(prefix="ros2-smoke-test-")
    _TMPDIRS.append(tmp)
    sandbox = Sandbox(Path(tmp.name))
    sandbox.link(*REAL_TOOLS)
    sandbox.fake("compose", rules=compose_rules, record_env=RECORDED)
    sandbox.fake("sleep")
    sandbox.fake("curl", exit_code=curl_exit)
    if not no_engine:
        sandbox.fake("podman", rules=PODMAN_RULES)
        sandbox.fake("podman-compose", stdout="podman-compose version 1.6.0\n")

    env.setdefault("COMPOSE", "compose")
    proc = subprocess.run(
        [str(SCRIPT)] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        cwd=str(sandbox.root),
        env=sandbox.environ(**env),
        check=False,
        timeout=180,
    )
    result = Scenario(
        Run(
            proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
        ),
        sandbox,
    )
    _CACHE[key] = result
    return result


def all_fail() -> Scenario:
    """Every check fails: the fakes exit 0 but print nothing the suite wants."""
    return scenario("all_fail")


def all_pass() -> Scenario:
    """The canned transcript under which every single check passes."""
    return scenario("all_pass", compose_rules=HAPPY_COMPOSE_RULES, curl_exit=0)


@unittest.skipIf(MISSING_TOOLS, NEEDS_TOOLS)
class SmokeTest(unittest.TestCase):
    """Assertions shared by the scenario classes below."""

    def assertProjectOnEveryCall(self, case: Scenario, project: str = PROJECT) -> None:
        calls = case.calls()
        self.assertTrue(calls, case.report())
        naked = [argv for argv in calls if argv[:2] != ["-p", project]]
        self.assertEqual([], naked, "compose calls without -p {}: {}".format(project, naked))

    def assertTornDown(self, case: Scenario, project: str = PROJECT) -> None:
        calls = case.calls()
        self.assertTrue(calls, case.report())
        self.assertEqual(
            ["-p", project, "down", "-v", "--remove-orphans"], calls[-1], case.report()
        )


class ProjectIsolation(SmokeTest):
    """The suite must never share a compose project with a student's workstation."""

    def test_every_compose_call_carries_the_selftest_project(self) -> None:
        self.assertProjectOnEveryCall(all_fail())

    def test_the_happy_path_keeps_the_project_on_every_call_too(self) -> None:
        self.assertProjectOnEveryCall(all_pass())

    def test_the_project_flag_reaches_the_calls_made_through_make(self) -> None:
        case = all_pass()
        # The Makefile targets go through scripts/run-quiet, so they arrive here
        # only if the exported COMPOSE carried the flag all the way.
        via_make = [argv for argv in case.calls() if "PKG_VIA_MAKE=1" in argv]
        self.assertTrue(via_make, "no compose call came from the Makefile\n" + case.report())
        for argv in via_make:
            self.assertEqual(["-p", PROJECT], argv[:2], argv)

    def test_selftest_project_overrides_the_prefix_on_every_call(self) -> None:
        case = scenario("other_project", SELFTEST_PROJECT="other-project")
        self.assertProjectOnEveryCall(case, project="other-project")

    def test_no_call_ever_names_the_bare_student_project(self) -> None:
        for case in (all_fail(), all_pass()):
            for argv in case.calls():
                self.assertNotIn(STUDENT_PROJECT, argv, argv)

    def test_the_exported_compose_already_carries_the_project_flag(self) -> None:
        # `export COMPOSE` is what makes the Makefile targets address the
        # self-test's project, so the flag has to be in the exported value.
        for env in all_fail().envs():
            self.assertEqual("compose -p {}".format(PROJECT), env.get("COMPOSE"), env)

    def test_the_banner_names_the_isolated_project_and_the_host_port(self) -> None:
        case = all_fail()
        self.assertIn(
            "using: compose -p {}  (isolated project; host port {})".format(PROJECT, HOST_PORT),
            case.run.out,
            case.report(),
        )


class PortIsolation(SmokeTest):
    """The host port is the suite's own; inside the container it is always 6080."""

    def host_curl_urls(self, case: Scenario) -> List[str]:
        return [arg for argv in case.sandbox.argv("curl") for arg in argv if "vnc.html" in arg]

    def container_curl_urls(self, case: Scenario) -> List[str]:
        return [arg for argv in case.calls() for arg in argv if "vnc.html" in arg]

    def test_the_host_curl_targets_the_selftest_port(self) -> None:
        case = all_fail()
        urls = self.host_curl_urls(case)
        self.assertTrue(urls, "the host-side curl never asked for vnc.html")
        for url in urls:
            self.assertIn("http://127.0.0.1:{}/vnc.html".format(HOST_PORT), url)

    def test_the_in_container_check_targets_6080_regardless(self) -> None:
        case = all_fail()
        urls = self.container_curl_urls(case)
        self.assertTrue(urls, "noVNC was never probed inside the container")
        for url in urls:
            self.assertIn("http://127.0.0.1:{}/vnc.html".format(CONTAINER_PORT), url)

    def test_selftest_novnc_port_moves_only_the_host_side(self) -> None:
        case = scenario("other_port", SELFTEST_NOVNC_PORT="6099")
        self.assertIn("host port 6099", case.run.out, case.report())
        for url in self.host_curl_urls(case):
            self.assertIn("127.0.0.1:6099/vnc.html", url)
        for url in self.container_curl_urls(case):
            self.assertIn("127.0.0.1:{}/vnc.html".format(CONTAINER_PORT), url)

    def test_compose_is_told_the_host_port_through_the_environment(self) -> None:
        for env in all_fail().envs():
            self.assertEqual(HOST_PORT, env.get("NOVNC_PORT"), env)
        for env in scenario("other_port", SELFTEST_NOVNC_PORT="6099").envs():
            self.assertEqual("6099", env.get("NOVNC_PORT"), env)


class RosGraphIsolation(SmokeTest):
    """The suite's nodes must not show up in a student's ROS graph, or the reverse."""

    def test_every_compose_call_runs_in_the_selftest_domain(self) -> None:
        case = all_fail()
        envs = case.envs()
        self.assertTrue(envs, case.report())
        for env in envs:
            self.assertEqual(DOMAIN, env.get("ROS_DOMAIN_ID"), env)

    def test_the_student_default_domain_is_never_used(self) -> None:
        cases = (all_fail(), all_pass(), scenario("other_domain", SELFTEST_ROS_DOMAIN_ID="77"))
        for case in cases:
            for env in case.envs():
                self.assertNotEqual(STUDENT_DOMAIN, env.get("ROS_DOMAIN_ID"), env)

    def test_selftest_ros_domain_id_overrides_it(self) -> None:
        case = scenario("other_domain", SELFTEST_ROS_DOMAIN_ID="77")
        envs = case.envs()
        self.assertTrue(envs, case.report())
        for env in envs:
            self.assertEqual("77", env.get("ROS_DOMAIN_ID"), env)

    def test_the_domain_check_asserts_the_domain_and_rules_out_42(self) -> None:
        case = all_fail()
        probes = [argv for argv in case.calls() if any("$ROS_DOMAIN_ID" in a for a in argv)]
        self.assertTrue(probes, "the suite never checks its ROS domain inside the container")
        text = probes[-1][-1]
        self.assertIn('"$ROS_DOMAIN_ID" = "{}"'.format(DOMAIN), text)
        self.assertIn('"$ROS_DOMAIN_ID" != 42', text)

    def test_the_domain_check_follows_the_override(self) -> None:
        case = scenario("other_domain", SELFTEST_ROS_DOMAIN_ID="77")
        probes = [argv for argv in case.calls() if any("$ROS_DOMAIN_ID" in a for a in argv)]
        self.assertIn('"$ROS_DOMAIN_ID" = "77"', probes[-1][-1])


class Accounting(SmokeTest):
    """Every check is counted exactly once, and a failure cannot be overlooked."""

    def test_a_failing_run_exits_one_and_accounts_for_every_check(self) -> None:
        case = all_fail()
        self.assertEqual(1, case.run.status, case.report())
        passed, failed = case.summary()
        pass_lines = case.marked("PASS")
        fail_lines = case.marked("FAIL")
        self.assertEqual(len(pass_lines), passed, case.report())
        self.assertEqual(len(fail_lines), failed, case.report())
        self.assertEqual(passed + failed, len(pass_lines) + len(fail_lines), case.report())
        self.assertGreater(failed, 0, case.report())

    def test_the_failed_checks_list_names_each_failure_once_and_in_order(self) -> None:
        case = all_fail()
        _, failed = case.summary()
        lines = case.run.out_lines
        start = lines.index("failed checks:")
        listed = [
            line.strip()[2:] for line in lines[start + 1 :] if line.strip().startswith("- ")
        ]
        self.assertEqual(failed, len(listed), case.report())
        self.assertEqual(case.marked("FAIL"), listed, case.report())

    def test_no_check_is_counted_as_both_passed_and_failed(self) -> None:
        case = all_fail()
        self.assertEqual([], sorted(set(case.marked("PASS")) & set(case.marked("FAIL"))))

    def test_every_check_name_is_distinct_on_the_all_pass_run(self) -> None:
        names = all_pass().marked("PASS")
        duplicates = sorted({name for name in names if names.count(name) > 1})
        self.assertEqual([], duplicates, duplicates)


# The transcript stage 06 must reproduce.  Captured from the all-pass run against
# the shell implementation: a step title is ("step", title), a check ("PASS",
# name), in printed order.  The trailing "cleaning up" is printed by the EXIT
# trap and is part of the transcript.
HAPPY_TRANSCRIPT: List[Tuple[str, str]] = [
    ("step", "Build"),
    ("PASS", "image builds"),
    ("step", "Start the desktop"),
    ("PASS", "desktop container accepts commands"),
    ("step", "Image and environment"),
    ("PASS", "the image defaults to the non-root ros user"),
    ("PASS", "desktop programs run as the non-root ros user"),
    ("PASS", "ROS_DISTRO is set"),
    ("PASS", "the self-test runs in its own ROS domain, not the student default"),
    ("PASS", "ros2 is on PATH"),
    ("PASS", "rosdep is on PATH"),
    ("PASS", "colcon is on PATH"),
    ("step", "Turtlesim"),
    ("PASS", "turtlesim_node and turtle_teleop_key are installed"),
    ("PASS", "turtlesim stays alive for 5s on the virtual display"),
    ("step", "Browser desktop"),
    ("PASS", "noVNC answers inside the container"),
    ("PASS", "noVNC answers on the host at http://localhost:6081"),
    ("step", "Cross-service DDS discovery"),
    ("PASS", "a node in one service receives messages from another service"),
    ("step", "Package installation helper"),
    ("PASS", "install-ros-packages installs a ROS short name"),
    ("PASS", "installed package is runnable"),
    ("PASS", "install-ros-packages fails loudly on a missing package"),
    ("step", "Source workspace build"),
    ("PASS", "colcon builds a source package in the persistent workspace"),
    ("PASS", "new shells source the workspace overlay automatically"),
    ("step", "pkg helper: templates, interfaces, and lint"),
    ("PASS", "pkg new --template pubsub builds"),
    ("PASS", "templated package registers its talker executable"),
    ("PASS", "templated pubsub node actually publishes on /chatter"),
    ("PASS", "pkg new --interfaces builds"),
    ("PASS", "ros2 interface show works for a generated message"),
    ("PASS", "ros2 interface show works for a generated service"),
    ("PASS", "pkg test reports a clean lint result for a generated package"),
    ("PASS", "pkg test exits non-zero when a test really fails"),
    ("PASS", "pkg test reads only the tested package's results"),
    ("step", "Student make targets (run from the host, as a student would)"),
    ("PASS", "make package prints the real command and points at make build"),
    ("PASS", "printed commands quote arguments so they paste correctly"),
    ("PASS", "make build prints colcon build and points at make run"),
    ("PASS", "make test reports the real colcon test-result verdict"),
    ("PASS", "make typed inside the container explains where to run it"),
    ("step", "Container helpers: tutorial, init-workspace, pkg refusals"),
    ("PASS", "a second init-workspace reports the workspace is already initialized"),
    ("PASS", "init-workspace leaves the existing workspace marker untouched"),
    ("PASS", "tutorial with no arguments exits 2 and prints usage"),
    ("PASS", "tutorial clone echoes the real git command and succeeds"),
    ("PASS", "the clone lands in /workspace/src"),
    ("PASS", "tutorial list names the cloned repository"),
    ("PASS", "tutorial build echoes colcon build --packages-select and succeeds"),
    ("PASS", "tutorial deps echoes both rosdep commands and succeeds"),
    ("PASS", "pkg with no arguments exits 2 and prints usage"),
    ("PASS", "pkg new --python --interfaces is refused with an explanation"),
    ("PASS", "the refused interface package was never created"),
    ("PASS", "pkg new refuses to create a package that already exists"),
    ("PASS", "the existing package is byte-identical after the refusal"),
    ("step", "Persistence across container recreation"),
    ("PASS", "workspace source survives container recreation"),
    ("PASS", "built overlay survives container recreation"),
    ("step", "Result"),
    ("step", "cleaning up"),
]


class HappyPath(SmokeTest):
    """One scenario of canned replies under which nothing fails at all."""

    def test_everything_passes(self) -> None:
        case = all_pass()
        self.assertEqual(0, case.run.status, case.report())
        passed, failed = case.summary()
        self.assertEqual(0, failed, case.report())
        self.assertEqual(len(case.marked("PASS")), passed, case.report())
        self.assertEqual([], case.marked("FAIL"), case.report())
        self.assertNotIn("failed checks:", case.run.out, case.report())

    def test_the_ordered_transcript_is_what_stage_06_must_reproduce(self) -> None:
        case = all_pass()
        self.assertEqual(HAPPY_TRANSCRIPT, case.transcript(), case.report())

    def test_the_step_titles_are_in_this_order(self) -> None:
        want = [name for kind, name in HAPPY_TRANSCRIPT if kind == "step"]
        got = [name for kind, name in all_pass().transcript() if kind == "step"]
        self.assertEqual(want, got, all_pass().report())

    def test_the_check_names_are_in_this_order(self) -> None:
        want = [name for kind, name in HAPPY_TRANSCRIPT if kind == "PASS"]
        self.assertEqual(want, all_pass().marked("PASS"), all_pass().report())

    def test_the_all_fail_run_asks_the_same_checks_in_the_same_order(self) -> None:
        # The check names carry interpolated detail when they fail, so compare
        # only the count and the order of the steps.
        want = [name for kind, name in HAPPY_TRANSCRIPT if kind == "step"]
        got = [name for kind, name in all_fail().transcript() if kind == "step"]
        self.assertEqual(want, got, all_fail().report())
        self.assertEqual(
            len([n for k, n in HAPPY_TRANSCRIPT if k == "PASS"]),
            len(all_fail().marked("PASS")) + len(all_fail().marked("FAIL")),
            all_fail().report(),
        )


class Cleanup(SmokeTest):
    """The suite tears its own project down whatever happened, unless told not to."""

    def test_the_all_pass_run_ends_by_removing_its_own_project(self) -> None:
        self.assertTornDown(all_pass())

    def test_the_all_fail_run_ends_by_removing_its_own_project(self) -> None:
        self.assertTornDown(all_fail())

    def test_an_early_abort_still_removes_the_project(self) -> None:
        # The desktop never becomes ready, so the suite leaves from the middle
        # of the run.  The EXIT trap still has to fire.
        case = scenario("never_ready", compose_rules=NEVER_READY)
        self.assertEqual(1, case.run.status, case.report())
        self.assertIn("desktop container never became ready", case.run.out, case.report())
        self.assertNotIn(" passed, ", case.run.out, case.report())
        self.assertTornDown(case)

    def test_the_teardown_deletes_volumes_only_inside_the_selftest_project(self) -> None:
        for case in (all_fail(), all_pass()):
            downs = case.downs()
            self.assertTrue(downs, case.report())
            for argv in downs:
                self.assertEqual(["-p", PROJECT], argv[:2], argv)
                self.assertIn("-v", argv)

    def test_exactly_one_teardown_happens(self) -> None:
        self.assertEqual(1, len(all_pass().downs()), all_pass().downs())


class KeepFlag(SmokeTest):
    """--keep leaves the containers alone and says how to remove them."""

    def keep(self) -> Scenario:
        return scenario("keep", args=("--keep",))

    def test_keep_makes_no_down_call_at_all(self) -> None:
        case = self.keep()
        self.assertEqual([], case.downs(), case.report())

    def test_keep_prints_a_removal_hint_naming_the_isolated_project(self) -> None:
        case = self.keep()
        self.assertIn(
            "containers kept (--keep); remove them with: compose -p {} down -v".format(PROJECT),
            case.run.out,
            case.report(),
        )

    def test_keep_honours_an_overridden_project_in_its_hint(self) -> None:
        case = scenario(
            "keep_other_project", args=("--keep",), SELFTEST_PROJECT="other-project"
        )
        self.assertIn("compose -p other-project down -v", case.run.out, case.report())
        self.assertEqual([], case.downs(), case.report())

    def test_keep_still_reports_the_same_verdict(self) -> None:
        case = self.keep()
        self.assertEqual(1, case.run.status, case.report())
        self.assertEqual(all_fail().summary(), case.summary(), case.report())

    def test_without_keep_the_hint_is_not_printed(self) -> None:
        case = all_fail()
        self.assertNotIn("containers kept", case.run.out, case.report())
        self.assertIn("cleaning up", case.run.out, case.report())


class Readiness(SmokeTest):
    """The suite waits for exec to work, then gives up loudly rather than hanging."""

    def probes(self, case: Scenario) -> List[List[str]]:
        return [argv for argv in case.calls() if argv[-3:] == ["bash", "-lc", "true"]]

    def test_a_desktop_that_needs_a_few_tries_is_accepted(self) -> None:
        case = scenario("ready_after_3", compose_rules=ready_after(3))
        self.assertIn("desktop container accepts commands", case.run.out, case.report())
        self.assertNotIn("never became ready", case.run.out, case.report())
        self.assertEqual(4, len(self.probes(case)), self.probes(case))
        # It slept between the failed attempts rather than spinning.
        self.assertEqual([["2"]] * 3, case.sandbox.argv("sleep")[:3], case.sandbox.argv("sleep"))

    def test_a_retried_desktop_goes_on_to_run_the_whole_suite(self) -> None:
        case = scenario("ready_after_3", compose_rules=ready_after(3))
        self.assertIn(" passed, ", case.run.out, case.report())
        self.assertTornDown(case)

    def test_a_desktop_that_never_answers_fails_the_check_and_exits_one(self) -> None:
        case = scenario("never_ready", compose_rules=NEVER_READY)
        self.assertEqual(1, case.run.status, case.report())
        self.assertIn("desktop container never became ready", case.marked("FAIL"))
        self.assertEqual([], case.marked("PASS")[1:], case.report())
        # It dumps the container's log before giving up, and it still cleans up.
        self.assertTrue(
            any(argv[2:4] == ["logs", "desktop"] for argv in case.calls()), case.calls()
        )
        self.assertTornDown(case)

    def test_it_gives_up_rather_than_retrying_forever(self) -> None:
        case = scenario("never_ready", compose_rules=NEVER_READY)
        self.assertEqual(30, len(self.probes(case)), len(self.probes(case)))

    def test_the_readiness_probe_is_exec_not_ps(self) -> None:
        # podman-compose's `ps` takes no service argument, so readiness is
        # measured by the thing the rest of the suite needs: exec working.
        case = scenario("never_ready", compose_rules=NEVER_READY)
        self.assertEqual([], [argv for argv in case.calls() if "ps" == argv[2:3]])
        for argv in self.probes(case):
            self.assertEqual(
                ["-p", PROJECT, "exec", "-T", "-u", "ros", "-e", "DISPLAY=:1", "desktop"],
                argv[:9],
                argv,
            )


class EngineDetection(SmokeTest):
    """A missing engine costs one check, not the rest of the run.

    The shell suite died under `set -e` here: exit 1, a message on stderr, and
    no summary and no `failed checks:` list at all -- the "silently stops
    counting" failure these tests exist to guard against.  Stage 06 turned it
    into an ordinary failed check, so everything after it is still asked and
    still accounted for.
    """

    def missing(self) -> Scenario:
        return scenario("no_engine", no_engine=True)

    def test_a_missing_engine_fails_one_check_and_the_run_carries_on(self) -> None:
        case = self.missing()
        self.assertEqual(1, case.run.status, case.report())
        # It got as far as the step that needs the engine...
        self.assertIn("== Image and environment", case.run.out, case.report())
        self.assertIn("no container engine found to inspect the image", case.marked("FAIL"))
        # ...and the steps after it still ran.
        self.assertIn("== Turtlesim", case.run.out, case.report())
        self.assertIn("== Persistence across container recreation", case.run.out, case.report())
        # Nothing is lost from the accounting: the summary is printed, and the
        # new failure is named in the list under it.
        passed, failed = case.summary()
        self.assertEqual(len(case.marked("PASS")), passed, case.report())
        self.assertEqual(len(case.marked("FAIL")), failed, case.report())
        lines = case.run.out_lines
        start = lines.index("failed checks:")
        listed = [
            line.strip()[2:] for line in lines[start + 1 :] if line.strip().startswith("- ")
        ]
        self.assertIn("no container engine found to inspect the image", listed)
        self.assertIn("no working docker or podman compose found", case.run.err, case.report())

    def test_a_missing_engine_still_cleans_up(self) -> None:
        # The property that matters most survives the abort.
        self.assertTornDown(self.missing())

    def test_the_engine_is_used_to_inspect_the_image_by_name(self) -> None:
        case = all_pass()
        inspects = [
            argv for argv in case.sandbox.argv("podman") if argv[:2] == ["image", "inspect"]
        ]
        self.assertTrue(inspects, case.sandbox.argv("podman"))
        self.assertIn("--format", inspects[0])
        self.assertTrue(
            any(arg.endswith("ros2-tutorials:lyrical") for arg in inspects[0]), inspects[0]
        )


class Housekeeping(SmokeTest):
    """Behaviours found by running the suite that the stage 05 prompt did not list."""

    def test_the_first_compose_call_builds_and_the_second_starts_the_desktop(self) -> None:
        case = all_fail()
        self.assertEqual(["-p", PROJECT, "build"], case.calls()[0], case.report())
        self.assertEqual(["-p", PROJECT, "up", "-d", "desktop"], case.calls()[1], case.report())

    def test_the_demo_profile_is_named_on_both_the_up_and_the_stop(self) -> None:
        # podman-compose needs --profile on every subcommand addressing a
        # service in a profile, so the flag has to be on the stop as well.
        self.assertEqual(
            [
                ["-p", PROJECT, "--profile", "demo", "up", "-d", "talker"],
                ["-p", PROJECT, "--profile", "demo", "stop", "talker"],
            ],
            [argv for argv in all_fail().calls() if "--profile" in argv],
        )

    def test_the_container_is_recreated_before_the_persistence_step(self) -> None:
        self.assertTrue(
            any(
                argv[2:] == ["up", "-d", "--force-recreate", "desktop"]
                for argv in all_pass().calls()
            ),
            all_pass().calls(),
        )

    def test_a_run_writes_no_log_files_into_the_hosts_own_tmp(self) -> None:
        # Two `>/tmp/pkg-smoke-*.log` redirections used to sit on the HOST side
        # of the pipeline rather than inside the quoted container command, so a
        # run of the suite littered the host's own /tmp.  Stage 06 keeps that
        # output in memory instead.  The files are removed first, and the
        # scenario is one no other test shares, so a cached run cannot make
        # this pass by accident.
        paths = ("/tmp/pkg-smoke-pubsub.log", "/tmp/pkg-smoke-msgs.log")
        for path in paths:
            if os.path.exists(path):
                os.remove(path)
        scenario("no_host_tmp_writes")
        for path in paths:
            self.assertFalse(os.path.exists(path), "{} was written".format(path))

    def test_a_failing_pkg_new_shows_the_tail_of_its_output(self) -> None:
        # That captured output is not thrown away: when the check fails, its
        # last five lines are printed, indented, under the FAIL line, which is
        # what the discarded log files never allowed.
        case = scenario("pubsub_build_fails", compose_rules=PUBSUB_BUILD_FAILS)
        lines = case.run.out_lines
        marker = "FAIL pkg new --template pubsub failed to build"
        where = [i for i, line in enumerate(lines) if strip_ansi(line).strip() == marker]
        self.assertEqual(1, len(where), case.report())
        shown = lines[where[0] + 1 : where[0] + 6]
        self.assertEqual(
            ["    build log line {}".format(n) for n in range(3, 8)], shown, case.report()
        )

    @unittest.skipIf(GIT_STATUS_AT_IMPORT is None, "git is not available here")
    def test_the_repository_is_left_untouched_by_a_run(self) -> None:
        # The suite cds to the repository root and runs the real Makefile there,
        # so a run could leave something behind.  Compare against the status
        # taken before any scenario ran, not against a clean tree: this file is
        # meant to keep working while someone is editing the repository.
        all_pass()
        all_fail()
        self.assertEqual(GIT_STATUS_AT_IMPORT, git_status())


if __name__ == "__main__":
    unittest.main()
