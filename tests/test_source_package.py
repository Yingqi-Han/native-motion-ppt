"""A source release must install exactly its checked bytes without local artifacts."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import native_motion
from native_motion.source_package import package_source, verify_source


class SourcePackageTests(unittest.TestCase):
    def test_version_is_read_from_canonical_file(self):
        self.assertEqual(native_motion.__version__, (ROOT / 'VERSION').read_text().strip())

    def test_source_release_is_reproducible_and_fresh_installable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_source(ROOT, root / 'first')
            package_source(ROOT, root / 'second')
            a = json.loads((root / 'first/manifest.json').read_text())
            b = json.loads((root / 'second/manifest.json').read_text())
            self.assertEqual(a, b)
            self.assertFalse(any(Path(n).parts[0] in {'showcase', '.github', 'dist'} for n in a['files']))
            report = verify_source(root / 'first')
            self.assertEqual(report['status'], 'passed')
            self.assertEqual(report['fresh_install_files'], len(a['files']))

    def test_changed_archive_is_rejected_before_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = package_source(ROOT, root)
            with Path(result['archive']).open('ab') as output:
                output.write(b'changed')
            with self.assertRaisesRegex(ValueError, 'differs from manifest'):
                verify_source(root)

    def test_nested_output_cannot_package_itself(self):
        with self.assertRaisesRegex(ValueError, 'inside dist'):
            package_source(ROOT, ROOT / 'accidental-release')
