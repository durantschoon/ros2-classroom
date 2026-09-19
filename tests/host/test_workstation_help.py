"""Black-box tests for scripts/workstation-help and the Makefile's help mode.

The second half runs the real ``make``: `make shell help` is a trick (make has
no subcommands), and the property that matters most is a negative one -- no
real target may run when help or examples is on the command line.
"""

import os
import shutil
import subprocess
import unittest

from fakes import REPO, Run, ScriptTestCase

BOLD = "\033[1m"
TOPICS = ("shell", "package", "build", "run", "test")
SECTIONS = ("help", "examples")


class OverviewTests(ScriptTestCase):
    script = "workstation-help"

    def test_groups_appear_in_the_order_a_student_meets_them(self):
        run = self.run_script()
        self.assertStatus(run, 0)
        positions = [run.out.index(title) for title in (
            "Start here", "Every session", "Your own packages",
            "When something looks wrong", "Working on this project")]
        self.assertEqual(positions, sorted(positions), run.report())

    def test_every_student_target_is_listed(self):
        run = self.run_script()
        for target in ("doctor", "image", "up", "open", "turtlesim", "turtlesim-teleop",
                       "shell", "down", "package", "build", "run", "test",
                       "engine", "logs", "selftest", "check", "lint", "digest", "reset"):
            self.assertHas(run, "make " + target)

    def test_the_url_and_the_compose_command_are_the_ones_passed_in(self):
        run = self.run_script("--url", "http://localhost:7000", "--compose", "podman-compose")
        self.assertHas(run, "http://localhost:7000")
        self.assertHas(run, "Container engine: podman-compose")

    def test_piped_output_marks_topics_with_a_star_and_has_no_escapes(self):
        run = self.run_script()
        self.assertNotIn("\033", run.stdout, run.report())
        self.assertHas(run, "Targets marked * have more to say")
        starred = [line for line in run.out_lines if line.startswith("* ")]
        self.assertEqual(len(TOPICS), len(starred), run.report())
        for topic in TOPICS:
            self.assertTrue(any(line.startswith("* make " + topic) for line in starred),
                            "{} is not starred\n{}".format(topic, run.report()))

    def test_forced_colour_bolds_exactly_the_topics(self):
        run = self.run_script(CLICOLOR_FORCE="1")
        for topic in TOPICS:
            self.assertIn(BOLD + "make " + topic, run.stdout, run.report())
        self.assertNotIn(BOLD + "make up", run.stdout, run.report())
        self.assertNotIn("\n* ", run.stdout, run.report())

    def test_no_color_wins_over_forced_colour(self):
        run = self.run_script(CLICOLOR_FORCE="1", NO_COLOR="1")
        self.assertNotIn("\033", run.stdout, run.report())
        self.assertHas(run, "Targets marked *")


class TopicTests(ScriptTestCase):
    script = "workstation-help"

    def test_every_topic_has_help_and_examples(self):
        for topic in TOPICS:
            for section in SECTIONS:
                with self.subTest(topic=topic, section=section):
                    run = self.run_script(topic, section)
                    self.assertStatus(run, 0)
                    self.assertTrue(run.out_lines[0].startswith("make " + topic + " -- "),
                                    run.report())
                    self.assertGreater(len(run.out_lines), 8, run.report())

    def test_a_topic_alone_means_its_help(self):
        self.assertEqual(self.run_script("shell").out, self.run_script("shell", "help").out)

    def test_word_order_does_not_matter(self):
        self.assertEqual(self.run_script("shell", "examples").out,
                         self.run_script("examples", "shell").out)

    def test_both_sections_can_be_asked_for_at_once(self):
        run = self.run_script("package", "help", "examples")
        self.assertHas(run, "make package -- create a ROS package")
        self.assertHas(run, "make package -- examples")

    def test_shell_help_names_the_real_compose_command(self):
        run = self.run_script("shell", "help", "--compose", "docker compose")
        self.assertHas(run, "docker compose run --rm shell")

    def test_shell_examples_teach_the_service_type_lookup(self):
        # Tutorials for older ROS releases say turtlesim/srv/Spawn, which fails
        # here.  The example must use the working type AND show how to find it.
        run = self.run_script("shell", "examples")
        self.assertHas(run, "ros2 service type /spawn")
        self.assertHas(run, "ros2 service call /spawn turtlesim_msgs/srv/Spawn")

    def test_examples_print_literal_braces_for_yaml_arguments(self):
        run = self.run_script("shell", "examples")
        self.assertHas(run, '"{linear: {x: 2.0}}"')
        self.assertLacks(run, "{{")

    def test_prose_fits_a_terminal(self):
        # Commands may run long, since they must paste as one line; prose may not.
        for topic in TOPICS:
            for section in SECTIONS:
                for line in self.run_script(topic, section).out_lines:
                    if line.lstrip().startswith(("ros2 ", "make ", "colcon ", "pkg ")):
                        continue
                    with self.subTest(topic=topic, section=section, line=line):
                        self.assertLessEqual(len(line), 79)

    def test_examples_alone_lists_the_topics(self):
        run = self.run_script("examples")
        self.assertStatus(run, 0)
        for topic in TOPICS:
            self.assertHas(run, topic)

    def test_an_unknown_target_is_refused_and_says_nothing_ran(self):
        run = self.run_script("up", "help")
        self.assertStatus(run, 2)
        self.assertEqual("", run.out)
        self.assertHas(run, "No extra help for: up", where="stderr")
        self.assertHas(run, "Nothing was run.", where="stderr")

    def test_a_reader_that_closes_the_pipe_early_gets_no_traceback(self):
        proc = subprocess.Popen([str(REPO / "scripts" / "workstation-help"), "shell", "examples"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=self.sandbox.environ())
        proc.stdout.readline()
        proc.stdout.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace")
        proc.stderr.close()
        proc.wait(timeout=30)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("BrokenPipeError", stderr)


@unittest.skipIf(shutil.which("make") is None, "make is not installed")
class MakeHelpModeTests(unittest.TestCase):
    """The real Makefile.  COMPOSE=false makes any target that really ran fail."""

    def make(self, *goals: str) -> Run:
        env = dict(os.environ)
        env.pop("MAKEFLAGS", None)
        env.pop("CLICOLOR_FORCE", None)
        proc = subprocess.run(["make", "--no-print-directory", "COMPOSE=false", "ENGINE=none"]
                              + list(goals), cwd=str(REPO), env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False, timeout=120)
        return Run(proc.returncode, proc.stdout.decode("utf-8", errors="replace"),
                   proc.stderr.decode("utf-8", errors="replace"))

    def test_make_shell_help_prints_help_and_never_enters_a_shell(self):
        run = self.make("shell", "help")
        self.assertEqual(0, run.status, run.report())
        self.assertIn("make shell -- a ROS command line", run.out)
        self.assertNotIn("Entering a ROS shell", run.out)

    def test_either_word_order_prints_the_topic_once(self):
        for goals in (("package", "examples"), ("examples", "package")):
            with self.subTest(goals=goals):
                run = self.make(*goals)
                self.assertEqual(0, run.status, run.report())
                self.assertEqual(1, run.out.count("make package -- examples"), run.report())
                self.assertNotIn("ROS 2 tutorial workstation", run.out)

    def test_make_variables_may_ride_along(self):
        run = self.make("run", "PKG=my_robot", "NODE=talker", "help")
        self.assertEqual(0, run.status, run.report())
        self.assertIn("make run -- run one of your nodes", run.out)

    def test_help_beside_a_target_without_help_runs_nothing(self):
        run = self.make("up", "help")
        self.assertEqual(2, run.status, run.report())
        self.assertIn("Nothing was run.", run.err)
        self.assertNotIn("The desktop is starting", run.out)

    def test_plain_make_help_is_still_the_overview(self):
        run = self.make("help")
        self.assertEqual(0, run.status, run.report())
        self.assertIn("ROS 2 tutorial workstation", run.out)
        self.assertIn("Start here", run.out)


if __name__ == "__main__":
    unittest.main()
