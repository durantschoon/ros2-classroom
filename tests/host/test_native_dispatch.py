"""Native boundaries are subprocesses; fakes record every forbidden action."""

import copy
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

from fakes import REAL_PATH, REPO, SCRIPTS, ScriptTestCase
import test_native_recipes as fixtures

MAKE = shutil.which('make', path=REAL_PATH)
PWSH = os.environ.get('PWSH') or shutil.which('pwsh', path=REAL_PATH)
MODEL = REPO / 'scripts' / 'native-recipes'
CATALOG = REPO / 'recipes' / 'native' / 'ubuntu-apt.json'


def protocol(recipe=None, request=None, host='ubuntu'):
    item = recipe or fixtures.recipe()
    return {'schema_version': 1, 'catalog': {'schema_version': 1, 'recipes': [item]},
            'facts': json.loads((fixtures.FIXTURES / (host + '.json')).read_text()),
            'request': request or {'operation': item['operation'], 'parameters': {}}}


class NativeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.counter = 0

    def write(self, data, raw=False):
        self.counter += 1
        path = self.path / (str(self.counter) + '.json')
        path.write_text(data if raw else json.dumps(data), encoding='utf-8')
        return str(path)

    def call(self, command, *args, expected=0):
        run = subprocess.run([sys.executable, str(MODEL), command] + list(args),
                             capture_output=True, text=True, timeout=15)
        self.assertEqual(expected, run.returncode, run.stdout + run.stderr)
        self.assertEqual('', run.stderr)
        return json.loads(run.stdout)

    def test_every_student_mapping_and_parameter_case(self):
        cases = [('up', {}, 'install', {}), ('image', {}, 'install', {}),
                 ('desktop', {}, 'install', {}), ('open', {}, 'session', {'workspace': '/tmp/ws'}),
                 ('shell', {}, 'shell', {'workspace': '/tmp/ws'}),
                 ('turtlesim', {}, 'turtlesim', {'workspace': '/tmp/ws'}),
                 ('turtlesim-teleop', {}, 'teleop', {'workspace': '/tmp/ws'}),
                 ('build', {}, 'build-workspace', {'workspace': '/tmp/ws'}),
                 ('test', {}, 'test-workspace', {'workspace': '/tmp/ws'}),
                 ('build', {'PKG': 'robot'}, 'build', {'workspace': '/tmp/ws', 'package': 'robot'}),
                 ('test', {'PKG': 'robot'}, 'test', {'workspace': '/tmp/ws', 'package': 'robot'}),
                 ('run', {'PKG': 'robot', 'NODE': 'talker'}, 'run', {'workspace': '/tmp/ws', 'package': 'robot', 'node': 'talker'}),
                 ('package', {'PKG': 'robot'}, 'package', {'workspace': '/tmp/ws', 'package': 'robot', 'build_type': 'ament_cmake'}),
                 ('package', {'PKG': 'robot', 'PYTHON': '1'}, 'package', {'workspace': '/tmp/ws', 'package': 'robot', 'build_type': 'ament_python'}),
                 ('package', {'PKG': 'robot', 'TEMPLATE': 'pubsub'}, 'package-template', {'workspace': '/tmp/ws', 'package': 'robot', 'build_type': 'ament_cmake', 'template': 'pubsub'}),
                 ('package', {'PKG': 'robot', 'INTERFACES': '1'}, 'package-interfaces', {'workspace': '/tmp/ws', 'package': 'robot'})]
        for goal in ('logs', 'down', 'reset', 'uninstall', 'ps', 'engine', 'doctor', 'selftest', 'digest', 'teleop'):
            cases.append((goal, {}, 'container-maintenance', {}))
        for goal, values, operation, parameters in cases:
            with self.subTest(goal=goal, values=values):
                result = self.call('request', goal, self.write(dict(values, NATIVE_WORKSPACE='/tmp/ws')))
                self.assertEqual(operation, result['operation'])
                self.assertEqual(parameters, result['parameters'])
        for goal, values in [('build', {'PKG': 'one two'}), ('run', {'PKG': 'robot'}),
                             ('run', {'PKG': 'robot', 'NODE': '--help'}), ('package', {}),
                             ('package', {'PKG': 'robot', 'TEMPLATE': 'wrong'}),
                             ('package', {'PKG': 'robot', 'INTERFACES': '1', 'PYTHON': '1'}),
                             ('package', {'PKG': 'robot', 'INTERFACES': '1', 'TEMPLATE': 'pubsub'}),
                             ('build', {'NATIVE_WORKSPACE': 'relative/path'})]:
            self.call('request', goal, self.write(values), expected=2)

    def test_distro_precedence_and_interpolation_refusal(self):
        env = self.write('ROS_DISTRO="jazzy"\n', raw=True)
        cases = [({}, 'jazzy'), ({'ROS_DISTRO': 'humble'}, 'humble'),
                 ({'NATIVE_CONFIGURED_ROS_DISTRO': 'rolling', 'NATIVE_ROS_DISTRO_ORIGIN': 'command line'}, 'rolling'),
                 ({'NATIVE_CONFIGURED_ROS_DISTRO': 'lyrical', 'NATIVE_ROS_DISTRO_ORIGIN': 'file'}, 'jazzy')]
        for values, distro in cases:
            self.assertEqual(distro, self.call('configuration', self.write(values), env)['ros_distro'])
        for value in ('', '${OTHER:-lyrical}', 'lyrical; touch file', 'lyrical\n'):
            self.call('configuration', self.write({'ROS_DISTRO': value}), env, expected=2)
        self.assertEqual('lyrical', self.call('configuration', self.write({}), self.write('', raw=True))['ros_distro'])

    def test_paste_safe_quoting_and_evidence_on_every_group(self):
        values = {'workspace': "/tmp/space '雪 ; $(touch forbidden)", 'package': 'robot;echo bad', 'node': 'a"b`c\\d'}
        item = fixtures.recipe(operation='run', parameters=values)
        result = self.call('protocol', self.write(protocol(item, {'operation': 'run', 'parameters': values})))
        commands = [line for line in result['rendered'].splitlines() if not line.startswith('#')]
        self.assertEqual([['synthetic-never-execute'] + list(values.values())], [shlex.split(line) for line in commands])
        self.assertIn(item['verification']['reference'], result['rendered'])
        self.assertIn(item['verification']['status'], result['rendered'])
        self.assertFalse(result['admitted'])

    def test_candidate_catalog_exact_platform_coverage_and_mapping_semantics(self):
        catalog = json.loads(CATALOG.read_text())
        self.call('validate', str(CATALOG))
        self.assertEqual({('26.04', 'lyrical', 'native', arch) for arch in ('amd64', 'arm64')},
                         {(r['platform']['version'], r['platform']['ros_distro'], r['platform']['context'], r['platform']['architecture']) for r in catalog['recipes']})
        for item in catalog['recipes']:
            op = item['operation']
            parameters = {'workspace': '/tmp/native ws'}
            if op == 'install': parameters = {}
            if op in ('build', 'run', 'test', 'package'): parameters['package'] = 'robot'
            if op == 'package': parameters['build_type'] = 'ament_cmake'
            if op == 'run': parameters['node'] = 'talker'
            raw = protocol(item, {'operation': op, 'parameters': parameters})
            raw['facts']['facts']['os_version']['values'] = ['26.04']
            raw['facts']['facts']['machine']['values'] = ['x86_64' if item['platform']['architecture'] == 'amd64' else 'aarch64']
            result = self.call('protocol', self.write(raw))
            self.assertFalse(result['admitted'])
            rendered = result['rendered']
            subprocess.run(['bash', '-n'], input=rendered, text=True, check=True)
            if op == 'package':
                self.assertIn('--license Apache-2.0', rendered)
                self.assertIn('git config --global user.name', rendered)
            if op in ('build', 'build-workspace'): self.assertIn("'--symlink-install'", rendered)
            if op == 'test': self.assertIn('--test-result-base "$1/build/$2"', rendered)
            if op == 'test-workspace': self.assertIn('colcon test-result --verbose', rendered)
            if op in ('run', 'test', 'test-workspace'): self.assertIn('source "$1/install/setup.bash"', rendered)
        self.assertFalse({'package-template', 'package-interfaces', 'turtlesim', 'teleop'} & {r['operation'] for r in catalog['recipes']})

    def test_ubuntu_rendering_rejects_relative_and_windows_workspaces(self):
        item = fixtures.recipe(operation='shell', parameters=('workspace',))
        for workspace in ('relative/path', 'C:\\ros2_ws'):
            self.call('protocol', self.write(protocol(item, {'operation': 'shell', 'parameters': {'workspace': workspace}})), expected=2)

    def test_run_identity_and_fingerprint_admission_rejects_command_mutation(self):
        raw = protocol()
        result = self.call('protocol', self.write(raw))
        evidence = raw['catalog']['recipes'][0]['verification']
        evidence.update(reference='https://github.com/example/fixture/actions/runs/123',
                        procedure='Synthetic evidence test. Recipe SHA-256: ' + result['fingerprint'],
                        provenance={'ci_run': '123'})
        self.assertTrue(self.call('protocol', self.write(raw))['admitted'])
        evidence['provenance']['ci_run'] = '456'
        self.assertFalse(self.call('protocol', self.write(raw))['admitted'])
        evidence['provenance']['ci_run'] = '123'
        raw['catalog']['recipes'][0]['commands'][0]['argv'].append({'literal': 'changed'})
        self.assertFalse(self.call('protocol', self.write(raw))['admitted'])


@unittest.skipUnless(MAKE, 'make is not installed')
class DispatchSafetyTests(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.tree = self.sandbox.root / 'tree'
        self.tree.mkdir()
        shutil.copytree(str(SCRIPTS), str(self.tree / 'scripts'))
        shutil.copytree(str(REPO / 'recipes'), str(self.tree / 'recipes'))
        shutil.copy2(str(REPO / 'Makefile'), str(self.tree / 'Makefile'))
        self.sandbox.link('echo')
        for command in ('docker', 'podman', 'curl', 'xdg-open', 'wsl', 'apt-get', 'touch'):
            self.sandbox.fake(command, exit_code=37)
        # Record the detector itself, including invocation during Make parsing.
        detector = self.tree / 'scripts' / 'compose-command'
        detector.write_text('#!/usr/bin/env python3\nimport os,pathlib\npathlib.Path(os.environ["PROBE"]).touch()\nraise SystemExit(37)\n')
        detector.chmod(0o755)
        self.probe = self.sandbox.root / 'probe'

    def make(self, *args, **env):
        return subprocess.run([str(MAKE), '--no-print-directory'] + list(args), cwd=str(self.tree),
                              env=self.sandbox.environ(PROBE=str(self.probe), **env),
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)

    def assert_no_effects(self, result):
        self.assertFalse(self.probe.exists(), result.stdout + result.stderr)
        for command in ('docker', 'podman', 'curl', 'xdg-open', 'wsl', 'apt-get', 'touch'):
            self.assertFalse(self.sandbox.called(command), command + result.stdout + result.stderr)

    def test_only_parallel_mixed_goals_and_help_have_no_effects(self):
        for args in [(), ('up', 'open'), ('-j4', 'package', 'build', 'run', 'test', 'PKG=robot', 'NODE=talker'),
                     ('-j4', 'up', 'doctor', 'down'), ('help',), ('shell', 'help'), ('help', 'up'), ('-n', 'up')]:
            with self.subTest(args=args):
                result = self.make(*args, EXPLAIN='only')
                self.assert_no_effects(result)
                if args and 'help' not in args and '-n' not in args: self.assertNotEqual(0, result.returncode)

    def test_invalid_values_stop_before_even_detector_with_on(self):
        for value in ('robot;touch bad', "robot'", 'robot robot', '雪', '$(touch bad)', 'robot\n'):
            result = self.make('-j4', 'build', 'open', 'EXPLAIN=1', 'PKG=' + value)
            self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
            self.assert_no_effects(result)
        relative = self.make('build', 'EXPLAIN=1', 'NATIVE_WORKSPACE=relative/path')
        self.assertNotEqual(0, relative.returncode)
        self.assert_no_effects(relative)
        malformed = self.make('shell', 'EXPLAIN=only', 'ROS_DISTRO=$(shell touch forbidden)')
        self.assertNotEqual(0, malformed.returncode)
        self.assert_no_effects(malformed)
        self.assertFalse((self.tree / 'forbidden').exists())

    def test_off_has_no_extra_explanation_and_on_unsupported_then_workflow(self):
        off = self.make('shell', EXPLAIN='0')
        self.assertTrue(self.probe.exists())
        self.assertNotIn('Native commands', off.stdout + off.stderr)
        self.probe.unlink()
        on = self.make('shell', EXPLAIN='1')
        self.assertTrue(self.probe.exists())
        self.assertIn('Native commands unavailable', on.stdout + on.stderr)

    def test_env_file_not_overridden_in_workflow_by_make_default(self):
        (self.tree / '.env').write_text('ROS_DISTRO=jazzy\n')
        self.sandbox.fake('compose', record_env=('ROS_DISTRO',))
        detector = self.tree / 'scripts' / 'compose-command'
        detector.write_text('#!/bin/sh\nexit 0\n')
        result = self.make('shell', 'COMPOSE=compose', 'EXPLAIN=1')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertNotIn('ROS_DISTRO', self.sandbox.last_recorded_env('compose'))

    def test_selftest_explicitly_isolates_explanation(self):
        self.sandbox.fake('smoke', record_env=('EXPLAIN',))
        smoke = self.tree / 'scripts' / 'smoke-container'
        smoke.write_text('#!/bin/sh\nexec smoke\n')
        result = self.make('selftest', EXPLAIN='1')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertNotIn('Native commands', result.stdout + result.stderr)
        self.assertEqual('0', self.sandbox.last_recorded_env('smoke')['EXPLAIN'])
        self.assert_no_effects(result)


@unittest.skipUnless(PWSH, 'pwsh unavailable: actual parity runs in CI')
class PowerShellNativeParityTests(NativeBoundaryTests):
    # Inherited Python boundary checks remain useful; parity below goes through
    # the actual PowerShell file, with no Python executable on its PATH.
    def ps(self, path):
        env = dict(os.environ, POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off')
        env['PATH'] = str(self.path)
        result = subprocess.run([str(PWSH), '-NoProfile', '-NonInteractive', '-File', str(REPO / 'ros2.ps1'),
                                 '-NativeRecipeRequest', path], capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual('', result.stderr, result.stdout + result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_shared_valid_invalid_selection_evidence_and_quoting(self):
        values = {'workspace': "/tmp/雪 ' $(touch should-not-exist)", 'package': 'pkg;echo bad', 'node': 'node"`\\'}
        item = fixtures.recipe(operation='run', parameters=values)
        raw = protocol(item, {'operation': 'run', 'parameters': values})
        valid = [raw, protocol(host='windows'), protocol(host='debian')]
        for status in ('verified-by-hand', 'community-reported'):
            valid.append(protocol(fixtures.recipe(status=status)))
        admitted = copy.deepcopy(raw)
        admitted_item = admitted['catalog']['recipes'][0]
        admitted_item['commands'][0]['argv'].append({'literal': "Unicode 雪 ' \\"})
        admitted_item['guidance'].append('Unicode evidence fingerprint 雪')
        digest = self.call('protocol', self.write(admitted))['fingerprint']
        admitted_item['verification'].update(reference='https://github.com/example/fixture/actions/runs/123',
                                             provenance={'ci_run': '123'}, procedure='Synthetic fixture. Recipe SHA-256: ' + digest)
        valid.append(admitted)
        ambiguous = copy.deepcopy(raw)
        second = copy.deepcopy(item)
        second['id'] = 'second'
        second['verification']['subject'] = 'second'
        ambiguous['catalog']['recipes'].append(second)
        valid.append(ambiguous)
        invalid = []
        for mutate in [lambda r: r['catalog'].update(extra=1),
                       lambda r: r['catalog'].update(schema_version=True),
                       lambda r: r['catalog']['recipes'][0]['verification'].update(provenance={'report': 'wrong'}),
                       lambda r: r['catalog']['recipes'][0]['verification'].update(subject='wrong'),
                       lambda r: r['catalog']['recipes'][0]['verification'].update(date='2026-02-30'),
                       lambda r: r['catalog']['recipes'][0]['commands'][0]['argv'].append({'parameter': 'unknown'}),
                       lambda r: r['facts']['facts']['kernel_release'].update(state='unknown', values=['bad']),
                       lambda r: r['request']['parameters'].update(workspace='bad\n'),
                       lambda r: r['request']['parameters'].update(workspace='relative/path'),
                       lambda r: r['request']['parameters'].update(workspace='C:\\ros2_ws')]:
            value = copy.deepcopy(raw)
            mutate(value)
            invalid.append(value)
        for value in valid + invalid:
            path = self.write(value)
            py = subprocess.run([sys.executable, str(MODEL), 'protocol', path], capture_output=True, text=True)
            status, ps = self.ps(path)
            self.assertEqual(py.returncode, status, py.stdout + str(ps))
            expected = json.loads(py.stdout)
            self.assertEqual(expected['outcome'], ps['outcome'])
            if status == 0:
                self.assertEqual(expected, ps)
        valid_text = json.dumps(raw)
        for text in (valid_text.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1),
                     valid_text[:-1] + ',}', valid_text + '\u00a0', valid_text.replace('"schema_version": 1', '"schema_version": NaN', 1)):
            path = self.write(text, raw=True)
            self.assertEqual(2, self.ps(path)[0])


@unittest.skipUnless(PWSH, 'pwsh unavailable: actual Windows-wrapper safety runs in CI')
class PowerShellStudentSafetyTests(ScriptTestCase):
    def test_only_default_desktop_and_help_without_python_or_workflow_effects(self):
        tree = self.sandbox.root / 'tree'
        tree.mkdir()
        shutil.copy2(str(REPO / 'ros2.ps1'), str(tree / 'ros2.ps1'))
        shutil.copytree(str(REPO / 'recipes'), str(tree / 'recipes'))
        marker = self.sandbox.root / 'forbidden'
        for name in ('docker', 'podman', 'curl', 'xdg-open', 'wsl', 'apt-get', 'python3', 'python'):
            executable = self.sandbox.bin / name
            executable.write_text('#!/bin/sh\nprintf called >> ' + shlex.quote(str(marker)) + '\nexit 37\n')
            executable.chmod(0o755)
        for args in [[], ['shell', 'ROS_DISTRO='], ['desktop'], ['up'], ['open'], ['build'], ['run', 'PKG=robot', 'NODE=talker'],
                     ['help'], ['desktop', 'help']]:
            with self.subTest(args=args):
                run = subprocess.run([str(PWSH), '-NoProfile', '-NonInteractive', '-File', str(tree / 'ros2.ps1')] + args + ['EXPLAIN=only'],
                                     env=self.sandbox.environ(POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off'),
                                     capture_output=True, text=True, timeout=30)
                self.assertFalse(marker.exists(), run.stdout + run.stderr)
                self.assertEqual('', run.stderr, run.stdout + run.stderr)
                if 'help' not in args:
                    self.assertEqual(2, run.returncode, run.stdout)
                    self.assertIn('literal identifier' if 'ROS_DISTRO=' in args else 'unavailable', run.stdout)
