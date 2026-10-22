"""Exercise the first project with only core dependencies; no Office or browser launch."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def smoke(python, workspace):
    entry = ROOT / 'scripts/nmp.py'
    def run(*arguments, json_output=True):
        process = subprocess.run([str(python), str(entry), *map(str, arguments)], capture_output=True, text=True, encoding='utf-8')
        if process.returncode:
            raise RuntimeError(process.stdout + '\n' + process.stderr)
        return json.loads(process.stdout) if json_output else process.stdout
    report = run('doctor', '--for', 'build', '--json')
    assert report['status'] == 'passed'
    assert not any(report['modules'][module] for module in ['numpy', 'fitz', 'playwright']), 'Use --isolated; this smoke verifies core-only installation'
    project = workspace / 'project with spaces'
    run('new', project)
    source = project / 'project.json'
    original = source.read_bytes()
    build = run('build', project, '--out', workspace / 'native-output', '--strict')
    assert build['status'] == 'passed' and build['desktop_playback']['status'] == 'pending'
    preview = run('preview', project, '--out', workspace / 'design-preview')
    assert preview['is_pptx_playback_recording'] is False
    fonts = json.loads((workspace / 'design-preview/font-audit.json').read_text())
    assert fonts and all(face.get('matched') for face in fonts)
    assert source.read_bytes() == original
    old = workspace / 'native-output/deck.pptx'
    enhanced = workspace / 'enhanced.pptx'
    run('enhance', old, '--out', enhanced, json_output=False)
    enhanced_report = json.loads(enhanced.with_suffix('.enhance-report.json').read_text())
    assert enhanced_report['status'] == 'passed' and enhanced_report['desktop_playback']['status'] == 'pending'
    with zipfile.ZipFile(old) as before, zipfile.ZipFile(enhanced) as after:
        for name in before.namelist():
            if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                assert before.read(name) == after.read(name), 'Existing layout and animation must be preserved'
    fixture=workspace/'existing source.pptx'
    subprocess.run([str(python),str(ROOT/'scripts/create_existing_demo.py'),'--out',str(fixture)],capture_output=True,text=True,encoding='utf-8',check=True)
    fixture_bytes=fixture.read_bytes()
    proposal=run('plan',fixture,'--max-clicks','2','--out',workspace/'proposal')
    plan=json.loads(Path(proposal['plan']).read_text(encoding='utf-8'))
    assert plan['source_pptx_sha256']==hashlib.sha256(fixture_bytes).hexdigest()
    assert proposal['proposed_slides']==2
    result=workspace/'existing enhanced.pptx'
    run('enhance',fixture,'--plan',proposal['plan'],'--out',result,json_output=False)
    report=json.loads(result.with_suffix('.enhance-report.json').read_text(encoding='utf-8'))
    assert report['status']=='passed' and report['preservation']['layout_and_relationships_preserved']
    assert fixture.read_bytes()==fixture_bytes
    with zipfile.ZipFile(fixture) as before,zipfile.ZipFile(result) as after:
        assert set(before.namelist())==set(after.namelist())
        allowed=set(report['preservation']['changed_timing_parts'])
        assert len(allowed)==2
        for name in before.namelist():
            if name not in allowed:assert before.read(name)==after.read(name),name
    return {'status': 'passed', 'platform': sys.platform, 'python': subprocess.check_output([str(python), '--version'], text=True).strip(),
            'core_only': True, 'source_preserved': True, 'source_sha256': hashlib.sha256(original).hexdigest(),
            'preview_fonts_match': True, 'manual_auto_and_existing_ppt_export': 'passed', 'existing_animations_preserved': True,
            'sha_bound_existing_plan': True, 'existing_package_parts_preserved': True,
            'desktop_playback': 'not executed', 'scope': 'Portable CLI/export/preview generation only; no WPS or PowerPoint compatibility claim'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated', action='store_true')
    parser.add_argument('--out')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nmp-core-') as temporary:
        workspace = Path(temporary)
        python = Path(sys.executable)
        if args.isolated:
            environment = workspace / 'venv'
            venv.create(environment, with_pip=True)
            python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            process = subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements-core.txt')], capture_output=True, text=True)
            if process.returncode:
                raise SystemExit(process.stdout + process.stderr)
        result = smoke(python, workspace)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
