"""Black-box tests for scripts/ci-annotate."""

from fakes import ScriptTestCase

SUITE_OUTPUT = (
    "== Build\n"
    "  \x1b[32mPASS\x1b[0m image builds\n"
    "  \x1b[31mFAIL\x1b[0m noVNC did not answer on the host port 6081\n"
    "1 passed, 1 failed\n"
)


class CiAnnotateTests(ScriptTestCase):
    script = "ci-annotate"

    def suite(self, exit_code: int) -> None:
        self.sandbox.fake("the-suite", stdout=SUITE_OUTPUT, exit_code=exit_code)

    def test_output_streams_through_unchanged(self):
        self.suite(1)
        run = self.run_script("smoke", "--", "the-suite")
        self.assertTrue(run.stdout.startswith(SUITE_OUTPUT), run.report())

    def test_a_failure_is_annotated_with_each_fail_line_and_the_tail(self):
        self.suite(1)
        run = self.run_script("smoke", "--", "the-suite")
        self.assertStatus(run, 1)
        self.assertHas(run, "::error title=smoke::FAIL noVNC did not answer on the host port 6081")
        self.assertHas(run, "::error title=smoke (last lines)::")
        # Newlines inside one annotation are escaped, and colour is stripped.
        self.assertHas(run, "1 passed%2C 1 failed".replace("%2C", ","))
        self.assertHas(run, "%0A")
        annotation_lines = [l for l in run.stdout.splitlines() if l.startswith("::error")]
        self.assertTrue(all("\x1b" not in l for l in annotation_lines), run.report())

    def test_success_is_not_annotated(self):
        self.suite(0)
        run = self.run_script("smoke", "--", "the-suite")
        self.assertStatus(run, 0)
        self.assertLacks(run, "::error")

    def test_the_exit_status_is_the_commands(self):
        self.suite(7)
        self.assertStatus(self.run_script("smoke", "--", "the-suite"), 7)

    def test_a_missing_command_is_an_annotation_not_a_traceback(self):
        run = self.run_script("smoke", "--", "no-such-command")
        self.assertStatus(run, 127)
        self.assertHas(run, "::error title=smoke::could not run no-such-command")
        self.assertLacks(run, "Traceback", where="stderr")

    def test_bad_usage_exits_two(self):
        run = self.run_script("smoke")
        self.assertStatus(run, 2)
        self.assertHas(run, "usage: ci-annotate", where="stderr")
