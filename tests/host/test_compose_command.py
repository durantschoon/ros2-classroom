"""Black-box tests for scripts/compose-command.

The detection order and the four output modes are what the Makefile, check-host,
smoke-container, and the docs all read, so they are pinned on exact text.
"""

import unittest

from fakes import ScriptTestCase, rule

DOCKER_OK = [rule(["compose", "version"], stdout="Docker Compose version v2.24.5\n")]
PODMAN_OK = [rule(["compose", "version"], stdout="podman-compose version 1.6.0\n")]
PODMAN_COMPOSE_OK = [rule(["--version"], stdout="podman-compose version 1.6.0\n")]
DOCKER_COMPOSE_OK = [rule(["--version"], stdout="docker-compose version 1.29.2\n")]


class ComposeCommandTests(ScriptTestCase):
    script = "compose-command"

    # --- detection order ---------------------------------------------------

    def with_all_four(self):
        self.sandbox.fake("docker", rules=DOCKER_OK, exit_code=1)
        self.sandbox.fake("podman", rules=PODMAN_OK, exit_code=1)
        self.sandbox.fake("podman-compose", rules=PODMAN_COMPOSE_OK, exit_code=1)
        self.sandbox.fake("docker-compose", rules=DOCKER_COMPOSE_OK, exit_code=1)

    def test_docker_compose_is_first(self):
        self.with_all_four()
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertEqual("docker compose\n", run.out)

    def test_podman_compose_subcommand_is_second(self):
        self.with_all_four()
        self.sandbox.fake("docker", exit_code=1)  # CLI present, probe fails
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertEqual("podman compose\n", run.out)

    def test_podman_compose_binary_is_third(self):
        self.with_all_four()
        self.sandbox.fake("docker", exit_code=1)
        self.sandbox.fake("podman", exit_code=1)
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertEqual("podman-compose\n", run.out)

    def test_docker_compose_binary_is_last(self):
        self.with_all_four()
        self.sandbox.fake("docker", exit_code=1)
        self.sandbox.fake("podman", exit_code=1)
        self.sandbox.fake("podman-compose", exit_code=1)
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertEqual("docker-compose\n", run.out)

    def test_a_missing_binary_is_skipped_not_probed(self):
        """Only podman-compose is installed at all."""
        self.sandbox.fake("podman-compose", rules=PODMAN_COMPOSE_OK, exit_code=1)
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertEqual("podman-compose\n", run.out)

    def test_docker_desktop_with_wsl_integration_off_is_not_selected(self):
        """`docker` exists but `docker compose version` fails: skip it entirely."""
        self.sandbox.fake("docker", exit_code=1)
        self.sandbox.fake("podman-compose", rules=PODMAN_COMPOSE_OK, exit_code=1)
        self.assertEqual("podman-compose\n", self.run_script().out)
        self.assertEqual("podman\n", self.run_script("--engine").out)

    def test_docker_compose_binary_reports_docker_as_the_engine(self):
        self.sandbox.fake("docker-compose", rules=DOCKER_COMPOSE_OK, exit_code=1)
        self.assertEqual("docker\n", self.run_script("--engine").out)
        self.assertEqual("docker docker-compose\n", self.run_script("--make").out)

    # --- the four output modes for one detected engine ---------------------

    def test_four_modes_for_docker(self):
        self.sandbox.fake("docker", rules=DOCKER_OK, exit_code=1)
        self.assertEqual("docker compose\n", self.run_script().out)
        self.assertEqual("docker\n", self.run_script("--engine").out)
        self.assertEqual("docker docker compose\n", self.run_script("--make").out)
        self.assertEqual(
            "using docker compose (engine: docker)\n", self.run_script("--explain").out
        )

    def test_four_modes_for_podman_compose(self):
        self.sandbox.fake("podman-compose", rules=PODMAN_COMPOSE_OK, exit_code=1)
        self.assertEqual("podman-compose\n", self.run_script().out)
        self.assertEqual("podman\n", self.run_script("--engine").out)
        self.assertEqual("podman podman-compose\n", self.run_script("--make").out)
        self.assertEqual(
            "using podman-compose (engine: podman)\n", self.run_script("--explain").out
        )

    def test_an_unknown_mode_behaves_like_the_default(self):
        """The Makefile relies on argument-free use; anything unknown falls through."""
        self.sandbox.fake("docker", rules=DOCKER_OK, exit_code=1)
        self.assertEqual("docker compose\n", self.run_script("--bogus").out)

    def test_the_command_goes_to_stdout_only(self):
        self.sandbox.fake("docker", rules=DOCKER_OK, exit_code=1)
        run = self.run_script()
        self.assertEqual("", run.err, run.report())

    # --- nothing found -----------------------------------------------------

    def test_nothing_found_exits_one_in_every_mode(self):
        for mode in ([], ["--engine"], ["--make"], ["--explain"]):
            with self.subTest(mode=mode or ["(default)"]):
                self.assertStatus(self.run_script(*mode), 1)

    def test_nothing_found_default_mode_hints_on_stderr(self):
        run = self.run_script()
        self.assertStatus(run, 1)
        self.assertEqual("", run.out, run.report())
        self.assertEqual(
            "no working docker or podman compose found; "
            "run: scripts/compose-command --explain\n",
            run.err,
        )

    def test_explain_names_both_engines_as_not_installed(self):
        run = self.run_script("--explain")
        self.assertStatus(run, 1)
        self.assertHas(run, "No working container engine found.")
        self.assertHas(run, "docker: not installed.")
        self.assertHas(run, "podman: not installed.")

    def test_explain_distinguishes_a_docker_cli_without_a_daemon(self):
        self.sandbox.fake("docker", exit_code=1)
        run = self.run_script("--explain")
        self.assertStatus(run, 1)
        self.assertHas(run, "docker: the CLI exists but no daemon answered.")
        self.assertHas(run, "WSL Integration for this distro.")
        self.assertHas(run, "podman: not installed.")

    def test_explain_distinguishes_a_podman_without_compose(self):
        self.sandbox.fake("podman", exit_code=1)
        run = self.run_script("--explain")
        self.assertStatus(run, 1)
        self.assertHas(run, "docker: not installed.")
        self.assertHas(run, 'podman: installed, but neither "podman compose" nor')
        self.assertHas(run, "Install podman-compose.")


if __name__ == "__main__":
    unittest.main()
