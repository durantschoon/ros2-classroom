"""Black-box tests for scripts/open-url.

This script exists because xdg-open on WSL opens a text editor instead of a
browser, so the WSL branch running *before* xdg-open is the behaviour that must
never regress.  The URL is printed first on every path, so a failed opener still
leaves an address to copy.
"""

import unittest

from fakes import NOT_ON_WSL, WSL_HOST, ScriptTestCase

URL = "http://localhost:6080/vnc.html?autoconnect=1&resize=remote&reconnect=true"

NO_WINDOWS_BROWSER = "Could not reach a Windows browser; open the address above yourself."
NO_OPENER = "No browser opener found; open the address above yourself."


class OpenUrlTests(ScriptTestCase):
    script = "open-url"

    def setUp(self):
        super().setUp()
        self.sandbox.link("grep")

    def go(self, **env):
        return self.run_script(URL, **env)

    # --- the URL is always printed ----------------------------------------

    def test_the_url_is_the_first_line_of_stdout_on_every_path(self):
        cases = {
            "browser": dict(openers=["mybrowser"], env={"BROWSER": "mybrowser"}),
            "wslview": dict(openers=["wslview"], env={"WSL_DISTRO_NAME": "Ubuntu"}),
            "powershell": dict(openers=["powershell.exe"], env={"WSL_DISTRO_NAME": "Ubuntu"}),
            "explorer": dict(openers=["explorer.exe"], env={"WSL_DISTRO_NAME": "Ubuntu"}),
            "nothing": dict(openers=[], env={"WSL_DISTRO_NAME": "Ubuntu"}),
        }
        for label, case in cases.items():
            with self.subTest(path=label):
                self.setUp()
                for name in case["openers"]:
                    self.sandbox.fake(name)
                run = self.go(**case["env"])
                self.assertEqual(URL, run.out_lines[0], run.report())

    # --- BROWSER -----------------------------------------------------------

    def test_browser_wins_when_the_command_exists(self):
        self.sandbox.fake("mybrowser")
        self.sandbox.fake("wslview")
        run = self.go(BROWSER="mybrowser", WSL_DISTRO_NAME="Ubuntu")
        self.assertStatus(run, 0)
        self.assertEqual([[URL]], self.sandbox.argv("mybrowser"))
        self.assertFalse(self.sandbox.called("wslview"), "wslview should not have run")

    def test_a_browser_naming_a_missing_command_is_ignored(self):
        self.sandbox.fake("wslview")
        run = self.go(BROWSER="not-installed", WSL_DISTRO_NAME="Ubuntu")
        self.assertStatus(run, 0)
        self.assertEqual([[URL]], self.sandbox.argv("wslview"))

    # --- WSL ---------------------------------------------------------------

    def test_wslview_is_the_first_choice_on_wsl(self):
        for name in ("wslview", "powershell.exe", "explorer.exe", "xdg-open"):
            self.sandbox.fake(name)
        run = self.go(WSL_DISTRO_NAME="Ubuntu")
        self.assertStatus(run, 0)
        self.assertEqual([[URL]], self.sandbox.argv("wslview"))
        for name in ("powershell.exe", "explorer.exe", "xdg-open"):
            self.assertFalse(self.sandbox.called(name), name + " should not have run")

    def test_powershell_is_the_second_choice_on_wsl(self):
        for name in ("powershell.exe", "explorer.exe", "xdg-open"):
            self.sandbox.fake(name)
        run = self.go(WSL_DISTRO_NAME="Ubuntu")
        self.assertStatus(run, 0)
        self.assertEqual(
            [["-NoProfile", "-Command", "Start-Process '{}'".format(URL)]],
            self.sandbox.argv("powershell.exe"),
        )
        self.assertFalse(self.sandbox.called("explorer.exe"))

    def test_explorer_is_the_last_choice_on_wsl(self):
        for name in ("explorer.exe", "xdg-open"):
            self.sandbox.fake(name)
        run = self.go(WSL_DISTRO_NAME="Ubuntu")
        self.assertStatus(run, 0)
        self.assertEqual([[URL]], self.sandbox.argv("explorer.exe"))
        self.assertFalse(self.sandbox.called("xdg-open"), "xdg-open must never run on WSL")

    def test_a_failing_explorer_still_exits_zero(self):
        """explorer.exe exits non-zero even when it succeeded."""
        self.sandbox.fake("explorer.exe", exit_code=1)
        run = self.go(WSL_DISTRO_NAME="Ubuntu")
        self.assertStatus(run, 0)
        self.assertEqual([[URL]], self.sandbox.argv("explorer.exe"))

    def test_no_opener_on_wsl_exits_zero_with_the_fallback_message(self):
        run = self.go(WSL_DISTRO_NAME="Ubuntu")
        self.assertStatus(run, 0)
        self.assertEqual(URL + "\n", run.out, run.report())
        self.assertHas(run, NO_WINDOWS_BROWSER, where="stderr")

    def test_xdg_open_is_never_used_on_wsl(self):
        self.sandbox.fake("xdg-open")
        run = self.go(WSL_DISTRO_NAME="Ubuntu")
        self.assertStatus(run, 0)
        self.assertFalse(self.sandbox.called("xdg-open"), "xdg-open must never run on WSL")
        self.assertHas(run, NO_WINDOWS_BROWSER, where="stderr")

    def test_the_opener_replaces_the_script_so_its_status_is_the_status(self):
        self.sandbox.fake("wslview", exit_code=3)
        self.assertStatus(self.go(WSL_DISTRO_NAME="Ubuntu"), 3)

    # --- macOS and Linux ---------------------------------------------------

    @unittest.skipIf(WSL_HOST, NOT_ON_WSL)
    def test_macos_uses_open(self):
        self.sandbox.fake("uname", stdout="Darwin\n")
        self.sandbox.fake("open")
        self.sandbox.fake("xdg-open")
        run = self.go()
        self.assertStatus(run, 0)
        self.assertEqual([[URL]], self.sandbox.argv("open"))
        self.assertFalse(self.sandbox.called("xdg-open"))

    @unittest.skipIf(WSL_HOST, NOT_ON_WSL)
    def test_macos_without_open_falls_back_to_the_message(self):
        self.sandbox.fake("uname", stdout="Darwin\n")
        run = self.go()
        self.assertStatus(run, 0)
        self.assertHas(run, NO_OPENER, where="stderr")

    @unittest.skipIf(WSL_HOST, NOT_ON_WSL)
    def test_linux_uses_xdg_open(self):
        self.sandbox.fake("uname", stdout="Linux\n")
        self.sandbox.fake("xdg-open")
        self.sandbox.fake("open")
        run = self.go()
        self.assertStatus(run, 0)
        self.assertEqual([[URL]], self.sandbox.argv("xdg-open"))
        self.assertFalse(self.sandbox.called("open"))

    @unittest.skipIf(WSL_HOST, NOT_ON_WSL)
    def test_linux_without_xdg_open_exits_zero_with_the_fallback_message(self):
        self.sandbox.fake("uname", stdout="Linux\n")
        run = self.go()
        self.assertStatus(run, 0)
        self.assertEqual(URL + "\n", run.out, run.report())
        self.assertHas(run, NO_OPENER, where="stderr")

    # --- usage -------------------------------------------------------------

    def test_a_missing_url_is_a_usage_error(self):
        run = self.run_script()
        self.assertNotEqual(0, run.status, run.report())
        self.assertHas(run, "usage: open-url URL", where="stderr")


if __name__ == "__main__":
    unittest.main()
