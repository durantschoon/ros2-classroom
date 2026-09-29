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

import os
import re
import shutil
import subprocess
import unittest
from typing import List

from fakes import REAL_PATH, REPO, Run, ScriptTestCase, strip_ansi

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


if __name__ == "__main__":
    unittest.main()
