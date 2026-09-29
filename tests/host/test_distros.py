"""Black-box tests for scripts/distros and the Makefile's use of it.

scripts/distros finds distros.json and .env beside its own directory, so every
test runs a temporary copy of it with its own table: nothing here writes inside
the repository.  The Makefile tests likewise run a temporary copy of the
Makefile with the scripts it calls, and a fake compose command that records
the environment it was given.

The last group reads files rather than running them: the defaults written into
the Dockerfile, compose.yaml and .env.example must be the table's default.
"""

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Dict, Optional

from fakes import REPO, SCRIPTS, Run, ScriptTestCase, rule

TABLE = json.loads((REPO / "distros.json").read_text())
DIGESTS = {name: entry["digest"] for name, entry in TABLE["distros"].items()}
NAMES = "humble jazzy kilted lyrical"
NEW_DIGEST = "sha256:" + "ab" * 32
FOUR = ("ROS_DISTRO", "ROS_BASE_DIGEST", "IMAGE_TAG", "COMPOSE_PROJECT_NAME")

DEFAULT_SETTINGS = {
    "ROS_DISTRO": "lyrical",
    "ROS_BASE_DIGEST": DIGESTS["lyrical"],
    "IMAGE_TAG": "latest",
    "COMPOSE_PROJECT_NAME": "ros2-tutorials",
}
JAZZY_SETTINGS = {
    "ROS_DISTRO": "jazzy",
    "ROS_BASE_DIGEST": DIGESTS["jazzy"],
    "IMAGE_TAG": "jazzy",
    "COMPOSE_PROJECT_NAME": "ros2-tutorials-jazzy",
}
KILTED_SETTINGS = {
    "ROS_DISTRO": "kilted",
    "ROS_BASE_DIGEST": DIGESTS["kilted"],
    "IMAGE_TAG": "kilted",
    "COMPOSE_PROJECT_NAME": "ros2-tutorials-kilted",
}


def exports(text: str) -> Dict[str, str]:
    """`export NAME=value` lines as a dict; fails on any other line."""
    found = {}
    for line in text.splitlines():
        match = re.fullmatch(r"export ([A-Z_]+)=(\S+)", line)
        if match is None:
            raise AssertionError("not an export line: {!r}".format(line))
        found[match.group(1)] = match.group(2)
    return found


class DistrosTreeCase(ScriptTestCase):
    """A temporary checkout: scripts/distros, distros.json, and optionally
    .env and a fake scripts/base-image-digest."""

    def setUp(self) -> None:
        super().setUp()
        self.tree = self.sandbox.root / "tree"
        (self.tree / "scripts").mkdir(parents=True)
        shutil.copy2(str(SCRIPTS / "distros"), str(self.tree / "scripts" / "distros"))
        shutil.copy2(str(REPO / "distros.json"), str(self.tree / "distros.json"))

    @property
    def table_path(self) -> Path:
        return self.tree / "distros.json"

    def write_dotenv(self, text: str) -> None:
        (self.tree / ".env").write_text(text)

    def fake_base_image_digest(self, answers: Dict[str, Optional[str]]) -> None:
        """A sibling base-image-digest answering each name; None fails."""
        rules = []
        for name, digest in answers.items():
            if digest is None:
                rules.append(rule([name], stderr="no digest for ros:{}-ros-base\n".format(name),
                                  exit_code=1))
            else:
                rules.append(rule([name], stdout=digest + "\n"))
        fake = self.sandbox.fake("base-image-digest", rules=rules, exit_code=1)
        shutil.copy2(str(fake), str(self.tree / "scripts" / "base-image-digest"))
        self.sandbox.remove("base-image-digest")

    def distros(self, *args: str, **overrides: Optional[str]) -> Run:
        proc = subprocess.run(
            [str(self.tree / "scripts" / "distros")] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=str(self.sandbox.root),
            env=self.sandbox.environ(**overrides),
            check=False,
            timeout=60,
        )
        return Run(proc.returncode, proc.stdout.decode("utf-8", errors="replace"),
                   proc.stderr.decode("utf-8", errors="replace"))

    def assertSettings(self, expected: Dict[str, str], run: Run) -> None:
        self.assertStatus(run, 0)
        self.assertEqual(expected, exports(run.out), run.report())
        self.assertEqual(list(FOUR), [line.split("=")[0][len("export "):]
                                      for line in run.out_lines], run.report())


class EnvTests(DistrosTreeCase):
    def test_nothing_set_is_the_default_under_its_old_names(self):
        self.assertSettings(DEFAULT_SETTINGS, self.distros("env"))

    def test_another_distribution_gets_its_own_names(self):
        self.assertSettings(JAZZY_SETTINGS, self.distros("env", ROS_DISTRO="jazzy"))

    def test_naming_the_default_explicitly_gives_the_default_names(self):
        self.assertSettings(DEFAULT_SETTINGS, self.distros("env", ROS_DISTRO="lyrical"))

    def test_dotenv_chooses_bare_quoted_and_after_a_comment(self):
        for text in ("ROS_DISTRO=kilted\n",
                     'ROS_DISTRO="kilted"\n',
                     "ROS_DISTRO='kilted'\n",
                     "# ROS_DISTRO=humble\n\nNOVNC_PORT=6080\nROS_DISTRO=kilted\n"):
            with self.subTest(dotenv=text):
                self.write_dotenv(text)
                self.assertSettings(KILTED_SETTINGS, self.distros("env"))

    def test_the_environment_beats_dotenv(self):
        self.write_dotenv("ROS_DISTRO=kilted\n")
        self.assertSettings(JAZZY_SETTINGS, self.distros("env", ROS_DISTRO="jazzy"))

    def test_an_empty_environment_value_falls_through_to_dotenv(self):
        self.write_dotenv("ROS_DISTRO=kilted\n")
        self.assertSettings(KILTED_SETTINGS, self.distros("env", ROS_DISTRO=""))

    def test_explicit_settings_in_the_environment_survive(self):
        run = self.distros("env", ROS_DISTRO="jazzy", ROS_BASE_DIGEST=NEW_DIGEST,
                           IMAGE_TAG="mine", COMPOSE_PROJECT_NAME="my-project")
        self.assertSettings({"ROS_DISTRO": "jazzy", "ROS_BASE_DIGEST": NEW_DIGEST,
                             "IMAGE_TAG": "mine", "COMPOSE_PROJECT_NAME": "my-project"}, run)

    def test_an_unsupported_name_from_the_environment_is_refused(self):
        run = self.distros("env", ROS_DISTRO="foxy")
        self.assertStatus(run, 2)
        self.assertEqual("", run.stdout)
        self.assertEqual(["ROS_DISTRO=foxy is not supported. Choose one of: " + NAMES],
                         run.err_lines)

    def test_an_unsupported_name_from_dotenv_is_refused(self):
        self.write_dotenv("ROS_DISTRO=rolling\n")
        run = self.distros("env", "--make")
        self.assertStatus(run, 2)
        self.assertEqual("", run.stdout)
        self.assertEqual(["ROS_DISTRO=rolling is not supported. Choose one of: " + NAMES],
                         run.err_lines)

    def test_make_form_is_four_bare_assignments(self):
        run = self.distros("env", "--make", ROS_DISTRO="jazzy")
        self.assertStatus(run, 0)
        self.assertEqual(["{}={}".format(name, JAZZY_SETTINGS[name]) for name in FOUR],
                         run.out_lines)

    def test_the_export_form_evaluates_in_a_shell(self):
        self.sandbox.link("sh")
        script = 'eval "$("$1" env)" && echo "$IMAGE_TAG $COMPOSE_PROJECT_NAME"'
        proc = subprocess.run(["sh", "-c", script, "sh", str(self.tree / "scripts" / "distros")],
                              stdout=subprocess.PIPE, env=self.sandbox.environ(ROS_DISTRO="humble"),
                              check=False)
        self.assertEqual(b"humble ros2-tutorials-humble\n", proc.stdout)


class ListTests(DistrosTreeCase):
    def test_list_shows_a_header_and_a_row_per_distribution(self):
        run = self.distros("list")
        self.assertStatus(run, 0)
        self.assertEqual([
            "DISTRO   UBUNTU  IMAGE TAG  COMPOSE PROJECT",
            "humble   22.04   humble     ros2-tutorials-humble",
            "jazzy    24.04   jazzy      ros2-tutorials-jazzy",
            "kilted   24.04   kilted     ros2-tutorials-kilted",
            "lyrical  26.04   latest     ros2-tutorials         (default)",
        ], run.out_lines)
        self.assertEqual(1, run.out.count("(default)"))

    def test_a_closed_pipe_is_not_an_error(self):
        # As `distros list | head -0`: the reader is gone before a byte is written.
        read_end, write_end = os.pipe()
        os.close(read_end)
        try:
            proc = subprocess.run([str(self.tree / "scripts" / "distros"), "list"],
                                  stdout=write_end, stderr=subprocess.PIPE,
                                  env=self.sandbox.environ(), check=False, timeout=60)
        finally:
            os.close(write_end)
        stderr = proc.stderr.decode("utf-8", errors="replace")
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("BrokenPipeError", stderr)


class RefreshTests(DistrosTreeCase):
    def test_nothing_new_leaves_the_table_byte_identical(self):
        self.fake_base_image_digest(dict(DIGESTS))
        before = self.table_path.read_bytes()
        stat_before = self.table_path.stat()
        run = self.distros("refresh")
        self.assertStatus(run, 0)
        self.assertEqual(4, len(run.out_lines), run.report())
        for name, line in zip(sorted(DIGESTS), run.out_lines):
            self.assertEqual([name, "unchanged"], line.split(), run.report())
        self.assertEqual(before, self.table_path.read_bytes())
        self.assertEqual(stat_before.st_mtime_ns, self.table_path.stat().st_mtime_ns)
        self.assertEqual(["base-image-digest " + name for name in sorted(DIGESTS)],
                         [" ".join(["base-image-digest"] + argv)
                          for argv in self.sandbox.argv("base-image-digest")])

    def test_one_new_digest_changes_only_its_own_entry(self):
        answers = dict(DIGESTS)
        answers["jazzy"] = NEW_DIGEST
        self.fake_base_image_digest(answers)
        before = self.table_path.read_text().splitlines()
        run = self.distros("refresh")
        self.assertStatus(run, 0)
        self.assertHas(run, "jazzy    {} -> {}".format(DIGESTS["jazzy"], NEW_DIGEST))
        self.assertHas(run, "make image ROS_DISTRO=jazzy")
        after = self.table_path.read_text().splitlines()
        changed = [(old, new) for old, new in zip(before, after) if old != new]
        self.assertEqual(len(before), len(after))
        self.assertEqual(1, len(changed), changed)
        self.assertEqual(changed[0][0].replace(DIGESTS["jazzy"], NEW_DIGEST), changed[0][1])
        written = json.loads(self.table_path.read_text())
        self.assertEqual(TABLE["_comment"], written["_comment"])
        self.assertEqual(NEW_DIGEST, written["distros"]["jazzy"]["digest"])
        self.assertTrue(self.table_path.read_text().endswith("}\n"))

    def test_a_failed_fetch_keeps_the_old_digest_and_fails(self):
        answers = dict(DIGESTS)  # type: Dict[str, Optional[str]]
        answers["kilted"] = None
        self.fake_base_image_digest(answers)
        before = self.table_path.read_bytes()
        run = self.distros("refresh")
        self.assertStatus(run, 1)
        self.assertHas(run, "kilted   kept {} (could not fetch)".format(DIGESTS["kilted"]))
        self.assertEqual(before, self.table_path.read_bytes())

    def test_an_answer_that_is_not_a_digest_is_not_used(self):
        answers = dict(DIGESTS)  # type: Dict[str, Optional[str]]
        answers["humble"] = "sha256:nope"
        self.fake_base_image_digest(answers)
        before = self.table_path.read_bytes()
        run = self.distros("refresh")
        self.assertStatus(run, 1)
        self.assertHas(run, "humble   kept {} (could not fetch)".format(DIGESTS["humble"]))
        self.assertHas(run, "humble: base-image-digest answered 'sha256:nope'", where="stderr")
        self.assertEqual(before, self.table_path.read_bytes())


class MalformedTableTests(DistrosTreeCase):
    def assertRefused(self, text: str, *args: str) -> None:
        self.table_path.write_text(text)
        run = self.distros(*args)
        self.assertStatus(run, 1)
        self.assertEqual("", run.stdout)
        self.assertEqual(1, len(run.err_lines), run.report())
        self.assertTrue(run.err.startswith(str(self.table_path) + ": "), run.report())
        self.assertNotIn("Traceback", run.err)

    def test_not_json(self):
        for args in (("env",), ("list",), ("refresh",)):
            with self.subTest(args=args):
                self.assertRefused("{ not json", *args)

    def test_no_distros(self):
        self.assertRefused('{"default": "lyrical"}\n', "env")

    def test_a_default_not_in_the_table(self):
        table = dict(TABLE)
        table["default"] = "rolling"
        self.assertRefused(json.dumps(table), "env")

    def test_a_missing_table(self):
        self.table_path.unlink()
        run = self.distros("env")
        self.assertStatus(run, 1)
        self.assertEqual(1, len(run.err_lines), run.report())
        self.assertTrue(run.err.startswith(str(self.table_path) + ": "), run.report())


class UsageTests(DistrosTreeCase):
    def test_no_subcommand_or_an_unknown_one_is_a_usage_error(self):
        for args in ((), ("bogus",), ("env", "--bogus"), ("list", "extra")):
            with self.subTest(args=args):
                run = self.distros(*args)
                self.assertStatus(run, 2)
                self.assertEqual("", run.stdout)
                self.assertHas(run, "usage: distros env [--make]", where="stderr")


@unittest.skipIf(shutil.which("make") is None, "make is not installed")
class MakefileTests(DistrosTreeCase):
    """A temporary copy of the Makefile, with a fake compose that records the
    environment every compose command would see."""

    def setUp(self) -> None:
        super().setUp()
        shutil.copy2(str(REPO / "Makefile"), str(self.tree / "Makefile"))
        shutil.copy2(str(SCRIPTS / "run-quiet"), str(self.tree / "scripts" / "run-quiet"))
        # require-engine only asks whether an engine exists.
        engine = self.tree / "scripts" / "compose-command"
        engine.write_text("#!/bin/sh\necho 'fake fake-compose'\n")
        engine.chmod(0o755)
        self.sandbox.fake("fake-compose", record_env=FOUR)
        # make runs a simple recipe line such as `echo ...` without a shell.
        self.sandbox.link("echo")
        self.make_path = shutil.which("make")

    def make(self, *args: str, **overrides: Optional[str]) -> Run:
        env = self.sandbox.environ(**overrides)
        proc = subprocess.run(
            [str(self.make_path), "--no-print-directory", "COMPOSE=fake-compose",
             "ENGINE=fake"] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
            cwd=str(self.tree), env=env, check=False, timeout=60)
        return Run(proc.returncode, proc.stdout.decode("utf-8", errors="replace"),
                   proc.stderr.decode("utf-8", errors="replace"))

    def test_a_command_line_distribution_reaches_compose(self):
        run = self.make("ps", "ROS_DISTRO=jazzy")
        self.assertStatus(run, 0)
        self.assertEqual(JAZZY_SETTINGS, self.sandbox.last_recorded_env("fake-compose"))

    def test_nothing_set_gives_compose_the_default(self):
        run = self.make("ps")
        self.assertStatus(run, 0)
        self.assertEqual(DEFAULT_SETTINGS, self.sandbox.last_recorded_env("fake-compose"))

    def test_an_environment_distribution_reaches_compose(self):
        run = self.make("ps", ROS_DISTRO="jazzy")
        self.assertStatus(run, 0)
        self.assertEqual(JAZZY_SETTINGS, self.sandbox.last_recorded_env("fake-compose"))

    def test_a_dotenv_distribution_reaches_compose(self):
        self.write_dotenv("ROS_DISTRO=kilted\n")
        run = self.make("ps")
        self.assertStatus(run, 0)
        self.assertEqual(KILTED_SETTINGS, self.sandbox.last_recorded_env("fake-compose"))

    def test_an_unsupported_distribution_stops_before_compose(self):
        run = self.make("ps", "ROS_DISTRO=foxy")
        self.assertNotEqual(0, run.status, run.report())
        self.assertHas(run, "ROS_DISTRO=foxy is not supported. Choose one of: " + NAMES,
                       where="stderr")
        self.assertFalse(self.sandbox.called("fake-compose"), run.report())

    def test_make_distros_lists_them_with_the_hint(self):
        run = self.make("distros")
        self.assertStatus(run, 0)
        self.assertEqual("DISTRO   UBUNTU  IMAGE TAG  COMPOSE PROJECT", run.out_lines[0])
        self.assertEqual(1, run.out.count("(default)"))
        self.assertEqual(["", "Choose one with ROS_DISTRO=<name>, e.g.  make up ROS_DISTRO=jazzy"],
                         run.out_lines[-2:])

    def test_make_digest_runs_the_refresh_and_echoes_it(self):
        self.fake_base_image_digest(dict(DIGESTS))
        run = self.make("digest")
        self.assertStatus(run, 0)
        self.assertEqual("./scripts/distros refresh", run.out_lines[0])
        self.assertEqual(4, sum("unchanged" in line for line in run.out_lines), run.report())

    def test_reset_names_the_distribution_and_its_project_and_removes_nothing(self):
        run = self.make("reset", "ROS_DISTRO=jazzy")
        self.assertStatus(run, 2)
        self.assertHas(run, "ros2-tutorials-jazzy")
        self.assertHas(run, "jazzy)")
        self.assertHas(run, "ros2-tutorials-jazzy_ros-workspace")
        self.assertHas(run, "ros2-tutorials-jazzy_ros-home")
        self.assertHas(run, "aborted; nothing was removed")
        self.assertFalse(self.sandbox.called("fake-compose"), run.report())


class ConsistencyTests(unittest.TestCase):
    """The table's default is written out in three other places."""

    default = TABLE["default"]
    digest = TABLE["distros"][TABLE["default"]]["digest"]

    def test_dockerfile_arg_defaults(self):
        text = (REPO / "Dockerfile").read_text()
        self.assertEqual([self.default], re.findall(r"^ARG ROS_DISTRO=(\S+)$", text, re.M))
        self.assertEqual([self.digest], re.findall(r"^ARG ROS_BASE_DIGEST=(\S+)$", text, re.M))

    def test_compose_build_arg_defaults(self):
        text = (REPO / "compose.yaml").read_text()
        self.assertEqual([self.default], re.findall(r"\$\{ROS_DISTRO:-([^}]*)\}", text))
        self.assertEqual([self.digest], re.findall(r"\$\{ROS_BASE_DIGEST:-([^}]*)\}", text))

    def test_env_example_distribution(self):
        text = (REPO / ".env.example").read_text()
        self.assertEqual([self.default], re.findall(r"^ROS_DISTRO=(\S+)$", text, re.M))


if __name__ == "__main__":
    unittest.main()
