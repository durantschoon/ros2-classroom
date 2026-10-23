"""Black-box contract tests; synthetic commands/evidence are never product recipes."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "native-recipes"
FIXTURES = Path(__file__).parent / "fixtures" / "native-recipes"


def recipe(identity="fixture.install", operation="install", parameters=(), status="verified-in-ci"):
    provenance = {"verified-in-ci": {"ci_run": "synthetic test run"},
                  "verified-by-hand": {"environment": "synthetic test host"},
                  "community-reported": {"report": "synthetic test report"}}[status]
    return {"id": identity, "platform": {"os": "ubuntu", "version": "24.04",
            "architecture": "amd64", "route": "apt", "ros_distro": "lyrical", "context": "native"},
            "operation": operation, "verification": {"status": status,
            "reference": "https://example.invalid/synthetic-test-only", "date": "2026-10-23",
            "procedure": "Schema fixture only; never verified or executed", "subject": identity,
            "provenance": provenance},
            "commands": [{"argv": [{"literal": "synthetic-never-execute"}] +
                         [{"parameter": p} for p in parameters]}], "guidance": ["Synthetic fixture"]}


class NativeRecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.counter = 0

    def write(self, data):
        self.counter += 1
        path = self.directory / (str(self.counter) + ".json")
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def cli(self, *args, expected=0, env=None):
        run = subprocess.run([sys.executable, str(SCRIPT)] + list(args), cwd=str(self.directory),
                             env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        self.assertEqual(run.stderr, "")
        result = json.loads(run.stdout)
        self.assertEqual(result["outcome"], "ok" if expected == 0 else ("unsupported" if expected == 1 else "error"))
        return result

    def validate(self, recipes, expected=0):
        return self.cli("validate", self.write({"schema_version": 1, "recipes": recipes}), expected=expected)

    def select(self, recipes, fixture="ubuntu", operation="install", parameters=None, expected=0):
        return self.cli("select", self.write({"schema_version": 1, "recipes": recipes}),
                        str(FIXTURES / (fixture + ".json")),
                        self.write({"operation": operation, "parameters": parameters or {}}), expected=expected)

    def test_recorded_platform_matrix(self):
        cases = [("ubuntu", "ubuntu", "amd64", "apt", "native"),
                 ("debian", "debian", "amd64", "", "native"),
                 ("fedora", "fedora", "amd64", "", "native"),
                 ("macos-arm64", "macos", "arm64", "pixi", "native"),
                 ("macos-amd64", "macos", "amd64", "pixi", "native"),
                 ("windows", "windows", "amd64", "wsl2", "native"),
                 ("wsl-ubuntu", "ubuntu", "arm64", "apt", "wsl"),
                 ("unknown-architecture", "ubuntu", "", "apt", "native"),
                 ("unknown-distro", "ubuntu", "amd64", "apt", "native")]
        for fixture, osname, arch, route, context in cases:
            with self.subTest(fixture=fixture):
                host = self.cli("classify", str(FIXTURES / (fixture + ".json")))["platform"]
                for key, value in (("os", osname), ("architecture", arch), ("route", route), ("context", context)):
                    self.assertEqual(host[key]["values"], [value] if value else [])
                    self.assertEqual(host[key]["state"], "known" if value else "unknown")

    def test_selection_exact_platform_and_no_distro_fallback(self):
        self.assertEqual(self.select([recipe()])["recipe"]["id"], "fixture.install")
        for fixture in ("debian", "fedora", "windows", "wsl-ubuntu", "macos-amd64", "unknown-architecture", "unknown-distro"):
            with self.subTest(fixture=fixture):
                self.select([recipe()], fixture, expected=1)
        for field, value in (("version", "22.04"), ("ros_distro", "jazzy"), ("architecture", "arm64"), ("context", "wsl")):
            item = recipe()
            item["platform"][field] = value
            self.select([item], expected=1)

    def test_pixi_bootstrap_does_not_require_pixi_installed(self):
        for fixture, arch in (("macos-arm64", "arm64"), ("macos-amd64", "amd64")):
            item = recipe()
            item["platform"].update(os="macos", version="15.0", architecture=arch, route="pixi")
            result = self.select([item], fixture)
            self.assertEqual(result["recipe"]["platform"]["route"], "pixi")

    def test_windows_bootstrap_distinct_from_wsl_guest(self):
        item = recipe()
        item["platform"].update(os="windows", version="10.0.26100", route="wsl2")
        self.select([item], "windows")
        self.select([item], "wsl-ubuntu", expected=1)
        item["platform"].update(os="ubuntu", version="24.04", architecture="arm64", route="apt", context="wsl")
        self.select([item], "wsl-ubuntu")

    def test_missing_and_ambiguous_matches_are_structured(self):
        self.assertEqual(self.select([], expected=1)["error"]["code"], "no-match")
        duplicate = recipe("fixture.other")
        result = self.select([recipe(), duplicate], expected=1)
        self.assertEqual(result["error"]["code"], "ambiguous-selection")
        self.assertNotIn("recipe", result)
        self.assertEqual(self.validate([recipe(), recipe()], expected=2)["error"]["code"], "duplicate-identity")

    def test_status_requires_matching_reproducible_evidence(self):
        for status in ("verified-in-ci", "verified-by-hand", "community-reported"):
            self.validate([recipe(status=status)])
            for field in ("status", "reference", "date", "procedure", "subject", "provenance"):
                item = recipe(status=status)
                del item["verification"][field]
                self.validate([item], expected=2)
            for field, value in (("status", "draft"), ("reference", ""), ("date", "2026-02-30"),
                                 ("procedure", ""), ("subject", "unrelated"), ("provenance", {"wrong": "value"})):
                item = recipe(status=status)
                item["verification"][field] = value
                self.validate([item], expected=2)

    def test_strict_schema_versions_types_and_unknown_fields(self):
        for version in (True, False, 0, 2, "1", None, []):
            self.cli("validate", self.write({"schema_version": version, "recipes": []}), expected=2)
        for payload in ({}, [], {"schema_version": 1, "recipes": [], "extra": 1},
                        {"schema_version": 1, "recipes": {}}, {"schema_version": 1, "recipes": [None]}):
            self.cli("validate", self.write(payload), expected=2)
        for field, value in (("operation", []), ("operation", "unknown"), ("commands", "shell text"),
                             ("guidance", [None]), ("id", ""), ("platform", {}), ("verification", {})):
            item = recipe()
            item[field] = value
            self.validate([item], expected=2)
        item = recipe()
        item["platform"]["route"] = "pixi"
        self.validate([item], expected=2)

    def test_duplicate_json_keys_and_non_json_numbers_rejected(self):
        for source in ('{"schema_version":1,"schema_version":1,"recipes":[]}',
                       '{"schema_version":1,"recipes":[],"x":NaN}', '{broken'):
            path = self.directory / "malformed.json"
            path.write_text(source)
            self.cli("validate", str(path), expected=2)

    def test_malformed_commands_and_parameter_references_rejected(self):
        bad = [[], [{}], [{"argv": []}], [{"argv": "echo hello"}],
               [{"argv": [{"literal": ""}]}], [{"argv": [{"literal": "a\u0000b"}]}],
               [{"argv": [{"parameter": "workspace"}]}],
               [{"argv": [{"literal": "cmd"}, {"parameter": "unknown"}]}],
               [{"argv": [{"literal": "cmd", "parameter": "workspace"}]}]]
        for commands in bad:
            item = recipe()
            item["commands"] = commands
            self.validate([item], expected=2)

    def test_every_operation_and_parameter_contract(self):
        contracts = {"build-workspace": {"workspace": "ws"},
                     "test-workspace": {"workspace": "ws"}, "install": {}, "session": {"workspace": "ws"}, "shell": {"workspace": "ws"},
                     "turtlesim": {"workspace": "ws"}, "teleop": {"workspace": "ws"},
                     "package": {"workspace": "ws", "package": "p", "build_type": "ament_cmake"},
                     "package-template": {"workspace": "ws", "package": "p", "build_type": "ament_python", "template": "pubsub"},
                     "package-interfaces": {"workspace": "ws", "package": "p"},
                     "build": {"workspace": "ws", "package": "p"}, "run": {"workspace": "ws", "package": "p", "node": "n"},
                     "test": {"workspace": "ws", "package": "p"}}
        for operation, params in contracts.items():
            with self.subTest(operation=operation):
                item = recipe(operation=operation, parameters=params)
                self.select([item], operation=operation, parameters=params)
                self.select([item], operation=operation, parameters=dict(params, bogus="x"), expected=2)
                if params:
                    missing = dict(params)
                    missing.pop(next(iter(missing)))
                    self.select([item], operation=operation, parameters=missing, expected=2)
                    item["commands"] = [{"argv": [{"literal": "synthetic"}]}]
                    self.validate([item], expected=2)
        self.select([], operation="container-maintenance", expected=1)
        self.validate([recipe(operation="container-maintenance")], expected=1)

    def test_workspace_operations_do_not_match_package_scoped_recipes(self):
        for scoped, whole in (("build", "build-workspace"), ("test", "test-workspace")):
            item = recipe(operation=scoped, parameters=("workspace", "package"))
            self.select([item], operation=whole, parameters={"workspace": "ws"}, expected=1)
            item = recipe(operation=whole, parameters=("workspace",))
            self.select([item], operation=scoped, parameters={"workspace": "ws", "package": "p"}, expected=1)
        self.select([], operation="build", parameters={"workspace": "ws", "packages": ["a", "b"]}, expected=2)

    def test_hostile_parameters_are_preserved_as_data(self):
        hostile = "$(touch PWNED); ' \" `touch PWNED` --x"
        params = {"workspace": hostile, "package": hostile, "node": hostile}
        item = recipe(operation="run", parameters=params)
        result = self.select([item], operation="run", parameters=params)
        self.assertEqual(result["parameters"], params)
        self.assertEqual(result["recipe"], item)
        self.assertFalse((self.directory / "PWNED").exists())

    def test_observation_states_are_distinct_and_invalid_states_fail(self):
        original = json.loads((FIXTURES / "ubuntu.json").read_text())
        for state in ("unknown", "none", "not-observed"):
            raw = copy.deepcopy(original)
            raw["facts"]["tools"] = {"state": state, "values": []}
            host = self.cli("classify", self.write(raw))["platform"]
            self.assertEqual(host["tools"]["state"], state)
            self.assertEqual(host["engine"]["state"], state)
        for bad in ({"state": "known", "values": []}, {"state": "unknown", "values": ["pixi"]},
                    {"state": "maybe", "values": []}, {"state": "known", "values": [False]},
                    {"state": "known", "values": ["pixi", "pixi"]}):
            raw = copy.deepcopy(original)
            raw["facts"]["tools"] = bad
            self.cli("classify", self.write(raw), expected=2)

    def test_ssh_vm_display_gpu_network_observations_are_retained(self):
        raw = json.loads((FIXTURES / "ubuntu.json").read_text())
        for name, value in (("ssh", "present"), ("vm", "kvm"), ("display", "wayland"),
                            ("gpu", "available"), ("network", "offline")):
            raw["facts"][name] = {"state": "known", "values": [value]}
        host = self.cli("classify", self.write(raw))["platform"]
        for name in ("ssh", "vm", "display", "gpu", "network"):
            self.assertEqual(host[name], raw["facts"][name])

    def test_invalid_request_cases_are_structured(self):
        for operation, params in (("unknown", {}), ("run", {"workspace": "ws", "package": "p", "node": False}),
                                  ("package", {"workspace": "ws", "package": "p", "build_type": "invented"}),
                                  ("package-template", {"workspace": "ws", "package": "p", "build_type": "ament_cmake", "template": "invented"})):
            self.select([], operation=operation, parameters=params, expected=2)

    def test_unknown_linux_kernel_never_implies_native_or_selects_recipe(self):
        original = json.loads((FIXTURES / "ubuntu.json").read_text())
        for state in ("unknown", "none", "not-observed"):
            with self.subTest(state=state):
                raw = copy.deepcopy(original)
                raw["facts"]["kernel_release"] = {"state": state, "values": []}
                path = self.write(raw)
                host = self.cli("classify", path)["platform"]
                self.assertEqual(host["kernel_release"], raw["facts"]["kernel_release"])
                self.assertEqual(host["context"], {"state": "not-observed" if state == "not-observed" else "unknown", "values": []})
                result = self.cli("select", self.write({"schema_version": 1, "recipes": [recipe()]}),
                                  path, self.write({"operation": "install", "parameters": {}}), expected=1)
                self.assertEqual(result["error"]["code"], "unknown-platform")
                self.assertNotIn("recipe", result)

    def test_detect_rejects_control_characters_with_structured_errors(self):
        for character in ("\n", "\r", "\t", "\x01", "\x1b", "\x7f", "\x85"):
            with self.subTest(character=repr(character)):
                result = self.cli("detect", "--ros-distro", "lyrical" + character + "invalid", expected=2)
                self.assertEqual(result["error"]["code"], "invalid-fact")
                self.assertNotIn("facts", result)
                raw = json.loads((FIXTURES / "ubuntu.json").read_text())
                raw["facts"]["ros_distro"]["values"] = ["lyrical" + character + "invalid"]
                self.cli("classify", self.write(raw), expected=2)

    def test_successful_detector_facts_always_replay_through_classifier(self):
        for distro in ("lyrical", "configured-distro", ""):
            with self.subTest(distro=distro):
                detected = self.cli("detect", "--ros-distro", distro)
                replay = self.cli("classify", self.write({"schema_version": 1, "facts": detected["facts"]}))
                self.assertEqual(replay["platform"], detected["platform"])
                expected_state = "known" if distro else "unknown"
                self.assertEqual(detected["facts"]["ros_distro"]["state"], expected_state)

    def test_real_detection_is_passive_private_and_reclassifiable(self):
        trap = self.directory / "bin"
        trap.mkdir()
        for tool in ("apt-get", "dnf", "brew", "pixi", "docker", "podman", "wsl", "nvidia-smi", "uname", "sysctl"):
            path = trap / tool
            path.write_text("#!/bin/sh\nprintf called > '" + str(self.directory / "CALLED") + "'\nexit 99\n")
            path.chmod(0o755)
        env = dict(os.environ, PATH=str(trap), SSH_CONNECTION="secret-username-and-host", DISPLAY="secret-display-host:0")
        detected = self.cli("detect", "--ros-distro", "configured-distro", env=env)
        self.assertFalse((self.directory / "CALLED").exists())
        self.assertNotIn("secret", json.dumps(detected))
        self.assertEqual(detected["platform"]["ros_distro"]["values"], ["configured-distro"])
        self.assertEqual(detected["platform"]["ssh"]["values"], ["present"])
        self.assertEqual(detected["platform"]["display"]["values"], ["x11"] if not env.get("WAYLAND_DISPLAY") else ["wayland"])
        classified = self.cli("classify", self.write({"schema_version": 1, "facts": detected["facts"]}))
        self.assertEqual(detected["platform"], classified["platform"])
        self.assertEqual(detected["facts"]["network"]["state"], "not-observed")
        self.assertEqual(detected["facts"]["gpu"]["state"], "not-observed")


if __name__ == "__main__":
    unittest.main()
