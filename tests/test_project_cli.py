"""First-run behavior and task routing; unit mocks never count as playback evidence."""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from native_motion.project_cli import main, project_new, export, output_base
from native_motion.readiness import CORE, collect
from native_motion.browser import browser_path
from native_motion.model import load
from native_motion.review import review
from native_motion.fonts import resolve_font


class FirstRunTests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, '-S', str(ROOT / 'scripts/nmp.py'), *args], capture_output=True, text=True)

    def test_help_and_creation_work_without_site_packages(self):
        self.assertEqual(self.cli('--help').returncode, 0)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'my-project'
            result = self.cli('new', str(folder), '--template', 'product')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(load(folder / 'project.json')['title'], '产品介绍 · 原生演示示例')

    def test_missing_dependencies_produce_repairs_without_traceback(self):
        result = self.cli('doctor', '--for', 'acceptance', '--player', 'wps', '--json')
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertFalse(report['core_pptx'])
        self.assertEqual(report['status'], 'pending')
        self.assertEqual(report['stages']['build']['repairs'][0]['argv'][:4], [sys.executable, '-m', 'pip', 'install'])
        self.assertIn('requirements-core.txt', report['stages']['build']['repairs'][0]['command'])
        self.assertNotIn('Traceback', result.stderr)

    def test_legacy_doctor_selected_backend_does_not_import_missing_dependencies(self):
        result = subprocess.run([sys.executable, '-S', str(ROOT / 'scripts/doctor.py'), '--target-player', 'wps-desktop', '--strict'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['selected_desktop_backend']['status'], 'pending')
        self.assertNotIn('Traceback', result.stderr)

    def test_existing_project_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'user.txt').write_text('keep')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                project_new(folder, 'progress')
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ['user.txt'])
            self.assertEqual((folder / 'user.txt').read_text(), 'keep')

    def test_science_project_carries_its_editable_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'science'
            project_new(folder, 'science', 'A custom title')
            self.assertEqual(json.loads((folder / 'project.json').read_text())['title'], 'A custom title')
            self.assertEqual(json.loads((folder / 'nmp.json').read_text())['profile'], 'science')
            self.assertEqual((folder / 'data/observations.csv').read_bytes(), (ROOT / 'examples/data/scientific-demo.csv').read_bytes())

    def test_generated_files_stay_out_of_source_directories(self):
        self.assertEqual(output_base(ROOT / 'examples/product-intro.json'), ROOT / 'output')
        with self.assertRaisesRegex(ValueError, 'output/'):
            project_new(ROOT / 'accidental-project', 'minimal')


class ReadinessTests(unittest.TestCase):
    def report(self, modules, commands=()):
        with patch('native_motion.readiness.available', side_effect=lambda name: name in modules), \
             patch('native_motion.readiness.shutil.which', side_effect=lambda name: '/unit/' + name if name in commands else None), \
             patch('native_motion.browser.browser_path', return_value=None):
            return collect()

    def test_core_export_does_not_require_browser_video_or_office(self):
        r = self.report(set(CORE))
        self.assertEqual(r['stages']['build']['status'], 'passed')
        self.assertEqual(r['stages']['preview']['status'], 'passed')
        self.assertEqual(r['stages']['acceptance']['status'], 'pending')
        self.assertFalse(r['microsoft_powerpoint_live_test'])

    def test_check_only_analysis_does_not_require_a_player(self):
        r = self.report(set(CORE) | {'numpy'}, ['ffmpeg', 'ffprobe'])
        self.assertEqual(r['stages']['analysis']['status'], 'passed')
        self.assertEqual(r['stages']['playback']['status'], 'pending')

    def test_invalid_browser_override_cannot_silently_use_a_different_browser(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {'NMP_BROWSER_EXECUTABLE': str(Path(temporary) / 'missing-browser')}):
            with self.assertRaisesRegex(ValueError, 'NMP_BROWSER_EXECUTABLE'):
                browser_path()

    def test_bundled_latin_font_wins_over_unmatched_system_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            fake = Path(temporary) / 'fallback.ttf'
            fake.write_bytes(b'not used as a font')
            response = argparse.Namespace(stdout=str(fake) + '\nUnrelated Font\nRegular\n0')
            resolve_font.cache_clear()
            try:
                with patch('native_motion.fonts.subprocess.run', return_value=response):
                    info = resolve_font('Space Grotesk SemiBold')
                self.assertTrue(info['matched'])
                self.assertEqual(Path(info['path']), ROOT / 'assets/fonts/SpaceGrotesk-SemiBold.ttf')
            finally:
                resolve_font.cache_clear()

    def test_old_node_is_not_reported_ready_for_video(self):
        with patch('native_motion.readiness.available', return_value=True), \
             patch('native_motion.readiness.shutil.which', side_effect=lambda name: '/unit/' + name if name != 'fc-match' else None), \
             patch('native_motion.readiness.subprocess.check_output', return_value='v18.20.0'), \
             patch('native_motion.browser.browser_path', return_value='/unit/browser'):
            r = collect()
        self.assertEqual(r['stages']['video']['status'], 'pending')
        self.assertTrue(any('20+' in missing for missing in r['stages']['video']['missing']))
        self.assertEqual(r['stages']['build']['status'], 'passed')


class ExportAndDispatchTests(unittest.TestCase):
    def test_both_native_exports_preserve_source_and_keep_playback_pending(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'project'
            project_new(folder, 'minimal')
            source = folder / 'project.json'
            before = source.read_bytes()
            out = folder / 'new-build'
            r = export(source, out)
            self.assertEqual(r['status'], 'passed')
            self.assertEqual(r['desktop_playback']['status'], 'pending')
            self.assertEqual(len(r['artifacts']), 2)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual((out / 'project.json').read_bytes(), before)
            with self.assertRaises(FileExistsError):
                export(source, out)
            self.assertEqual(source.read_bytes(), before)

    def test_invalid_source_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'invalid.json'
            source.write_text('{"version":1,"slides":[]}')
            out = Path(temporary) / 'must-not-exist'
            with self.assertRaises(ValueError):
                export(source, out)
            self.assertFalse(out.exists())

    def test_wps_dispatch_uses_exact_selected_backend(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            folder = Path(temporary) / 'project'
            project_new(folder, 'product')
            with patch('native_motion.project_cli.ready', return_value=True), patch('native_motion.project_cli.subprocess.run', return_value=argparse.Namespace(returncode=0)) as run:
                self.assertEqual(main(['accept', str(folder), '--player', 'wps', '--wps-root', '/unit/wps', '--wps-profile', '/unit/profile']), 0)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[cmd.index('--target-player') + 1], 'wps-desktop')
            self.assertNotIn('impress-desktop', cmd)
            self.assertIn('--wps-profile', cmd)

    def test_check_resume_gates_analysis_without_starting_a_player(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            folder = Path(temporary) / 'run'
            project_new(folder, 'minimal')
            with patch('native_motion.project_cli.ready', return_value=True) as ready, patch('native_motion.project_cli.subprocess.run', return_value=argparse.Namespace(returncode=0)) as run:
                self.assertEqual(main(['accept', '--resume', str(folder), '--mode', 'check']), 0)
            self.assertEqual(ready.call_args.args[0], 'analysis')
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[cmd.index('--mode') + 1], 'check')
            self.assertNotIn('--target-player', cmd)

    def test_direct_science_example_does_not_invent_data_paths(self):
        with redirect_stdout(io.StringIO()), patch('native_motion.project_cli.ready', return_value=True), patch('native_motion.project_cli.subprocess.run', return_value=argparse.Namespace(returncode=0)) as run:
            self.assertEqual(main(['accept', str(ROOT/'examples/scientific.json'), '--profile', 'science', '--player', 'wps']), 0)
        self.assertNotIn('--science-csv', run.call_args.args[0])

    def test_science_project_with_missing_data_cannot_use_unrelated_example_data(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stderr(io.StringIO()):
            folder=Path(temporary)/'project';project_new(folder,'science');(folder/'data/observations.csv').unlink()
            with patch('native_motion.project_cli.ready',return_value=True),patch('native_motion.project_cli.subprocess.run') as run:
                self.assertEqual(main(['accept',str(folder),'--player','wps']),2)
            run.assert_not_called()

    def test_enhance_rejects_input_overwrite_before_loading_pptx(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stderr(io.StringIO()):
            source = Path(temporary) / 'input.pptx'
            source.write_bytes(b'unit preservation fixture, not a real PPT')
            self.assertEqual(main(['enhance', str(source), '--out', str(source)]), 2)
            self.assertEqual(source.read_bytes(), b'unit preservation fixture, not a real PPT')

    def test_starters_have_valid_layout_timing_and_measurable_shared_subjects(self):
        for filename, ident in [('product-intro.json', 'product-token'), ('project-update.json', 'delivery-marker')]:
            doc = load(ROOT / 'examples' / filename)
            audit = review(doc)
            self.assertEqual((audit['errors'], audit['warnings']), (0, 0), filename)
            a = next(o for o in doc['slides'][0]['objects'] if o['id'] == ident)
            b = next(o for o in doc['slides'][1]['objects'] if o['id'] == ident)
            self.assertNotEqual(a['box'], b['box'])
            self.assertEqual(doc['slides'][1]['transition']['kind'], 'morph')


if __name__ == '__main__':
    unittest.main()
