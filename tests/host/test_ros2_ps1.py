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
        # Each refusal is "<the table's path>: <what is wrong>".  The two
        # scripts may spell the path differently: scripts/distros resolves its
        # own location, ros2.ps1 uses $PSScriptRoot as given, and where the
        # temporary directory is behind a symlink (macOS: /tmp ->
        # /private/tmp) those differ.  Both are right to name the file; the
        # spelling of a symlinked path is not what this test guards.  So each
        # path must name the table written here (os.path.samefile), and the
        # words after it must be identical.
        table_path = self.tree / "distros.json"
        for case, text in malformed_tables().items():
            with self.subTest(case=case):
                table_path.write_text(text)
                proc = subprocess.run(
                    [str(self.tree / "scripts" / "distros"), "env"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                    env=self.sandbox.environ(), check=False, timeout=60)
                script_err = proc.stderr.decode("utf-8", errors="replace").strip()
                self.assertEqual(1, proc.returncode, script_err)
                self.assertEqual(1, len(script_err.splitlines()), script_err)
                script_path, _, script_words = script_err.partition(": ")
                self.assertTrue(os.path.samefile(script_path, str(table_path)), script_err)
                run = self.run_copy("distros")
                self.assertStatus(run, 1)
                self.assertEqual(1, len(run.out_lines), run.report())
                ps1_path, _, ps1_words = run.out_lines[0].partition(": ")
                self.assertTrue(os.path.samefile(ps1_path, str(table_path)), run.report())
                self.assertEqual(script_words, ps1_words, run.report())
                self.assertFalse(self.sandbox.called("docker"), run.report())


# --- the first-run question: the same contract as scripts/explain-choice ---------

from fakes import SCRIPTS, run_on_pty  # noqa: E402  (kept beside the tests that use it)

FIRST_RUN_PROMPT = "Choose 1 or 2 [1]: "
FIRST_RUN_QUESTION = """\
One question before we start. You will only be asked once.

  1. Just run things for me in the browser workstation.
  2. Do that, AND show me the commands that should do the same thing directly
     on my own system - no container involved.

Option 2 shows commands we think work on your system, each marked with how
well it has been checked. It is not a promise.
You can change your answer at any time with: .\\ros2.ps1 choose
"""
FIRST_LINE = "One question before we start."
SAVED_ON = '{"version": 1, "explain": "on"}\n'
SAVED_OFF = '{"version": 1, "explain": "off"}\n'
UP_ARGV = [["info"], ["compose", "pull", "--ignore-pull-failures"], ["compose", "up", "-d"]]
UNREADABLE = ": the saved answer could not be read: "
CORRUPT_FILES = {
    "not JSON": "explain = on\n",
    "no explain key": '{"version": 1}\n',
    "only, which is never saved": '{"version": 1, "explain": "only"}\n',
    "an unknown version": '{"version": 2, "explain": "on"}\n',
}


class FirstRunTests(Ros2Ps1TestCase):
    """A temporary copy of ros2.ps1, distros.json and scripts/explain-choice,
    so .workstation/ is created beside the copy, never in the repository."""

    def setUp(self) -> None:
        super().setUp()
        self.tree = self.sandbox.root / "tree"
        (self.tree / "scripts").mkdir(parents=True)
        shutil.copy2(str(REPO / "ros2.ps1"), str(self.tree / "ros2.ps1"))
        shutil.copy2(str(REPO / "distros.json"), str(self.tree / "distros.json"))
        shutil.copy2(str(SCRIPTS / "explain-choice"), str(self.tree / "scripts" / "explain-choice"))
        self.saved = self.tree / ".workstation" / "preferences.json"

    def env(self, **overrides: str) -> Dict[str, str]:
        return self.sandbox.environ(
            POWERSHELL_TELEMETRY_OPTOUT="1",
            POWERSHELL_UPDATECHECK="Off",
            DOTNET_CLI_TELEMETRY_OPTOUT="1",
            **overrides
        )

    def ps1_on_pty(self, *args: str, keys: List[bytes] = (), stdout_on_pty: bool = True,
                   **overrides: str) -> Run:
        # No -NonInteractive: a student's PowerShell may ask.
        return run_on_pty([str(PWSH), "-NoProfile", "-File", str(self.tree / "ros2.ps1")]
                          + list(args), env=self.env(**overrides), cwd=self.sandbox.root,
                          keys=keys, prompt=FIRST_RUN_PROMPT if stdout_on_pty else None,
                          stdout_on_pty=stdout_on_pty, timeout=120)

    def ps1_piped(self, *args: str) -> Run:
        proc = subprocess.run(
            [str(PWSH), "-NoProfile", "-NonInteractive", "-File", str(self.tree / "ros2.ps1")]
            + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
            cwd=str(self.sandbox.root), env=self.env(), check=False, timeout=120)
        return Run(proc.returncode, strip_ansi(proc.stdout.decode("utf-8", errors="replace")),
                   strip_ansi(proc.stderr.decode("utf-8", errors="replace")))

    def explain_choice(self, *args: str, keys: List[bytes] = ()) -> Run:
        """The copy of scripts/explain-choice, on a pty when keys are given."""
        argv = [str(self.tree / "scripts" / "explain-choice")] + list(args)
        if keys:
            return run_on_pty(argv, env=self.sandbox.environ(), cwd=self.sandbox.root,
                              keys=keys, prompt=FIRST_RUN_PROMPT)
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.DEVNULL, cwd=str(self.sandbox.root),
                              env=self.sandbox.environ(), check=False, timeout=60)
        return Run(proc.returncode, proc.stdout.decode("utf-8", errors="replace"),
                   proc.stderr.decode("utf-8", errors="replace"))

    def save(self, text: str) -> None:
        self.saved.parent.mkdir(exist_ok=True)
        self.saved.write_text(text)

    def assertNothingSaved(self, run: Run) -> None:
        self.assertFalse((self.tree / ".workstation").exists(), run.report())

    # 19
    def test_choose_on_a_pty_saves_what_explain_choice_saves(self):
        run = self.ps1_on_pty("choose", keys=[b"2\n"])
        self.assertStatus(run, 0)
        self.assertIn("Nothing is saved yet.", run.out, run.report())
        self.assertIn(FIRST_RUN_QUESTION + "\n" + FIRST_RUN_PROMPT, run.out, run.report())
        self.assertIn("Saved: option 2. You can change it at any time with: .\\ros2.ps1 choose",
                      run.out, run.report())
        self.assertEqual(SAVED_ON.encode("utf-8"), self.saved.read_bytes(), run.report())
        self.assertEqual(["preferences.json"], [p.name for p in self.saved.parent.iterdir()])
        # ros2.ps1 wrote it; explain-choice reads it.
        self.assertEqual("on\n", self.explain_choice("--show").stdout)

    def test_a_file_explain_choice_wrote_is_read_by_ros2_ps1(self):
        written = self.explain_choice("--choose", keys=[b"1\n"])
        self.assertEqual(SAVED_OFF, self.saved.read_text(), written.report())
        run = self.ps1_on_pty("choose", keys=[b"2\n"])
        self.assertStatus(run, 0)
        self.assertEqual("Your current answer: option 1.", run.out_lines[0], run.report())
        self.assertEqual(SAVED_ON, self.saved.read_text(), run.report())
        # And `up` on a terminal, with an answer saved, does not ask.
        again = self.ps1_on_pty("up", keys=[b"1\n"])
        self.assertStatus(again, 0)
        self.assertNotIn(FIRST_LINE, again.out, again.report())
        self.assertEqual(SAVED_ON, self.saved.read_text(), again.report())

    def test_desktop_asks_once_before_it_starts_anything(self):
        # docker info fails, so desktop stops in its first step, up: after the
        # question, before open would wait for a desktop.
        self.sandbox.fake("docker", rules=[rule(["info"], exit_code=1)])
        run = self.ps1_on_pty("desktop", keys=[b"2\n"])
        self.assertEqual(1, run.out.count(FIRST_LINE), run.report())
        self.assertEqual(SAVED_ON, self.saved.read_text(), run.report())
        self.assertLess(run.out.index(FIRST_LINE),
                        run.out.index("the Docker engine is not running"), run.report())

    # 20
    def test_up_without_a_terminal_asks_nothing_and_runs_as_before(self):
        run = self.ps1_piped("up")
        self.assertStatus(run, 0)
        self.assertNotIn(FIRST_LINE, run.out + run.err, run.report())
        self.assertNothingSaved(run)
        self.assertEqual(UP_ARGV, self.sandbox.argv("docker"))

    def test_a_terminal_for_input_but_captured_output_is_no_terminal(self):
        # An answer is typed anyway, so a script that asked would save it.
        run = self.ps1_on_pty("up", keys=[b"2\n"], stdout_on_pty=False)
        self.assertStatus(run, 0)
        self.assertNotIn(FIRST_LINE, run.out + run.err, run.report())
        self.assertNothingSaved(run)
        self.assertEqual(UP_ARGV, self.sandbox.argv("docker"))

    # 21
    def test_explain_on_the_command_line_or_in_the_environment_means_no_question(self):
        for args, overrides in ((("up", "EXPLAIN=1"), {}), (("up",), {"EXPLAIN": "1"})):
            with self.subTest(args=args, env=overrides):
                run = self.ps1_on_pty(*args, keys=[b"2\n"], **overrides)
                self.assertStatus(run, 0)
                self.assertNotIn(FIRST_LINE, run.out, run.report())
                self.assertNothingSaved(run)
                self.assertEqual(UP_ARGV, self.sandbox.argv("docker")[-3:])

    # 22
    def test_a_corrupt_file_is_said_in_explain_choices_words_and_asked_again(self):
        for case, text in CORRUPT_FILES.items():
            with self.subTest(case=case):
                self.save(text)
                expected = self.explain_choice("--show")
                self.assertEqual("off\n", expected.stdout, expected.report())
                expected_path, _, expected_words = expected.err.strip().partition(UNREADABLE)
                run = self.ps1_on_pty("up", keys=[b"2\n"])
                self.assertStatus(run, 0)
                said = [line for line in run.out_lines if UNREADABLE in line]
                self.assertEqual(1, len(said), run.report())
                path, _, words = said[0].partition(UNREADABLE)
                self.assertTrue(os.path.samefile(path, str(self.saved)), run.report())
                self.assertTrue(os.path.samefile(expected_path, str(self.saved)), expected.report())
                self.assertEqual(expected_words, words, run.report())
                self.assertIn(FIRST_RUN_QUESTION, run.out, run.report())
                self.assertEqual(SAVED_ON, self.saved.read_text(), run.report())

    def test_a_corrupt_file_without_a_terminal_is_said_and_left_alone(self):
        text = CORRUPT_FILES["not JSON"]
        self.save(text)
        run = self.ps1_piped("up")
        self.assertStatus(run, 0)
        self.assertEqual(1, sum(UNREADABLE in line for line in run.out_lines), run.report())
        self.assertNotIn(FIRST_LINE, run.out, run.report())
        self.assertEqual(text, self.saved.read_text(), run.report())
        self.assertEqual(UP_ARGV, self.sandbox.argv("docker"))


if __name__ == "__main__":
    unittest.main()
