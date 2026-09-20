"""Black-box tests for scripts/compose-up.

This script exists because podman-compose silently keeps running a stale image
after `make image`.  The stale-image comparison, and the explanation it prints,
are the behaviour to preserve.
"""

import unittest

from fakes import ScriptTestCase, rule

IMAGE = "ros2-tutorials:lyrical"
LOCAL_IMAGE = "localhost/" + IMAGE
CONTAINER = "c0ffeeba5e"

KEPT = "Kept: /workspace and /home/ros (your code, builds, and settings)."
LOST = "Lost: anything added with apt or install-ros-packages inside the old container."
REBUILT = "The image was rebuilt since this desktop started, so it will be recreated."


def engine_rules(image_id=None, local_image_id=None, container="", running_id=None):
    """Replies for `image inspect`, `ps`, and `inspect` on one fake engine."""
    rules = []
    if local_image_id is not None:
        rules.append(
            rule(["image", "inspect", "--format", "{{.Id}}", LOCAL_IMAGE],
                 stdout=local_image_id + "\n")
        )
    if image_id is not None:
        rules.append(
            rule(["image", "inspect", "--format", "{{.Id}}", IMAGE], stdout=image_id + "\n")
        )
    rules.append(rule(["image"], exit_code=1))
    rules.append(rule(["ps"], stdout=(container + "\n") if container else ""))
    if running_id is not None:
        rules.append(rule(["inspect"], stdout=running_id + "\n"))
    else:
        rules.append(rule(["inspect"], exit_code=1))
    return rules


class ComposeUpTests(ScriptTestCase):
    script = "compose-up"

    def setUp(self):
        super().setUp()
        self.sandbox.link("dirname", "sed", "head")

    def engine(self, **kwargs):
        self.sandbox.fake("podman", rules=engine_rules(**kwargs))

    def compose(self, name="compose-stub"):
        self.sandbox.fake(name, stdout="compose ran\n")

    # --- stale image -------------------------------------------------------

    def test_a_stale_running_image_is_explained_and_recreated(self):
        self.engine(image_id="newid", container=CONTAINER, running_id="oldid")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertHas(run, REBUILT)
        self.assertHas(run, KEPT)
        self.assertHas(run, LOST)
        self.assertHas(run, "+ compose-stub up -d --force-recreate")
        self.assertEqual([["up", "-d", "--force-recreate"]], self.sandbox.argv("compose-stub"))

    def test_matching_ids_start_the_desktop_without_an_explanation(self):
        self.engine(image_id="sameid", container=CONTAINER, running_id="sameid")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertLacks(run, REBUILT)
        self.assertLacks(run, "--force-recreate")
        self.assertHas(run, "+ compose-stub up -d")
        self.assertEqual([["up", "-d"]], self.sandbox.argv("compose-stub"))

    def test_a_sha256_prefix_on_one_side_still_counts_as_equal(self):
        """Docker reports sha256:<hex>, Podman bare <hex>; same image either way."""
        self.engine(image_id="deadbeef", container=CONTAINER, running_id="sha256:deadbeef")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertLacks(run, REBUILT)
        self.assertEqual([["up", "-d"]], self.sandbox.argv("compose-stub"))

    def test_a_sha256_prefix_on_the_current_image_still_counts_as_equal(self):
        self.engine(image_id="sha256:deadbeef", container=CONTAINER, running_id="deadbeef")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertLacks(run, REBUILT)
        self.assertEqual([["up", "-d"]], self.sandbox.argv("compose-stub"))

    # --- nothing to compare ------------------------------------------------

    def test_no_container_yet_is_a_plain_up(self):
        self.engine(image_id="newid", container="")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertLacks(run, REBUILT)
        self.assertEqual([["up", "-d"]], self.sandbox.argv("compose-stub"))

    def test_no_image_yet_is_a_plain_up(self):
        self.engine(image_id=None, container=CONTAINER, running_id="whatever")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertLacks(run, REBUILT)
        self.assertEqual([["up", "-d"]], self.sandbox.argv("compose-stub"))

    def test_the_image_is_found_under_the_localhost_name(self):
        """Podman names locally built images localhost/<name>."""
        self.engine(image_id=None, local_image_id="newid",
                    container=CONTAINER, running_id="oldid")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertHas(run, REBUILT)
        self.assertEqual([["up", "-d", "--force-recreate"]], self.sandbox.argv("compose-stub"))

    # --- the queries it makes ---------------------------------------------

    def test_it_looks_for_the_desktop_of_this_compose_project(self):
        self.engine(image_id="newid", container=CONTAINER, running_id="newid")
        self.compose()
        self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        ps_calls = [c for c in self.sandbox.argv("podman") if c and c[0] == "ps"]
        self.assertEqual(1, len(ps_calls), self.sandbox.argv("podman"))
        self.assertEqual(
            ["ps", "-a", "-q",
             "--filter", "label=com.docker.compose.project=ros2-tutorials",
             "--filter", "label=com.docker.compose.service=desktop"],
            ps_calls[0],
        )

    # --- which compose project's desktop it looks for ----------------------
    #
    # Filtering on a hardcoded project finds nothing under any project
    # override, so the stale-image check silently stops working -- which is the
    # one failure this script exists to prevent.  The project is therefore read
    # from COMPOSE, then COMPOSE_PROJECT_NAME, then compose.yaml's `name:`.

    def project_filter(self):
        """The project label the single `ps` call filtered on."""
        ps_calls = [c for c in self.sandbox.argv("podman") if c and c[0] == "ps"]
        self.assertEqual(1, len(ps_calls), self.sandbox.argv("podman"))
        labels = [w for w in ps_calls[0] if w.startswith("label=com.docker.compose.project=")]
        self.assertEqual(1, len(labels), ps_calls[0])
        return labels[0].split("=", 2)[2]

    def run_with(self, compose, **env):
        self.engine(image_id="sameid", container=CONTAINER, running_id="sameid")
        self.sandbox.fake(compose.split()[0], stdout="compose ran\n")
        run = self.run_script(COMPOSE=compose, ENGINE="podman", **env)
        self.assertStatus(run, 0)
        return run

    def test_a_short_project_flag_in_compose_names_the_project(self):
        self.run_with("compose-stub -p other")
        self.assertEqual("other", self.project_filter())

    def test_a_short_project_flag_with_an_equals_names_the_project(self):
        self.run_with("compose-stub -p=other")
        self.assertEqual("other", self.project_filter())

    def test_an_attached_short_project_flag_names_the_project(self):
        self.run_with("compose-stub -pother")
        self.assertEqual("other", self.project_filter())

    def test_a_flag_that_merely_starts_with_p_is_not_a_project(self):
        self.run_with("compose-stub --profile demo")
        self.assertEqual("ros2-tutorials", self.project_filter())

    def test_a_long_project_flag_in_compose_names_the_project(self):
        self.run_with("compose-stub --project-name other")
        self.assertEqual("other", self.project_filter())

    def test_a_long_project_flag_with_an_equals_names_the_project(self):
        self.run_with("compose-stub --project-name=other")
        self.assertEqual("other", self.project_filter())

    def test_compose_project_name_names_the_project(self):
        self.run_with("compose-stub", COMPOSE_PROJECT_NAME="from-the-environment")
        self.assertEqual("from-the-environment", self.project_filter())

    def test_a_project_flag_beats_the_environment_variable(self):
        self.run_with("compose-stub -p from-the-flag",
                      COMPOSE_PROJECT_NAME="from-the-environment")
        self.assertEqual("from-the-flag", self.project_filter())

    def test_a_stale_image_is_detected_under_a_project_override(self):
        self.engine(image_id="newid", container=CONTAINER, running_id="oldid")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub -p other", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertEqual("other", self.project_filter())
        self.assertHas(run, REBUILT)
        self.assertHas(run, "+ compose-stub -p other up -d --force-recreate")
        self.assertEqual(
            [["-p", "other", "up", "-d", "--force-recreate"]],
            self.sandbox.argv("compose-stub"),
        )

    def test_the_image_name_and_distro_can_be_overridden(self):
        self.sandbox.fake(
            "podman",
            rules=[rule(["image", "inspect", "--format", "{{.Id}}", "custom:jazzy"],
                        stdout="id\n"),
                   rule(["image"], exit_code=1),
                   rule(["ps"], stdout=""),
                   rule(["inspect"], exit_code=1)],
        )
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman",
                              IMAGE_NAME="custom", ROS_DISTRO="jazzy")
        self.assertStatus(run, 0)
        inspects = [c for c in self.sandbox.argv("podman") if c and c[0] == "image"]
        self.assertEqual([["image", "inspect", "--format", "{{.Id}}", "custom:jazzy"]], inspects)

    # --- the echoed command ------------------------------------------------

    def test_a_two_word_compose_command_is_split_into_words(self):
        self.engine(image_id="sameid", container=CONTAINER, running_id="sameid")
        self.sandbox.fake("docker", stdout="compose ran\n")
        run = self.run_script(COMPOSE="docker compose", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertHas(run, "+ docker compose up -d")
        self.assertEqual([["compose", "up", "-d"]], self.sandbox.argv("docker"))

    def test_the_command_is_echoed_before_it_runs(self):
        self.engine(image_id="sameid", container=CONTAINER, running_id="sameid")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertEqual(["+ compose-stub up -d", "compose ran"], run.out_lines)

    def test_the_exit_status_of_compose_is_the_exit_status(self):
        self.engine(image_id="sameid", container=CONTAINER, running_id="sameid")
        self.sandbox.fake("compose-stub", exit_code=7)
        self.assertStatus(self.run_script(COMPOSE="compose-stub", ENGINE="podman"), 7)

    def test_a_failed_up_names_the_port_and_a_free_one_to_try(self):
        self.engine(image_id="sameid", container=CONTAINER, running_id="sameid")
        self.sandbox.fake("compose-stub", exit_code=1)
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertStatus(run, 1)
        self.assertHas(run, "something else is using host port 6080.", where="stderr")
        # Not 6081: that is `make selftest`'s own port.
        self.assertHas(run, "  make up NOVNC_PORT=6082 && make open NOVNC_PORT=6082",
                       where="stderr")

    def test_the_hint_follows_an_overridden_port(self):
        self.engine(image_id="sameid", container=CONTAINER, running_id="sameid")
        self.sandbox.fake("compose-stub", exit_code=1)
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman", NOVNC_PORT="7000")
        self.assertHas(run, "something else is using host port 7000.", where="stderr")
        self.assertHas(run, "  make up NOVNC_PORT=7001 && make open NOVNC_PORT=7001",
                       where="stderr")

    def test_a_successful_up_says_nothing_about_ports(self):
        self.engine(image_id="sameid", container=CONTAINER, running_id="sameid")
        self.compose()
        run = self.run_script(COMPOSE="compose-stub", ENGINE="podman")
        self.assertStatus(run, 0)
        self.assertLacks(run, "host port", where="stderr")

    # --- required environment ---------------------------------------------

    def test_an_unset_compose_fails_with_a_message(self):
        self.engine(image_id="id")
        run = self.run_script(ENGINE="podman")
        self.assertNotEqual(0, run.status, run.report())
        self.assertHas(run, "COMPOSE is not set", where="stderr")

    def test_an_unset_engine_fails_with_a_message(self):
        self.compose()
        run = self.run_script(COMPOSE="compose-stub")
        self.assertNotEqual(0, run.status, run.report())
        self.assertHas(run, "ENGINE is not set", where="stderr")
        self.assertEqual([], self.sandbox.argv("compose-stub"))


if __name__ == "__main__":
    unittest.main()
