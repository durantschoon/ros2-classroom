"""Black-box tests for scripts/check-host (`make doctor`).

This is the first thing a student runs, so its verdict and its fix-it lines are
pinned on exact text.  The resource lines are pinned on shape only: their
numbers are the machine's.
"""

import unittest

from fakes import ScriptTestCase, rule

DOCKER_VERSION = [
    rule(["compose", "version"], stdout="Docker Compose version v2.24.5\n"),
    rule(["version", "--format", "{{.Client.Version}}"], stdout="24.0.7\n"),
]


class CheckHostTests(ScriptTestCase):
    script = "check-host"

    def setUp(self):
        super().setUp()
        self.sandbox.link("dirname", "df", "awk", "cut", "tr", "sed", "head", "grep")

    def podman(self, version, rootless="true", compose_subcommand=False):
        rules = [
            rule(["version", "--format", "{{.Client.Version}}"], stdout=version + "\n"),
            rule(["info", "--format", "{{.Host.Security.Rootless}}"], stdout=rootless + "\n"),
        ]
        if compose_subcommand:
            rules.insert(0, rule(["compose", "version"], stdout="podman compose\n"))
        self.sandbox.fake("podman", rules=rules, exit_code=1)

    # --- an engine was found ----------------------------------------------

    def test_docker_is_reported_and_the_host_is_ready(self):
        self.sandbox.fake("docker", rules=DOCKER_VERSION, exit_code=1)
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertHas(run, "  ok    compose: docker compose")
        self.assertHas(run, "  ok    engine:  docker 24.0.7")
        self.assertHas(run, "Ready: run `make image`, then `make up`.")
        self.assertLacks(run, "Not ready")

    def test_the_version_falls_back_to_the_plain_version_flag(self):
        self.sandbox.fake(
            "docker",
            rules=[rule(["compose", "version"], stdout="Docker Compose version v2.24.5\n"),
                   rule(["--version"], stdout="Docker version 24.0.7, build afdd53b\n")],
            exit_code=1,
        )
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertHas(run, "  ok    engine:  docker Docker version 24.0.7, build afdd53b")

    def test_a_modern_podman_is_not_warned_about(self):
        self.podman("4.9.3", compose_subcommand=True)
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertHas(run, "  ok    compose: podman compose")
        self.assertHas(run, "  ok    engine:  podman 4.9.3")
        self.assertLacks(run, "predates")

    def test_podman_below_version_four_warns_and_names_the_requirements_file(self):
        self.podman("3.4.4")
        self.sandbox.fake("podman-compose", rules=[rule(["--version"], stdout="1.6.0\n")],
                          exit_code=1)
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertHas(run, "  ok    compose: podman-compose")
        self.assertHas(run, "  ok    engine:  podman 3.4.4")
        self.assertHas(run, "  warn  podman 3.4.4 predates `podman compose`; using podman-compose")
        self.assertHas(run, "        -> pip install --user -r requirements-host.txt   "
                            "(already satisfied)")

    def test_rootless_podman_is_reported(self):
        self.podman("4.9.3", rootless="true", compose_subcommand=True)
        self.assertHas(self.run_script(), "  ok    podman is running rootless")

    def test_rooted_podman_is_warned_about(self):
        self.podman("4.9.3", rootless="false", compose_subcommand=True)
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertHas(run, "  warn  podman is running as root; rootless is recommended")

    def test_docker_is_not_probed_for_rootlessness(self):
        self.sandbox.fake("docker", rules=DOCKER_VERSION, exit_code=1)
        run = self.run_script()
        self.assertLacks(run, "rootless")

    # --- no engine ---------------------------------------------------------

    def test_no_engine_fails_and_quotes_the_explanation(self):
        run = self.run_script()
        self.assertStatus(run, 1)
        self.assertHas(run, "  miss  no working docker or podman compose")
        self.assertHas(run, "        No working container engine found.")
        self.assertHas(run, "        docker: not installed.")
        self.assertHas(run, "        podman: not installed.")
        self.assertHas(run, "        -> see docs/host-requirements.md")
        self.assertHas(run, "Not ready; see docs/host-requirements.md.")

    # --- resources ---------------------------------------------------------

    def test_the_resource_lines_have_the_documented_shape(self):
        self.sandbox.fake("docker", rules=DOCKER_VERSION, exit_code=1)
        run = self.run_script()
        self.assertHas(run, "Resources")
        self.assertRegex(run.out, r"\n  (ok|warn)  +disk free: \d+ GB", run.report())
        self.assertRegex(run.out, r"\n  (ok|warn)  +memory: \d+ GB", run.report())

    def test_the_sections_come_in_order(self):
        self.sandbox.fake("docker", rules=DOCKER_VERSION, exit_code=1)
        out = self.run_script().out
        self.assertLess(out.index("Container engine"), out.index("Resources"))
        self.assertLess(out.index("Resources"), out.index("Ready:"))

    def test_it_changes_nothing_and_writes_only_to_stdout(self):
        self.sandbox.fake("docker", rules=DOCKER_VERSION, exit_code=1)
        run = self.run_script()
        self.assertEqual("", run.err, run.report())
        docker_calls = [c for c in self.sandbox.argv("docker")]
        for call in docker_calls:
            self.assertNotIn("run", call, "check-host must not start containers")
            self.assertNotIn("build", call, "check-host must not build")


if __name__ == "__main__":
    unittest.main()
