"""Black-box tests for scripts/explain-choice, the first-run question.

The script finds the repository root from its own location, so every test
copies it (and, for the Makefile tests, the Makefile and the scripts it calls)
into a temporary tree and runs it there.  Nothing here writes inside the
repository.  The current directory is the sandbox, never the tree, so a script
that looked for its root in the current directory would save in the wrong
place and fail these tests.

The question is asked only on a terminal, so most tests run the script on a
pseudo-terminal (fakes.run_on_pty) and type the answers.
"""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Optional, Sequence

from fakes import REAL_PATH, REPO, SCRIPTS, Run, ScriptTestCase, run_on_pty

PROMPT = "Choose 1 or 2 [1]: "
QUESTION = """\
One question before we start. You will only be asked once.

  1. Just run things for me in the browser workstation.
  2. Do that, AND show me the commands that should do the same thing directly
     on my own system - no container involved.

Option 2 shows commands we think work on your system, each marked with how
well it has been checked. It is not a promise.
You can change your answer at any time with: make choose
"""
FIRST_LINE = "One question before we start."
SAVED_ON = '{"version": 1, "explain": "on"}\n'
SAVED_OFF = '{"version": 1, "explain": "off"}\n'
FOR_NOW = "Using option 1 for now. Nothing was saved, so you will be asked again."
UNREADABLE = ": the saved answer could not be read: "

# One saved file that cannot be read, per way it can be wrong, and the reason
# both explain-choice and ros2.ps1 give for it.
CORRUPT = {
    "not JSON": ("explain = on\n", "it is not JSON"),
    "no explain key": ('{"version": 1}\n', 'it has no "explain"'),
    "only, which is never saved": ('{"version": 1, "explain": "only"}\n',
                                   'its "explain" is neither "off" nor "on"'),
    "an unknown version": ('{"version": 2, "explain": "on"}\n', 'its "version" is not 1'),
}


class ExplainChoiceTestCase(ScriptTestCase):
    """A copy of scripts/explain-choice in <sandbox>/tree/scripts."""

    def setUp(self) -> None:
        super().setUp()
        self.tree = self.sandbox.root / "tree"
        (self.tree / "scripts").mkdir(parents=True)
        self.script = self.tree / "scripts" / "explain-choice"
        shutil.copy2(str(SCRIPTS / "explain-choice"), str(self.script))
        self.saved = self.tree / ".workstation" / "preferences.json"

    def save(self, text: str) -> None:
        self.saved.parent.mkdir(exist_ok=True)
        self.saved.write_text(text)

    def on_pty(self, *args: str, keys: Sequence[bytes] = (), stdout_on_pty: bool = True,
               **overrides: Optional[str]) -> Run:
        return run_on_pty([str(self.script)] + list(args), env=self.sandbox.environ(**overrides),
                          cwd=self.sandbox.root, keys=keys,
                          prompt=PROMPT if stdout_on_pty else None,
                          stdout_on_pty=stdout_on_pty)

    def piped(self, *args: str, **overrides: Optional[str]) -> Run:
        """stdin /dev/null, stdout and stderr pipes: no terminal at all."""
        proc = subprocess.run([str(self.script)] + list(args), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=str(self.sandbox.root), env=self.sandbox.environ(**overrides),
                              check=False, timeout=60)
        return Run(proc.returncode, proc.stdout.decode("utf-8", errors="replace"),
                   proc.stderr.decode("utf-8", errors="replace"))

    def assertSaved(self, expected: str, run: Run) -> None:
        self.assertTrue(self.saved.exists(), run.report())
        self.assertEqual(expected, self.saved.read_text(), run.report())

    def assertNothingSaved(self, run: Run) -> None:
        self.assertFalse((self.tree / ".workstation").exists(), run.report())
        self.assertFalse((self.sandbox.root / ".workstation").exists(), run.report())

    def assertNoTraceback(self, run: Run) -> None:
        self.assertNotIn("Traceback", run.out + run.err, run.report())


class AskOnceTests(ExplainChoiceTestCase):
    # 1
    def test_the_question_word_for_word_then_2_saves_on(self):
        run = self.on_pty("--ask-once", keys=[b"2\n"])
        self.assertStatus(run, 0)
        self.assertIn(QUESTION + "\n" + PROMPT, run.out, run.report())
        self.assertSaved(SAVED_ON, run)
        self.assertEqual({"version": 1, "explain": "on"}, json.loads(self.saved.read_text()))
        self.assertEqual("Saved: option 2. You can change it at any time with: make choose",
                         run.out_lines[-1], run.report())
        # Written atomically, beside the script (the current directory is the
        # sandbox, not the tree), and no temporary file left behind.
        self.assertEqual(["preferences.json"],
                         sorted(p.name for p in self.saved.parent.iterdir()), run.report())
        self.assertFalse((self.sandbox.root / ".workstation").exists(), run.report())

    def test_the_question_fits_78_columns(self):
        for line in QUESTION.splitlines():
            self.assertLessEqual(len(line), 78, line)

    # 2
    def test_1_and_enter_alone_save_off_and_spaces_are_ignored(self):
        for keys, expected in (([b"1\n"], SAVED_OFF), ([b"\n"], SAVED_OFF),
                               ([b" 2 \n"], SAVED_ON)):
            with self.subTest(keys=keys):
                if self.saved.exists():
                    self.saved.unlink()
                run = self.on_pty("--ask-once", keys=keys)
                self.assertStatus(run, 0)
                self.assertSaved(expected, run)
                option = "2" if expected == SAVED_ON else "1"
                self.assertIn("Saved: option {}.".format(option), run.out, run.report())

    # 3
    def test_an_answer_already_saved_means_no_question_and_no_output(self):
        for text in (SAVED_ON, SAVED_OFF):
            with self.subTest(saved=text):
                self.save(text)
                run = self.on_pty("--ask-once", keys=[b"2\n"])
                self.assertStatus(run, 0)
                self.assertEqual("", run.out, run.report())
                self.assertEqual(text, self.saved.read_text())

    # 4
    def test_three_unusable_answers_save_nothing(self):
        run = self.on_pty("--ask-once", keys=[b"x\n", b"3\n", b"yes\n", b"2\n"])
        self.assertStatus(run, 0)
        for typed in ("x", "3", "yes"):
            self.assertIn('"{}" is not 1 or 2.'.format(typed), run.out, run.report())
        self.assertEqual(3, run.out.count(PROMPT), run.report())
        self.assertEqual(FOR_NOW, run.out_lines[-1], run.report())
        self.assertNothingSaved(run)

    def test_an_unusable_answer_then_a_usable_one_is_saved(self):
        run = self.on_pty("--ask-once", keys=[b"maybe\n", b"2\n"])
        self.assertStatus(run, 0)
        self.assertIn('"maybe" is not 1 or 2.', run.out, run.report())
        self.assertSaved(SAVED_ON, run)

    def test_ctrl_d_means_option_1_for_now_and_saves_nothing(self):
        run = self.on_pty("--ask-once", keys=[b"\x04"])
        self.assertStatus(run, 0)
        self.assertEqual(FOR_NOW, run.out_lines[-1], run.report())
        self.assertNothingSaved(run)

    # 5
    def test_ctrl_c_saves_nothing_and_exits_130_without_a_traceback(self):
        run = self.on_pty("--ask-once", keys=[b"\x03"])
        self.assertStatus(run, 130)
        self.assertNoTraceback(run)
        self.assertNotIn("KeyboardInterrupt", run.out, run.report())
        self.assertNothingSaved(run)

    # 6
    def test_no_terminal_asks_nothing_and_saves_nothing(self):
        run = self.piped("--ask-once")
        self.assertStatus(run, 0)
        self.assertEqual(("", ""), (run.stdout, run.stderr), run.report())
        self.assertNothingSaved(run)

    # 7
    def test_a_terminal_for_input_but_captured_output_is_no_terminal(self):
        # The self-test's shape: make runs with the student's terminal as
        # stdin and its output captured.  An answer is typed anyway, so a
        # script that asked would save it.
        run = self.on_pty("--ask-once", keys=[b"2\n"], stdout_on_pty=False)
        self.assertStatus(run, 0)
        self.assertEqual(("", ""), (run.stdout, run.stderr), run.report())
        self.assertNothingSaved(run)

    # 8
    def test_explain_set_means_no_question_and_nothing_saved(self):
        for value in ("0", "1", "only"):
            with self.subTest(EXPLAIN=value):
                run = self.on_pty("--ask-once", keys=[b"2\n"], EXPLAIN=value)
                self.assertStatus(run, 0)
                self.assertEqual("", run.out, run.report())
                self.assertNothingSaved(run)

    def test_explain_with_another_value_is_refused(self):
        run = self.on_pty("--ask-once", keys=[b"2\n"], EXPLAIN="maybe")
        self.assertStatus(run, 2)
        self.assertEqual(["EXPLAIN=maybe is not understood. Use EXPLAIN=0, EXPLAIN=1 or "
                          "EXPLAIN=only."], run.out_lines, run.report())
        self.assertNothingSaved(run)


class ShowTests(ExplainChoiceTestCase):
    # 9
    def test_off_when_nothing_is_saved(self):
        run = self.piped("--show")
        self.assertStatus(run, 0)
        self.assertEqual(("off\n", ""), (run.stdout, run.stderr), run.report())
        self.assertNothingSaved(run)

    def test_the_saved_answer(self):
        for text, word in ((SAVED_ON, "on"), (SAVED_OFF, "off")):
            with self.subTest(saved=word):
                self.save(text)
                run = self.piped("--show")
                self.assertEqual(("{}\n".format(word), ""), (run.stdout, run.stderr),
                                 run.report())

    def test_each_explain_value_beats_a_saved_answer(self):
        for saved, value, word in ((SAVED_ON, "0", "off"), (SAVED_OFF, "1", "on"),
                                   (SAVED_ON, "only", "only"), (SAVED_OFF, "only", "only")):
            with self.subTest(saved=saved, EXPLAIN=value):
                self.save(saved)
                run = self.piped("--show", EXPLAIN=value)
                self.assertStatus(run, 0)
                self.assertEqual("{}\n".format(word), run.stdout, run.report())

    def test_an_empty_explain_does_not(self):
        self.save(SAVED_ON)
        run = self.piped("--show", EXPLAIN="")
        self.assertEqual("on\n", run.stdout, run.report())

    def test_explain_with_another_value_names_the_three_accepted(self):
        for value in ("maybe", "ON"):
            with self.subTest(EXPLAIN=value):
                run = self.piped("--show", EXPLAIN=value)
                self.assertStatus(run, 2)
                self.assertEqual("", run.stdout, run.report())
                for accepted in ("EXPLAIN=0", "EXPLAIN=1", "EXPLAIN=only"):
                    self.assertIn(accepted, run.err, run.report())

    # 14
    def test_a_closed_output_pipe_is_no_traceback(self):
        self.save(SAVED_ON)
        for overrides in ({}, {"EXPLAIN": "only"}):
            with self.subTest(**overrides):
                read_end, write_end = os.pipe()
                os.close(read_end)  # `| head -0`: nobody will read
                try:
                    proc = subprocess.run([str(self.script), "--show"], stdin=subprocess.DEVNULL,
                                          stdout=write_end, stderr=subprocess.PIPE,
                                          cwd=str(self.sandbox.root),
                                          env=self.sandbox.environ(**overrides),
                                          check=False, timeout=60)
                finally:
                    os.close(write_end)
                stderr = proc.stderr.decode("utf-8", errors="replace")
                self.assertEqual(0, proc.returncode, stderr)
                self.assertNotIn("Traceback", stderr)
                self.assertNotIn("BrokenPipeError", stderr)


class ChooseTests(ExplainChoiceTestCase):
    # 10
    def test_choose_shows_the_old_answer_and_replaces_it(self):
        self.save(SAVED_OFF)
        run = self.on_pty("--choose", keys=[b"2\n"])
        self.assertStatus(run, 0)
        self.assertEqual("Your current answer: option 1.", run.out_lines[0], run.report())
        self.assertIn(QUESTION, run.out, run.report())
        self.assertSaved(SAVED_ON, run)

    def test_choose_with_nothing_saved_says_so(self):
        run = self.on_pty("--choose", keys=[b"1\n"])
        self.assertStatus(run, 0)
        self.assertEqual("Nothing is saved yet.", run.out_lines[0], run.report())
        self.assertSaved(SAVED_OFF, run)

    def test_choose_without_a_terminal_changes_nothing(self):
        self.save(SAVED_OFF)
        run = self.piped("--choose")
        self.assertStatus(run, 1)
        self.assertEqual("", run.stdout, run.report())
        self.assertEqual(["make choose asks a question, so it needs a terminal. "
                          "Nothing was changed."], run.err_lines, run.report())
        self.assertEqual(SAVED_OFF, self.saved.read_text())

    def test_choose_ctrl_d_keeps_the_old_answer(self):
        self.save(SAVED_ON)
        run = self.on_pty("--choose", keys=[b"\x04"])
        self.assertStatus(run, 0)
        self.assertEqual(SAVED_ON, self.saved.read_text(), run.report())


class CorruptFileTests(ExplainChoiceTestCase):
    """A saved file that cannot be read is said, then treated as not saved."""

    def assertNamesTheFile(self, line: str, reason: str) -> None:
        path, found, rest = line.partition(UNREADABLE)
        self.assertTrue(found, line)
        self.assertTrue(os.path.samefile(path, str(self.saved)), line)
        self.assertEqual(reason + "; treating it as not saved.", rest)

    # 11
    def test_show_says_so_in_one_line_and_prints_off(self):
        for case, (text, reason) in CORRUPT.items():
            with self.subTest(case=case):
                self.save(text)
                run = self.piped("--show")
                self.assertStatus(run, 0)
                self.assertEqual("off\n", run.stdout, run.report())
                self.assertEqual(1, len(run.err_lines), run.report())
                self.assertNamesTheFile(run.err_lines[0], reason)
                self.assertEqual(text, self.saved.read_text(), "--show must not touch it")

    def test_ask_once_says_so_asks_again_and_replaces_it(self):
        for case, (text, reason) in CORRUPT.items():
            with self.subTest(case=case):
                self.save(text)
                run = self.on_pty("--ask-once", keys=[b"2\n"])
                self.assertStatus(run, 0)
                self.assertNamesTheFile(run.out_lines[0], reason)
                self.assertIn(QUESTION, run.out, run.report())
                self.assertSaved(SAVED_ON, run)

    def test_ask_once_without_a_terminal_says_so_and_leaves_it(self):
        text, reason = CORRUPT["not JSON"]
        self.save(text)
        run = self.piped("--ask-once")
        self.assertStatus(run, 0)
        self.assertEqual("", run.stdout, run.report())
        self.assertNamesTheFile(run.err_lines[0], reason)
        self.assertEqual(text, self.saved.read_text())


class ErrorTests(ExplainChoiceTestCase):
    # 12
    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "running as root, where directory permissions do not bind")
    def test_an_unwritable_root_is_a_plain_message(self):
        self.tree.chmod(0o555)
        self.addCleanup(self.tree.chmod, 0o755)
        run = self.on_pty("--ask-once", keys=[b"2\n"])
        self.assertNotEqual(0, run.status, run.report())
        self.assertIn("Could not save the answer in ", run.out, run.report())
        self.assertNoTraceback(run)
        self.assertNothingSaved(run)

    # 13
    def test_a_usage_error_is_exit_2(self):
        for args in ((), ("--bogus",), ("--show", "--choose"), ("--ask-once", "--ask-once"),
                     ("show",)):
            with self.subTest(args=args):
                run = self.piped(*args)
                self.assertStatus(run, 2)
                self.assertEqual("", run.stdout, run.report())
                self.assertTrue(run.err.startswith("usage: explain-choice "), run.report())
                self.assertNothingSaved(run)


# --- through the real Makefile ------------------------------------------------------

MAKE = shutil.which("make", path=REAL_PATH)


@unittest.skipIf(MAKE is None, "make is not installed")
class MakefileTests(ExplainChoiceTestCase):
    """A temporary copy of the Makefile, distros.json and scripts/, with a fake
    docker for the engine check and a fake compose for COMPOSE."""

    def setUp(self) -> None:
        super().setUp()
        shutil.copy2(str(REPO / "Makefile"), str(self.tree / "Makefile"))
        shutil.copy2(str(REPO / "distros.json"), str(self.tree / "distros.json"))
        for script in SCRIPTS.iterdir():
            if script.is_file():
                shutil.copy2(str(script), str(self.tree / "scripts" / script.name))
        # make runs a one-word recipe such as `echo` itself, without a shell.
        self.sandbox.link("echo")
        self.sandbox.fake("docker")
        self.sandbox.fake("compose")

    def make_argv(self, *goals: str) -> Sequence[str]:
        return [str(MAKE), "--no-print-directory", "COMPOSE=compose", "ENGINE=docker"] + list(goals)

    def make_on_pty(self, *goals: str, keys: Sequence[bytes] = ()) -> Run:
        return run_on_pty(self.make_argv(*goals), env=self.sandbox.environ(), cwd=self.tree,
                          keys=keys, prompt=PROMPT)

    def make_piped(self, *goals: str) -> Run:
        proc = subprocess.run(self.make_argv(*goals), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=str(self.tree), env=self.sandbox.environ(),
                              check=False, timeout=120)
        return Run(proc.returncode, proc.stdout.decode("utf-8", errors="replace"),
                   proc.stderr.decode("utf-8", errors="replace"))

    # 15
    def test_make_shell_asks_saves_then_runs_and_asks_only_once(self):
        run = self.make_on_pty("shell", keys=[b"2\n"])
        self.assertStatus(run, 0)
        self.assertIn(QUESTION, run.out, run.report())
        self.assertSaved(SAVED_ON, run)
        self.assertEqual([["run", "--rm", "shell"]], self.sandbox.argv("compose"))
        question_at = run.out.index(FIRST_LINE)
        self.assertLess(question_at, run.out.index("Entering a ROS shell"), run.report())

        again = self.make_on_pty("shell", keys=[b"1\n"])
        self.assertStatus(again, 0)
        self.assertNotIn(FIRST_LINE, again.out, again.report())
        self.assertSaved(SAVED_ON, again)
        self.assertEqual([["run", "--rm", "shell"]] * 2, self.sandbox.argv("compose"))

    def test_make_choose_replaces_the_answer(self):
        self.save(SAVED_ON)
        run = self.make_on_pty("choose", keys=[b"1\n"])
        self.assertStatus(run, 0)
        self.assertIn("Your current answer: option 2.", run.out, run.report())
        self.assertSaved(SAVED_OFF, run)

    def test_ctrl_c_at_the_question_stops_the_target(self):
        run = self.make_on_pty("shell", keys=[b"\x03"])
        self.assertNotEqual(0, run.status, run.report())
        self.assertNoTraceback(run)
        self.assertFalse(self.sandbox.called("compose"), run.report())
        self.assertNothingSaved(run)

    def test_explain_on_the_command_line_means_no_question(self):
        run = self.make_on_pty("shell", "EXPLAIN=1", keys=[b"2\n"])
        self.assertStatus(run, 0)
        self.assertNotIn(FIRST_LINE, run.out, run.report())
        self.assertNothingSaved(run)
        self.assertEqual([["run", "--rm", "shell"]], self.sandbox.argv("compose"))

    def test_no_terminal_runs_the_target_unasked_and_saves_nothing(self):
        run = self.make_piped("shell")
        self.assertStatus(run, 0)
        self.assertNotIn(FIRST_LINE, run.out + run.err, run.report())
        self.assertNothingSaved(run)
        self.assertEqual([["run", "--rm", "shell"]], self.sandbox.argv("compose"))

    # 16
    def test_make_up_help_asks_nothing_and_runs_nothing(self):
        # `up` has no help topic, so this is the refusal that says nothing ran.
        run = self.make_piped("up", "help")
        self.assertStatus(run, 2)
        self.assertNotIn(FIRST_LINE, run.out + run.err, run.report())
        self.assertIn("Nothing was run.", run.err, run.report())
        self.assertFalse(self.sandbox.called("compose"), run.report())
        self.assertNothingSaved(run)

    def test_make_shell_help_prints_help_and_asks_nothing(self):
        run = self.make_piped("shell", "help")
        self.assertStatus(run, 0)
        self.assertIn("make shell -- a ROS command line", run.out, run.report())
        self.assertNotIn(FIRST_LINE, run.out + run.err, run.report())
        self.assertFalse(self.sandbox.called("compose"), run.report())
        self.assertNothingSaved(run)

    # 17
    def test_make_n_up_neither_asks_nor_saves(self):
        run = self.make_on_pty("-n", "up", keys=[b"2\n"])
        self.assertStatus(run, 0)
        self.assertIn("./scripts/explain-choice --ask-once", run.out, run.report())
        self.assertNotIn(FIRST_LINE, run.out, run.report())
        self.assertNothingSaved(run)


if __name__ == "__main__":
    unittest.main()
