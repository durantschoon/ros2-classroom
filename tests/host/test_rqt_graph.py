"""Black-box contract for the container's rqt_graph command wrapper."""

import subprocess

from fakes import REPO, ScriptTestCase


class RqtGraphTest(ScriptTestCase):
    script = str(REPO / "docker" / "scripts" / "rqt_graph")

    def test_no_arguments_launches_the_ros_package_executable(self) -> None:
        self.sandbox.fake("ros2")

        run = self.run_script()

        self.assertStatus(run, 0)
        self.assertEqual([["run", "rqt_graph", "rqt_graph"]], self.sandbox.argv("ros2"))
        self.assertEqual("", run.stdout)
        self.assertEqual("", run.stderr)

    def test_arguments_are_forwarded_losslessly_without_shell_evaluation(self) -> None:
        self.sandbox.fake("ros2")
        marker = self.sandbox.fake("argument-evaluated")
        args = [
            "",
            "two words",
            "tortue 🐢 東京",
            "'single' and \"double\" quotes",
            "*?[abc]",
            "$HOME; argument-evaluated | argument-evaluated &",
            "$(argument-evaluated)",
            "`argument-evaluated`",
            "first line\nsecond line",
            "; {}".format(marker),
        ]

        run = self.run_script(*args)

        self.assertStatus(run, 0)
        self.assertEqual(
            [["run", "rqt_graph", "rqt_graph"] + args], self.sandbox.argv("ros2")
        )
        self.assertFalse(self.sandbox.called("argument-evaluated"), run.report())

    def test_child_streams_and_nonzero_exit_status_are_preserved(self) -> None:
        stdout = "graph output\r\n東京\x00without final newline"
        stderr = "graph warning\r\n\x1b[31mred\x1b[0m\x00"
        self.sandbox.fake("ros2", stdout=stdout, stderr=stderr, exit_code=37)

        run = self.run_script()

        self.assertStatus(run, 37)
        self.assertEqual(stdout, run.stdout)
        self.assertEqual(stderr, run.stderr)

    def test_missing_ros2_has_a_useful_diagnostic_and_status_127(self) -> None:
        run = self.run_script()

        self.assertStatus(run, 127)
        self.assertEqual("", run.stdout)
        self.assertIn("ros2", run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_nonexecutable_ros2_has_a_useful_diagnostic_and_status_126(self) -> None:
        ros2 = self.sandbox.fake("ros2")
        ros2.chmod(0o644)

        run = self.run_script()

        self.assertStatus(run, 126)
        self.assertEqual("", run.stdout)
        self.assertIn("ros2", run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_ros2_replaces_the_wrapper_process(self) -> None:
        ros2 = self.sandbox.bin / "ros2"
        ros2.write_text(
            "#!/usr/bin/env python3\n"
            "import os\n"
            "print(os.getpid())\n"
        )
        ros2.chmod(0o755)

        with subprocess.Popen(
            [self.script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.sandbox.root),
            env=self.sandbox.environ(),
        ) as proc:
            try:
                stdout, stderr = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise

        self.assertEqual(0, proc.returncode)
        self.assertEqual(b"", stderr)
        self.assertEqual(proc.pid, int(stdout))
