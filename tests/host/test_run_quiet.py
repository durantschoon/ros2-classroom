"""Black-box tests for scripts/run-quiet.

Two known-harmless Podman 3.x warnings are dropped from stderr and nothing else
is.  The wrapped command's exit status and its stdout must survive untouched,
because every container-facing make target runs through this wrapper.
"""

import unittest

from fakes import ScriptTestCase

CNI = (
    'time="2026-01-01T00:00:00-05:00" level=warning '
    'msg="Error validating CNI config file /home/x/.config/cni/net.d/ros.conflist: '
    '[plugin firewall does not support config version \\"1.0.0\\"]"'
)
SHARED_MOUNT = 'Error: /  is not a shared mount'
REAL_ERROR = "Error: no such container: desktop"


class RunQuietTests(ScriptTestCase):
    script = "run-quiet"

    def setUp(self):
        super().setUp()
        self.sandbox.link("mktemp", "grep", "cat", "rm")

    def wrapped(self, stdout="", stderr="", exit_code=0):
        self.sandbox.fake("wrapped", stdout=stdout, stderr=stderr, exit_code=exit_code)

    def go(self, *args, **env):
        env.setdefault("TMPDIR", str(self.sandbox.root))
        return self.run_script("wrapped", *args, **env)

    # --- exit status -------------------------------------------------------

    def test_the_exit_status_is_preserved(self):
        for status in (0, 1, 7):
            with self.subTest(status=status):
                self.wrapped(exit_code=status)
                self.assertStatus(self.go(), status)

    def test_the_exit_status_is_preserved_when_verbose(self):
        for status in (0, 1, 7):
            with self.subTest(status=status):
                self.wrapped(exit_code=status)
                self.assertStatus(self.go(VERBOSE="1"), status)

    def test_arguments_reach_the_wrapped_command(self):
        self.wrapped()
        self.go("up", "-d", "--force-recreate")
        self.assertEqual([["up", "-d", "--force-recreate"]], self.sandbox.argv("wrapped"))

    # --- the two filtered patterns ----------------------------------------

    def test_the_cni_warning_is_dropped_from_stderr(self):
        self.wrapped(stderr=CNI + "\n")
        run = self.go()
        self.assertEqual("", run.err, run.report())

    def test_the_shared_mount_warning_is_dropped_from_stderr(self):
        self.wrapped(stderr=SHARED_MOUNT + "\n")
        run = self.go()
        self.assertEqual("", run.err, run.report())

    def test_every_other_stderr_line_passes_through(self):
        self.wrapped(stderr="\n".join([CNI, REAL_ERROR, SHARED_MOUNT, "second real line"]) + "\n")
        run = self.go()
        self.assertEqual([REAL_ERROR, "second real line"], run.err_lines, run.report())

    def test_an_unrelated_warning_is_not_dropped(self):
        self.wrapped(stderr="level=warning msg=\"something else entirely\"\n")
        run = self.go()
        self.assertEqual(['level=warning msg="something else entirely"'], run.err_lines)

    # --- stdout is never filtered -----------------------------------------

    def test_stdout_is_untouched(self):
        self.wrapped(stdout="line one\nline two\n", stderr=CNI + "\n")
        run = self.go()
        self.assertEqual("line one\nline two\n", run.out, run.report())

    def test_a_filtered_pattern_on_stdout_is_not_dropped(self):
        """The filter is stderr-only: a command's real output is never rewritten."""
        self.wrapped(stdout=CNI + "\n" + SHARED_MOUNT + "\n")
        run = self.go()
        self.assertEqual([CNI, SHARED_MOUNT], run.out_lines, run.report())

    # --- VERBOSE -----------------------------------------------------------

    def test_verbose_disables_filtering_entirely(self):
        self.wrapped(stdout="output\n", stderr=CNI + "\n" + SHARED_MOUNT + "\n")
        run = self.go(VERBOSE="1")
        self.assertEqual([CNI, SHARED_MOUNT], run.err_lines, run.report())
        self.assertEqual("output\n", run.out)

    def test_a_verbose_value_other_than_one_still_filters(self):
        self.wrapped(stderr=CNI + "\n")
        run = self.go(VERBOSE="0")
        self.assertEqual("", run.err, run.report())


if __name__ == "__main__":
    unittest.main()
