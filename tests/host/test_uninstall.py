"""Black-box tests for scripts/uninstall.

The behaviour to preserve: it finds only the workstation's own containers,
volumes, network, and images, for both the student's project and the
self-test's; it shows them before removing anything; it never removes without
YES=1 or a typed confirmation; and it leaves the shared build cache alone.
"""

import re
import unittest

from fakes import REPO, ScriptTestCase, rule

IMAGE = "ros2-tutorials:lyrical"
LOCAL_IMAGE = "localhost/" + IMAGE
DIGEST = re.search(
    r"^ARG ROS_BASE_DIGEST=(\S+)", (REPO / "Dockerfile").read_text(), re.MULTILINE
).group(1)
BASE = "docker.io/library/ros@" + DIGEST

STUDENT = "ros2-tutorials"
SELFTEST = "ros2-tutorials-selftest"


def everything_rules(image_name=IMAGE):
    """An engine on which every one of the workstation's objects exists."""
    return [
        rule(["ps", "-a", "--filter", "label=com.docker.compose.project=" + STUDENT],
             stdout="ros2-tutorials-desktop-1\n"),
        rule(["ps", "-a", "--filter", "label=com.docker.compose.project=" + SELFTEST],
             stdout="ros2-tutorials-selftest-desktop-1\nros2-tutorials-selftest-shell-1\n"),
        rule(["volume", "ls", "--filter", "label=com.docker.compose.project=" + STUDENT],
             stdout=STUDENT + "_ros-workspace\n" + STUDENT + "_ros-home\n"),
        rule(["volume", "ls", "--filter", "label=com.docker.compose.project=" + SELFTEST],
             stdout=SELFTEST + "_ros-workspace\n" + SELFTEST + "_ros-home\n"),
        rule(["network", "ls", "--filter", "label=com.docker.compose.project=" + STUDENT],
             stdout=STUDENT + "_ros\n"),
        rule(["network", "ls", "--filter", "label=com.docker.compose.project=" + SELFTEST],
             stdout=SELFTEST + "_ros\n"),
        rule(["image", "inspect", "--format", "{{.Size}}", image_name],
             stdout="3100000000\n"),
        rule(["image", "inspect", "--format", "{{.Size}}", BASE], stdout="850000000\n"),
        rule(["image", "inspect"], exit_code=1),
    ]


def nothing_rules():
    return [
        rule(["ps"], stdout=""),
        rule(["volume", "ls"], stdout=""),
        rule(["network", "ls"], stdout=""),
        rule(["image", "inspect"], exit_code=1),
    ]


class UninstallTests(ScriptTestCase):
    script = "uninstall"

    def removals(self, engine="docker"):
        """Every removal call the script made, in order."""
        return [argv for argv in self.sandbox.argv(engine)
                if argv[:1] == ["rm"] or argv[1:2] == ["rm"]]

    # --- what it finds ------------------------------------------------------

    def test_the_plan_lists_both_projects_and_both_images_with_sizes(self):
        self.sandbox.fake("docker", rules=everything_rules())
        run = self.run_script(ENGINE="docker")
        for needle in ("ros2-tutorials-desktop-1", "ros2-tutorials-selftest-shell-1",
                       STUDENT + "_ros-workspace", SELFTEST + "_ros-home",
                       STUDENT + "_ros", SELFTEST + "_ros",
                       IMAGE + "  (3.1 GB)", BASE + "  (850.0 MB)",
                       "Frees at least 4.0 GB."):
            self.assertHas(run, needle)

    def test_the_volumes_say_what_a_student_would_lose(self):
        self.sandbox.fake("docker", rules=everything_rules())
        run = self.run_script(ENGINE="docker")
        self.assertHas(run, STUDENT + "_ros-workspace  (src/, build/, install/, log/)")
        self.assertHas(run, STUDENT + "_ros-home  (shell history, rosdep cache, settings)")

    def test_a_volume_compose_yaml_gains_later_is_still_found(self):
        rules = [rule(["volume", "ls", "--filter",
                       "label=com.docker.compose.project=" + STUDENT],
                      stdout=STUDENT + "_ros-cache\n")]
        self.sandbox.fake("docker", rules=rules + everything_rules())
        run = self.run_script(ENGINE="docker", YES="1")
        self.assertStatus(run, 0)
        self.assertIn(["volume", "rm", STUDENT + "_ros-cache",
                       SELFTEST + "_ros-workspace", SELFTEST + "_ros-home"], self.removals())

    def test_nothing_found_removes_nothing_and_succeeds(self):
        self.sandbox.fake("docker", rules=nothing_rules())
        run = self.run_script(ENGINE="docker", YES="1")
        self.assertStatus(run, 0)
        self.assertHas(run, "nothing to remove")
        self.assertEqual([], self.removals())

    def test_podman_finds_the_image_under_its_localhost_name(self):
        self.sandbox.fake("podman", rules=everything_rules(image_name=LOCAL_IMAGE))
        run = self.run_script(ENGINE="podman", YES="1")
        self.assertStatus(run, 0)
        self.assertIn(["image", "rm", LOCAL_IMAGE, BASE], self.removals("podman"))

    def test_image_name_and_project_overrides_are_honoured(self):
        self.sandbox.fake("docker", rules=[
            rule(["ps", "-a", "--filter", "label=com.docker.compose.project=mine"],
                 stdout="mine-desktop-1\n"),
            rule(["ps"], stdout=""),
            rule(["volume", "ls", "--filter", "label=com.docker.compose.project=mine"],
                 stdout="mine_ros-home\n"),
            rule(["volume", "ls"], stdout=""),
            rule(["network", "ls"], stdout=""),
            rule(["image", "inspect", "--format", "{{.Size}}", "custom:jazzy"], stdout="5\n"),
            rule(["image", "inspect"], exit_code=1),
        ])
        run = self.run_script(ENGINE="docker", YES="1", COMPOSE_PROJECT_NAME="mine",
                              IMAGE_NAME="custom", ROS_DISTRO="jazzy")
        self.assertStatus(run, 0)
        self.assertEqual([["rm", "-f", "mine-desktop-1"],
                          ["volume", "rm", "mine_ros-home"],
                          ["image", "rm", "custom:jazzy"]], self.removals())

    # --- asking first -------------------------------------------------------

    def test_without_a_terminal_or_yes_it_refuses_and_removes_nothing(self):
        self.sandbox.fake("docker", rules=everything_rules())
        run = self.run_script(ENGINE="docker")
        self.assertStatus(run, 1)
        self.assertHas(run, "YES=1", where="stderr")
        self.assertEqual([], self.removals())

    def test_yes_removes_everything_in_dependency_order(self):
        self.sandbox.fake("docker", rules=everything_rules())
        run = self.run_script(ENGINE="docker", YES="1")
        self.assertStatus(run, 0)
        self.assertEqual([
            ["rm", "-f", "ros2-tutorials-desktop-1",
             "ros2-tutorials-selftest-desktop-1", "ros2-tutorials-selftest-shell-1"],
            ["volume", "rm", STUDENT + "_ros-workspace", STUDENT + "_ros-home",
             SELFTEST + "_ros-workspace", SELFTEST + "_ros-home"],
            ["network", "rm", STUDENT + "_ros", SELFTEST + "_ros"],
            ["image", "rm", IMAGE, BASE],
        ], self.removals())
        self.assertHas(run, "+ docker image rm " + IMAGE)

    def test_yes_must_be_exactly_1(self):
        self.sandbox.fake("docker", rules=everything_rules())
        run = self.run_script(ENGINE="docker", YES="yes")
        self.assertStatus(run, 1)
        self.assertEqual([], self.removals())

    # --- afterwards ---------------------------------------------------------

    def test_the_build_cache_is_reported_never_pruned(self):
        self.sandbox.fake("docker", rules=everything_rules())
        run = self.run_script(ENGINE="docker", YES="1")
        self.assertHas(run, "docker builder prune")
        self.assertFalse(any("prune" in argv for argv in self.sandbox.argv("docker")),
                         run.report())

    def test_a_failed_removal_is_reported_and_fails_the_run(self):
        rules = [rule(["image", "rm"], stderr="image is in use\n", exit_code=1)]
        self.sandbox.fake("docker", rules=rules + everything_rules())
        run = self.run_script(ENGINE="docker", YES="1")
        self.assertStatus(run, 1)
        self.assertHas(run, "image is in use", where="stderr")
        # The earlier kinds were still removed.
        self.assertIn(["network", "rm", STUDENT + "_ros", SELFTEST + "_ros"],
                      self.removals())

    def test_an_unknown_engine_is_a_usage_error(self):
        run = self.run_script(ENGINE="nerdctl")
        self.assertStatus(run, 2)
        self.assertHas(run, "neither docker nor podman", where="stderr")


if __name__ == "__main__":
    unittest.main()
