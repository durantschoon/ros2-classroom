"""Black-box tests for scripts/uninstall.

The behaviour to preserve: it finds only the workstation's own containers,
volumes, network, and images, for both the student's project and the
self-test's; it shows them before removing anything; it never removes without
YES=1 or a typed confirmation; and it leaves the shared build cache alone.
"""

import re
import unittest

from fakes import COMPOSE_IMAGE, COMPOSE_IMAGE_TAG, REPO, ScriptTestCase, rule
import json
import shutil
from fakes import SCRIPTS

IMAGE = COMPOSE_IMAGE
# What builds were tagged before compose.yaml named the published image.
LEGACY_IMAGE = "ros2-tutorials:lyrical"
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

    def test_the_published_image_and_a_legacy_build_are_both_removed(self):
        # The image compose pulls is the one taking the disk; a build tagged
        # the old way may still sit beside it.
        self.sandbox.fake("docker", rules=nothing_rules()[:3] + [
            rule(["image", "inspect", "--format", "{{.Size}}", IMAGE], stdout="4500000000\n"),
            rule(["image", "inspect", "--format", "{{.Size}}", LEGACY_IMAGE],
                 stdout="4400000000\n"),
            rule(["image", "inspect"], exit_code=1),
        ])
        run = self.run_script(ENGINE="docker", YES="1")
        self.assertStatus(run, 0)
        self.assertHas(run, IMAGE + "  (4.5 GB)")
        self.assertHas(run, LEGACY_IMAGE + "  (4.4 GB)")
        self.assertEqual([["image", "rm", IMAGE, LEGACY_IMAGE]], self.removals())

    def test_image_name_and_project_overrides_are_honoured(self):
        self.sandbox.fake("docker", rules=[
            rule(["ps", "-a", "--filter", "label=com.docker.compose.project=mine"],
                 stdout="mine-desktop-1\n"),
            rule(["ps"], stdout=""),
            rule(["volume", "ls", "--filter", "label=com.docker.compose.project=mine"],
                 stdout="mine_ros-home\n"),
            rule(["volume", "ls"], stdout=""),
            rule(["network", "ls"], stdout=""),
            rule(["image", "inspect", "--format", "{{.Size}}", "custom:" + COMPOSE_IMAGE_TAG],
                 stdout="5\n"),
            rule(["image", "inspect", "--format", "{{.Size}}", "ros2-tutorials:jazzy"],
                 stdout="7\n"),
            rule(["image", "inspect"], exit_code=1),
        ])
        run = self.run_script(ENGINE="docker", YES="1", COMPOSE_PROJECT_NAME="mine",
                              IMAGE_NAME="custom", ROS_DISTRO="jazzy")
        self.assertStatus(run, 0)
        self.assertEqual([["rm", "-f", "mine-desktop-1"],
                          ["volume", "rm", "mine_ros-home"],
                          ["image", "rm", "custom:" + COMPOSE_IMAGE_TAG, "ros2-tutorials:jazzy"]],
                         self.removals())

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


# --- every distribution in distros.json ---------------------------------------

TABLE = json.loads((REPO / "distros.json").read_text())
DEFAULT_DISTRO = TABLE["default"]
# The default first, then the others by name: the order uninstall looks in.
DISTROS = [DEFAULT_DISTRO] + sorted(n for n in TABLE["distros"] if n != DEFAULT_DISTRO)


def project_of(name):
    return STUDENT if name == DEFAULT_DISTRO else STUDENT + "-" + name


def image_of(name):
    return "{}:{}".format(COMPOSE_IMAGE.rsplit(":", 1)[0],
                          COMPOSE_IMAGE_TAG if name == DEFAULT_DISTRO else name)


def base_of(name):
    return "docker.io/library/ros@" + TABLE["distros"][name]["digest"]


ALL_PROJECTS = [project_of(name) for name in DISTROS] + [SELFTEST]
ALL_IMAGES = ([image_of(name) for name in DISTROS]
              + ["ros2-tutorials:" + name for name in DISTROS]
              + [base_of(name) for name in DISTROS])


def every_distribution_rules():
    """An engine holding one of everything for every distribution and the self-test."""
    rules = []
    for project in ALL_PROJECTS:
        label = "label=com.docker.compose.project=" + project
        rules.append(rule(["ps", "-a", "--filter", label], stdout=project + "-desktop-1\n"))
        rules.append(rule(["volume", "ls", "--filter", label],
                          stdout=project + "_ros-workspace\n"))
        rules.append(rule(["network", "ls", "--filter", label], stdout=project + "_ros\n"))
    for index, image in enumerate(ALL_IMAGES):
        rules.append(rule(["image", "inspect", "--format", "{{.Size}}", image],
                          stdout="{}000000\n".format(100 + index)))
    rules.append(rule(["image", "inspect"], exit_code=1))
    return rules


class EveryDistributionTests(ScriptTestCase):
    script = "uninstall"

    def removals(self):
        return [argv for argv in self.sandbox.argv("docker")
                if argv[:1] == ["rm"] or argv[1:2] == ["rm"]]

    def test_the_plan_lists_every_distributions_objects_with_sizes(self):
        self.sandbox.fake("docker", rules=every_distribution_rules())
        run = self.run_script(ENGINE="docker")
        for project in ALL_PROJECTS:
            self.assertHas(run, project + "-desktop-1")
            self.assertHas(run, project + "_ros-workspace  (src/, build/, install/, log/)")
            self.assertHas(run, project + "_ros")
        for index, image in enumerate(ALL_IMAGES):
            self.assertHas(run, "  image     {}  ({}.0 MB)".format(image, 100 + index))

    def test_everything_is_removed_in_order_one_call_per_kind(self):
        # With nothing set, and as make runs it for another distribution: the
        # same objects either way, each once.
        environments = (
            {},
            {"ROS_DISTRO": "jazzy", "IMAGE_TAG": "jazzy",
             "COMPOSE_PROJECT_NAME": STUDENT + "-jazzy",
             "ROS_BASE_DIGEST": TABLE["distros"]["jazzy"]["digest"]},
        )
        for environment in environments:
            with self.subTest(environment=environment):
                self.setUp()
                self.sandbox.fake("docker", rules=every_distribution_rules())
                run = self.run_script(ENGINE="docker", YES="1", **environment)
                self.assertStatus(run, 0)
                self.assertEqual([
                    ["rm", "-f"] + [p + "-desktop-1" for p in ALL_PROJECTS],
                    ["volume", "rm"] + [p + "_ros-workspace" for p in ALL_PROJECTS],
                    ["network", "rm"] + [p + "_ros" for p in ALL_PROJECTS],
                    ["image", "rm"] + ALL_IMAGES,
                ], self.removals())

    def test_an_unreadable_table_looks_only_where_it_did_before_the_table(self):
        # A copy of uninstall with the Dockerfile beside it and no distros.json,
        # then with one that is not JSON.
        tree = self.sandbox.root / "tree"
        (tree / "scripts").mkdir(parents=True)
        shutil.copy2(str(SCRIPTS / "uninstall"), str(tree / "scripts" / "uninstall"))
        shutil.copy2(str(REPO / "Dockerfile"), str(tree / "Dockerfile"))
        for table in (None, "{ not json"):
            with self.subTest(table=table):
                if table is not None:
                    (tree / "distros.json").write_text(table)
                self.sandbox.fake("docker", rules=everything_rules()
                                  + every_distribution_rules())
                calls_before = len(self.sandbox.argv("docker"))
                run = self.run_script(ENGINE="docker", YES="1",
                                      script=str(tree / "scripts" / "uninstall"))
                self.assertStatus(run, 0)
                self.assertEqual([
                    ["rm", "-f", "ros2-tutorials-desktop-1",
                     "ros2-tutorials-selftest-desktop-1", "ros2-tutorials-selftest-shell-1"],
                    ["volume", "rm", STUDENT + "_ros-workspace", STUDENT + "_ros-home",
                     SELFTEST + "_ros-workspace", SELFTEST + "_ros-home"],
                    ["network", "rm", STUDENT + "_ros", SELFTEST + "_ros"],
                    ["image", "rm", IMAGE, BASE],
                ], self.removals()[-4:])
                asked = self.sandbox.argv("docker")[calls_before:]
                self.assertFalse(any("jazzy" in word for argv in asked for word in argv), asked)


if __name__ == "__main__":
    unittest.main()
