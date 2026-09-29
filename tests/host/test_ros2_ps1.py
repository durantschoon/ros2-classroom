"""Black-box tests for ros2.ps1, the Windows stand-in for the Makefile.

The promise the README makes is that every student-facing `make TARGET` is
`.\\ros2.ps1 TARGET` with the same arguments.  These tests hold it to that:
the target list comes from scripts/workstation-help's overview, the same
source `make help` prints, so a new Makefile target without a ros2.ps1
counterpart fails here.

ros2.ps1 runs under PowerShell 7 (`pwsh`), which GitHub's ubuntu runners
ship; the tests are skipped where there is none.  Set PWSH to point at one
that is not on PATH.  As with every test here, a fake `docker` stands in for
the engine, and only output, exit status, and the fake's recorded argv are
asserted on.
"""

import json
import os
import re
import shutil
import subprocess
import unittest
from typing import List
from typing import Dict

from fakes import REAL_PATH, REPO, Run, ScriptTestCase, strip_ansi
from fakes import COMPOSE_IMAGE, malformed_tables, rule
from typing import Tuple

PWSH = os.environ.get("PWSH") or shutil.which("pwsh", path=REAL_PATH)

# Targets for people working on the workstation itself, not for students.
MAINTAINER_TARGETS = {"selftest", "check", "lint", "digest"}


def student_targets() -> List[str]:
    """Every `make TARGET` the overview names, less the maintainer-only ones."""
    proc = subprocess.run(
        [str(REPO / "scripts" / "workstation-help")],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    text = strip_ansi(proc.stdout.decode("utf-8", errors="replace"))
    # Table rows only (`  make up   Start...`, `* make build ...` when piped),
    # not prose such as "make does not work in there".
    named = re.findall(r"^[ *]*make ([a-z][a-z-]*) ", text, re.MULTILINE)
    return sorted(set(named) - MAINTAINER_TARGETS)


@unittest.skipUnless(PWSH, "pwsh (PowerShell 7) is not installed; set PWSH to one")
class Ros2Ps1TestCase(ScriptTestCase):
    """Runs ros2.ps1 with the sandbox's fake docker first on PATH."""

    def setUp(self) -> None:
        super().setUp()
        (self.sandbox.bin / "pwsh").symlink_to(str(PWSH))
        self.sandbox.fake("docker", record_env=("NOVNC_PORT", "ROS_DOMAIN_ID"))

    def run_ps1(self, *args: str) -> Run:
        env = self.sandbox.environ(
            # Keep pwsh from phoning home or checking for updates mid-test.
            POWERSHELL_TELEMETRY_OPTOUT="1",
            POWERSHELL_UPDATECHECK="Off",
            DOTNET_CLI_TELEMETRY_OPTOUT="1",
        )
        proc = subprocess.run(
            [str(PWSH), "-NoProfile", "-NonInteractive", "-File", str(REPO / "ros2.ps1")] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=str(self.sandbox.root),
            env=env,
            check=False,
            timeout=120,
        )
        return Run(
            proc.returncode,
            strip_ansi(proc.stdout.decode("utf-8", errors="replace")),
            strip_ansi(proc.stderr.decode("utf-8", errors="replace")),
        )

    def last_desktop_script(self) -> str:
        """The script the last `docker compose exec ... bash -lc SCRIPT` ran."""
        argv = self.sandbox.last_argv("docker")
        self.assertEqual(["bash", "-lc"], argv[-3:-1], argv)
        return argv[-1]


class ParityTests(Ros2Ps1TestCase):
    def test_the_overview_names_the_targets_this_suite_checks(self):
        # Guards the parse below: an empty list would pass every parity test.
        targets = student_targets()
        for target in ("up", "doctor", "package", "run", "uninstall"):
            self.assertIn(target, targets)

    def test_every_student_make_target_is_a_ros2_ps1_command(self):
        # `TARGET help` is accepted for every command and never runs it, so
        # this checks the command exists without starting, deleting, or
        # waiting for anything.
        for target in student_targets():
            with self.subTest(target=target):
                run = self.run_ps1(target, "help")
                self.assertNotIn("Unknown command", run.out + run.err, run.report())

    def test_help_lists_every_student_target(self):
        run = self.run_ps1("help")
        self.assertStatus(run, 0)
        listed = set(re.findall(r"^  ([a-z][a-z-]*)", run.out, re.MULTILINE))
        for target in student_targets():
            self.assertIn(target, listed, run.report())


class HelpTests(Ros2Ps1TestCase):
    def test_help_after_a_command_runs_only_the_help(self):
        run = self.run_ps1("uninstall", "help")
        for argv in self.sandbox.argv("docker"):
            self.assertNotIn("rm", argv, run.report())
            self.assertNotIn("down", argv, run.report())

    def test_topic_help_runs_workstation_help_in_the_image(self):
        self.run_ps1("build", "help")
        argv = self.sandbox.last_argv("docker")
        self.assertEqual(["compose", "run", "--rm", "-T", "--no-deps", "shell",
                          "python3", "-", "build", "help"], argv)

    def test_help_first_is_the_same_as_help_last(self):
        self.run_ps1("help", "build")
        self.assertEqual(["build", "help"], self.sandbox.last_argv("docker")[-2:])

    def test_an_unknown_command_shows_the_help_and_fails(self):
        run = self.run_ps1("bogus")
        self.assertStatus(run, 1)
        self.assertHas(run, "Unknown command: bogus")
        self.assertHas(run, "Usage:")


class ArgumentTests(Ros2Ps1TestCase):
    def test_make_style_arguments_reach_pkg(self):
        run = self.run_ps1("run", "PKG=my_robot", "NODE=talker")
        self.assertStatus(run, 0)
        self.assertEqual("pkg run my_robot talker", self.last_desktop_script())

    def test_powershell_style_arguments_reach_pkg_the_same_way(self):
        self.run_ps1("run", "-Pkg", "my_robot", "-Node", "talker")
        self.assertEqual("pkg run my_robot talker", self.last_desktop_script())

    def test_package_options_match_make_package(self):
        self.run_ps1("package", "PKG=my_robot", "TEMPLATE=pubsub", "PYTHON=1", "INTERFACES=1")
        self.assertEqual("pkg new my_robot --python --template pubsub --interfaces",
                         self.last_desktop_script())

    def test_other_assignments_become_environment_variables(self):
        self.run_ps1("ps", "NOVNC_PORT=6081", "ROS_DOMAIN_ID=7")
        self.assertEqual({"NOVNC_PORT": "6081", "ROS_DOMAIN_ID": "7"},
                         self.sandbox.last_recorded_env("docker"))

    def test_a_missing_argument_prints_the_make_style_usage(self):
        run = self.run_ps1("run", "PKG=my_robot")
        self.assertStatus(run, 2)
        self.assertHas(run, "usage: .\\ros2.ps1 run PKG=name NODE=executable")
        self.assertFalse(self.sandbox.called("docker"), run.report())

    def test_each_command_prints_the_docker_command_it_runs(self):
        run = self.run_ps1("ps")
        self.assertHas(run, "docker compose ps")


class ConfirmationTests(Ros2Ps1TestCase):
    def test_reset_without_a_terminal_or_yes_removes_nothing(self):
        run = self.run_ps1("reset")
        self.assertStatus(run, 1)
        for argv in self.sandbox.argv("docker"):
            self.assertNotIn("-v", argv, run.report())

    def test_reset_with_yes_removes_the_volumes(self):
        self.run_ps1("reset", "YES=1")
        self.assertEqual(["compose", "down", "-v", "--remove-orphans"],
                         self.sandbox.last_argv("docker"))



# --- the ROS distribution: the same resolution as scripts/distros ----------------

DISTRO_VARS = ("ROS_DISTRO", "ROS_BASE_DIGEST", "IMAGE_TAG", "COMPOSE_PROJECT_NAME")
DISTRO_TABLE = json.loads((REPO / "distros.json").read_text())


def distro_settings(name: str) -> Dict[str, str]:
    """What ros2.ps1 should hand docker for the named distribution."""
    default = name == DISTRO_TABLE["default"]
    return {
        "ROS_DISTRO": name,
        "ROS_BASE_DIGEST": DISTRO_TABLE["distros"][name]["digest"],
        "IMAGE_TAG": "latest" if default else name,
        "COMPOSE_PROJECT_NAME": "ros2-tutorials" if default else "ros2-tutorials-" + name,
    }


class DistroTests(Ros2Ps1TestCase):
    """A temporary copy of ros2.ps1 and distros.json, so a .env can sit beside
    them without touching the repository."""

    def setUp(self) -> None:
        super().setUp()
        self.sandbox.fake("docker", record_env=DISTRO_VARS)
        self.tree = self.sandbox.root / "tree"
        self.tree.mkdir()
        shutil.copy2(str(REPO / "ros2.ps1"), str(self.tree / "ros2.ps1"))
        shutil.copy2(str(REPO / "distros.json"), str(self.tree / "distros.json"))

    def run_copy(self, *args: str, **overrides: str) -> Run:
        env = self.sandbox.environ(
            POWERSHELL_TELEMETRY_OPTOUT="1",
            POWERSHELL_UPDATECHECK="Off",
            DOTNET_CLI_TELEMETRY_OPTOUT="1",
            **overrides
        )
        proc = subprocess.run(
            [str(PWSH), "-NoProfile", "-NonInteractive", "-File", str(self.tree / "ros2.ps1")]
            + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
            cwd=str(self.sandbox.root), env=env, check=False, timeout=120,
        )
        return Run(proc.returncode,
                   strip_ansi(proc.stdout.decode("utf-8", errors="replace")),
                   strip_ansi(proc.stderr.decode("utf-8", errors="replace")))

    def test_a_named_distribution_reaches_docker(self):
        run = self.run_copy("ps", "ROS_DISTRO=jazzy")
        self.assertStatus(run, 0)
        self.assertEqual(distro_settings("jazzy"), self.sandbox.last_recorded_env("docker"))

    def test_nothing_set_gives_docker_the_default(self):
        run = self.run_copy("ps")
        self.assertStatus(run, 0)
        self.assertEqual(distro_settings("lyrical"), self.sandbox.last_recorded_env("docker"))
        self.assertEqual("latest", self.sandbox.last_recorded_env("docker")["IMAGE_TAG"])

    def test_an_unsupported_distribution_is_refused_before_docker(self):
        run = self.run_copy("ps", "ROS_DISTRO=foxy")
        self.assertStatus(run, 2)
        self.assertIn("ROS_DISTRO=foxy is not supported. Choose one of: "
                      "humble jazzy kilted lyrical", run.out + run.err, run.report())
        self.assertFalse(self.sandbox.called("docker"), run.report())

    def test_dotenv_chooses_and_the_environment_beats_it(self):
        (self.tree / ".env").write_text("# a comment\nROS_DISTRO=\"kilted\"\n")
        run = self.run_copy("ps")
        self.assertStatus(run, 0)
        self.assertEqual(distro_settings("kilted"), self.sandbox.last_recorded_env("docker"))
        run = self.run_copy("ps", ROS_DISTRO="jazzy")
        self.assertStatus(run, 0)
        self.assertEqual(distro_settings("jazzy"), self.sandbox.last_recorded_env("docker"))
        run = self.run_copy("ps", "ROS_DISTRO=humble")
        self.assertStatus(run, 0)
        self.assertEqual(distro_settings("humble"), self.sandbox.last_recorded_env("docker"))

    def test_explicit_settings_are_kept(self):
        run = self.run_copy("ps", "ROS_DISTRO=jazzy", "IMAGE_TAG=mine",
                            "COMPOSE_PROJECT_NAME=my-project")
        self.assertStatus(run, 0)
        recorded = self.sandbox.last_recorded_env("docker")
        self.assertEqual("mine", recorded["IMAGE_TAG"])
        self.assertEqual("my-project", recorded["COMPOSE_PROJECT_NAME"])

    def test_distros_prints_the_table_and_the_hint(self):
        run = self.run_copy("distros")
        self.assertStatus(run, 0)
        self.assertEqual([
            "DISTRO   UBUNTU  PORT  IMAGE TAG  COMPOSE PROJECT",
            "humble   22.04   6082  humble     ros2-tutorials-humble",
            "jazzy    24.04   6083  jazzy      ros2-tutorials-jazzy",
            "kilted   24.04   6084  kilted     ros2-tutorials-kilted",
            "lyrical  26.04   6080  latest     ros2-tutorials         (default)",
            "",
            "Choose one with ROS_DISTRO=<name>, e.g.  .\\ros2.ps1 up ROS_DISTRO=jazzy",
        ], run.out_lines)
        self.assertFalse(self.sandbox.called("docker"), run.report())

    def test_help_names_the_distribution_and_project_last(self):
        run = self.run_copy("help", "ROS_DISTRO=jazzy")
        self.assertStatus(run, 0)
        last = run.out_lines[-1]
        self.assertIn("jazzy", last, run.report())
        self.assertIn("ros2-tutorials-jazzy", last, run.report())

    def test_reset_names_the_project_it_would_remove(self):
        run = self.run_copy("reset", "ROS_DISTRO=jazzy")
        self.assertStatus(run, 1)
        self.assertHas(run, "ros2-tutorials-jazzy_ros-workspace")
        self.assertHas(run, "ros2-tutorials-jazzy_ros-home")
        for argv in self.sandbox.argv("docker"):
            self.assertNotIn("-v", argv, run.report())


# --- a port per distribution, uninstall across all of them, one table check ------

PORTS = {"humble": "6082", "jazzy": "6083", "kilted": "6084", "lyrical": "6080"}
IMAGE_NAME = COMPOSE_IMAGE.rsplit(":", 1)[0]


class DistroTreeTestCase(Ros2Ps1TestCase):
    """A temporary copy of ros2.ps1, scripts/distros and distros.json."""

    def setUp(self) -> None:
        super().setUp()
        self.tree = self.sandbox.root / "tree"
        (self.tree / "scripts").mkdir(parents=True)
        shutil.copy2(str(REPO / "ros2.ps1"), str(self.tree / "ros2.ps1"))
        shutil.copy2(str(REPO / "distros.json"), str(self.tree / "distros.json"))
        shutil.copy2(str(REPO / "scripts" / "distros"), str(self.tree / "scripts" / "distros"))

    def run_copy(self, *args: str, **overrides: str) -> Run:
        env = self.sandbox.environ(
            POWERSHELL_TELEMETRY_OPTOUT="1",
            POWERSHELL_UPDATECHECK="Off",
            DOTNET_CLI_TELEMETRY_OPTOUT="1",
            **overrides
        )
        proc = subprocess.run(
            [str(PWSH), "-NoProfile", "-NonInteractive", "-File", str(self.tree / "ros2.ps1")]
            + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
            cwd=str(self.sandbox.root), env=env, check=False, timeout=120,
        )
        return Run(proc.returncode,
                   strip_ansi(proc.stdout.decode("utf-8", errors="replace")),
                   strip_ansi(proc.stderr.decode("utf-8", errors="replace")))


class PortTests(DistroTreeTestCase):
    def test_each_distribution_hands_docker_its_own_port(self):
        self.sandbox.fake("docker", record_env=("NOVNC_PORT",))
        for name, port in PORTS.items():
            with self.subTest(distro=name):
                run = self.run_copy("ps", "ROS_DISTRO=" + name)
                self.assertStatus(run, 0)
                self.assertEqual({"NOVNC_PORT": port}, self.sandbox.last_recorded_env("docker"))

    def test_an_explicit_port_wins(self):
        self.sandbox.fake("docker", record_env=("NOVNC_PORT",))
        run = self.run_copy("ps", "ROS_DISTRO=jazzy", "NOVNC_PORT=7000")
        self.assertStatus(run, 0)
        self.assertEqual({"NOVNC_PORT": "7000"}, self.sandbox.last_recorded_env("docker"))

    def test_open_uses_the_distributions_port(self):
        # `help` shows exactly what `open` starts, without waiting for a desktop.
        for name, port in PORTS.items():
            with self.subTest(distro=name):
                run = self.run_copy("help", "ROS_DISTRO=" + name)
                self.assertStatus(run, 0)
                self.assertHas(run, "runs: Start-Process http://127.0.0.1:{}/vnc.html?".format(port))
                self.assertHas(run, "Desktop: http://127.0.0.1:{}".format(port))
                self.assertEqual({port}, set(re.findall(r"127\.0\.0\.1:(\d+)", run.out)))


def every_distribution_docker() -> Tuple[List[Dict[str, object]], List[str], List[str]]:
    """A docker holding one container, volume and network per distribution's
    project and the self-test's, and each distribution's images; with the
    projects and images in the order uninstall should find them."""
    default = DISTRO_TABLE["default"]
    names = [default] + sorted(n for n in DISTRO_TABLE["distros"] if n != default)
    projects = [("ros2-tutorials" if n == default else "ros2-tutorials-" + n) for n in names]
    projects.append("ros2-tutorials-selftest")
    images = ([IMAGE_NAME + ":" + ("latest" if n == default else n) for n in names]
              + ["ros2-tutorials:" + n for n in names]
              + ["docker.io/library/ros@" + DISTRO_TABLE["distros"][n]["digest"] for n in names])
    rules = []
    for project in projects:
        label = "label=com.docker.compose.project=" + project
        rules.append(rule(["ps", "-a", "--filter", label], stdout=project + "-desktop-1\n"))
        rules.append(rule(["volume", "ls", "--filter", label], stdout=project + "_ros-home\n"))
        rules.append(rule(["network", "ls", "--filter", label], stdout=project + "_ros\n"))
    for image in images:
        rules.append(rule(["image", "inspect", "--format", "{{.Size}}", image],
                          stdout="2000000\n"))
    rules.append(rule(["image", "inspect"], exit_code=1))
    return rules, projects, images


class EveryDistributionUninstallTests(DistroTreeTestCase):
    def test_uninstall_lists_every_distributions_objects(self):
        rules, projects, images = every_distribution_docker()
        self.sandbox.fake("docker", rules=rules)
        run = self.run_copy("uninstall")
        self.assertStatus(run, 1)
        for project in projects:
            for thing in ("container " + project + "-desktop-1",
                          "volume    " + project + "_ros-home",
                          "network   " + project + "_ros"):
                self.assertHas(run, "  " + thing)
        for image in images:
            self.assertHas(run, "  image     {}  (2.0 MB)".format(image))
        self.assertEqual([], [argv for argv in self.sandbox.argv("docker") if "rm" in argv])

    def test_uninstall_removes_them_in_order_one_call_per_kind(self):
        rules, projects, images = every_distribution_docker()
        self.sandbox.fake("docker", rules=rules)
        run = self.run_copy("uninstall", "YES=1", "ROS_DISTRO=kilted")
        self.assertStatus(run, 0)
        removals = [argv for argv in self.sandbox.argv("docker")
                    if argv[:1] == ["rm"] or argv[1:2] == ["rm"]]
        self.assertEqual([
            ["rm", "-f"] + [p + "-desktop-1" for p in projects],
            ["volume", "rm"] + [p + "_ros-home" for p in projects],
            ["network", "rm"] + [p + "_ros" for p in projects],
            ["image", "rm"] + images,
        ], removals)


class SharedTableTests(DistroTreeTestCase):
    """The same malformed tables through scripts/distros and ros2.ps1: both
    refuse each one, in the same words."""

    def test_both_refuse_every_malformed_table_alike(self):
        table_path = self.tree / "distros.json"
        prefix = "{}: ".format(table_path)
        for case, text in malformed_tables().items():
            with self.subTest(case=case):
                table_path.write_text(text)
                proc = subprocess.run(
                    [str(self.tree / "scripts" / "distros"), "env"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                    env=self.sandbox.environ(), check=False, timeout=60)
                script_err = proc.stderr.decode("utf-8", errors="replace").strip()
                self.assertEqual(1, proc.returncode, script_err)
                self.assertTrue(script_err.startswith(prefix), script_err)
                run = self.run_copy("distros")
                self.assertStatus(run, 1)
                self.assertEqual([script_err], run.out_lines, run.report())
                self.assertFalse(self.sandbox.called("docker"), run.report())


if __name__ == "__main__":
    unittest.main()
