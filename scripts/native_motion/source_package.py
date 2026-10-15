"""Portable source releases, independent of generated demo and playback outputs."""
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from install_skill import files, install


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package_source(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError('Use a separate output directory')
    # Only dist/ may be nested in the source; it is excluded by the installer.
    if source in destination.parents and destination.relative_to(source).parts[0] != 'dist':
        raise ValueError('Nested release output must be inside dist/')
    destination.mkdir(parents=True, exist_ok=True)
    version = (source / 'VERSION').read_text().strip()
    archive = destination / f'native-motion-ppt-v{version}.zip'
    members = files(source)
    manifest = {'format_version': 1, 'kind': 'skill_source', 'version': version, 'files': {}}
    stage = archive.with_suffix('.writing.zip')
    with zipfile.ZipFile(stage, 'w', zipfile.ZIP_DEFLATED) as output:
        for name, path in sorted(members.items()):
            data = path.read_bytes()
            info = zipfile.ZipInfo('native-motion-ppt/' + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, data)
            manifest['files'][name] = {'sha256': digest(data), 'bytes': len(data)}
    stage.replace(archive)
    manifest['archive'] = {'file': archive.name, 'sha256': digest(archive.read_bytes()), 'bytes': archive.stat().st_size}
    (destination / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return {'archive': str(archive), 'version': version, 'source_files': len(members)}


def verify_source(destination):
    destination = Path(destination).resolve()
    manifest = json.loads((destination / 'manifest.json').read_text())
    if manifest.get('kind') != 'skill_source' or manifest.get('format_version') != 1:
        raise ValueError('Unsupported source manifest')
    record = manifest['archive']
    archive_name = PurePosixPath(record['file'])
    if len(archive_name.parts) != 1 or archive_name.is_absolute():
        raise ValueError('Unsafe archive filename')
    archive = destination / record['file']
    if archive.stat().st_size != record['bytes'] or digest(archive.read_bytes()) != record['sha256']:
        raise ValueError('Source archive differs from manifest')
    with zipfile.ZipFile(archive) as zipped, tempfile.TemporaryDirectory() as temporary:
        names = zipped.namelist()
        expected = {'native-motion-ppt/' + name for name in manifest['files']}
        if len(names) != len(set(names)) or set(names) != expected or zipped.testzip():
            raise ValueError('Source archive inventory/CRC mismatch')
        for item in zipped.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or '..' in path.parts or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe source archive member')
            data = zipped.read(item)
            target = manifest['files'][str(path.relative_to('native-motion-ppt'))]
            if len(data) != target['bytes'] or digest(data) != target['sha256']:
                raise ValueError('Source member differs from manifest: ' + item.filename)
        if zipped.read('native-motion-ppt/VERSION').decode().strip() != manifest['version']:
            raise ValueError('Source version differs from manifest')
        zipped.extractall(temporary)
        installed = install(Path(temporary) / 'native-motion-ppt', Path(temporary) / 'workspace')
        subprocess.run([sys.executable, str(Path(installed['path']) / 'scripts/validate_skill.py')], check=True, capture_output=True, text=True)
    result = {'status': 'passed', 'version': manifest['version'], 'source_files': len(names),
              'fresh_install_files': installed['files'], 'archive_sha256': record['sha256'], 'errors': []}
    (destination / 'package-check.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
