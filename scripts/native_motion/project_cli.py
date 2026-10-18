"""Small, lazy project entrypoint; creating a project and asking for help need only Python."""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = {'minimal': ('starter-minimal.json', 'generic'), 'product': ('product-intro.json', 'generic'),
             'progress': ('project-update.json', 'generic'), 'science': ('scientific.json', 'science')}
PLAYERS = {'wps': 'wps-desktop', 'impress': 'impress-desktop', 'powerpoint': 'powerpoint-desktop'}


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_path(value):
    path = Path(value).expanduser().resolve()
    if path.is_dir():
        config_file = path / 'nmp.json'
        config = json.loads(config_file.read_text()) if config_file.is_file() else {}
        if config and (config.get('format_version') != 1 or config.get('source') != 'project.json'):
            raise ValueError('Unsupported project configuration; expected format_version=1 and source=project.json')
        path = path / 'project.json'
    if not path.is_file() or path.suffix.lower() != '.json':
        raise ValueError('Supply an existing project folder or source JSON: ' + str(path))
    return path


def options(args):
    home = Path.home() / '.local/share/native-motion-ppt'
    def choose(argument, env, default):
        value = getattr(args, argument, None) or os.environ.get(env)
        return str(Path(value).expanduser().resolve()) if value else str(home / default) if (home / default).is_dir() else None
    return {'tools_root': choose('tools_root', 'NMP_DESKTOP_TOOLS', 'desktop'),
            'wps_root': choose('wps_root', 'NMP_WPS_ROOT', 'wps'),
            'wps_profile': choose('wps_profile', 'NMP_WPS_PROFILE', 'wps-profile')}


def ready(stage, args, spec=None):
    from .readiness import collect, print_report
    report = collect(PLAYERS.get(getattr(args, 'player', None)), spec=spec, **options(args))
    if report['stages'][stage]['status'] != 'passed':
        print_report(report, stage)
        return False
    return True


def project_new(destination, template='minimal', title=None):
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Project destination already exists; existing files were preserved: ' + str(destination))
    resolved = destination.resolve()
    if resolved == ROOT or (ROOT in resolved.parents and resolved.relative_to(ROOT).parts[0] != 'output'):
        raise ValueError('Use output/ inside the skill, or a project directory outside it')
    filename, profile = TEMPLATES[template]
    doc = json.loads((ROOT / 'examples' / filename).read_text(encoding='utf-8'))
    if title:
        doc['title'] = title
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.nmp-new-', dir=destination.parent))
    try:
        save(stage / 'project.json', doc)
        save(stage / 'nmp.json', {'format_version': 1, 'source': 'project.json', 'template': template, 'profile': profile})
        if profile == 'science':
            data = stage / 'data'
            data.mkdir()
            for source, target in [('scientific-demo.csv', 'observations.csv'), ('scientific-manifest.json', 'figures.json')]:
                shutil.copy2(ROOT / 'examples/data' / source, data / target)
        entry = shlex.join([sys.executable, str(ROOT / 'scripts/nmp.py')])
        folder = shlex.quote(str(destination))
        (stage / 'README.md').write_text(f'''# {doc['title']}

Edit project.json to change the text, data, layout and motion. nmp.json identifies this project; a custom --title changes project metadata, not every slide headline.

```bash
{entry} doctor --for build
{entry} build {folder}
{entry} preview {folder}
{entry} accept {folder} --player wps
```

Native export needs requirements-core.txt. Full acceptance additionally needs the browser/video/Office dependencies, a prepared real WPS installation and fonts. Use doctor --for acceptance --player wps for exact missing requirements and repair instructions. Player paths can be supplied by --tools-root, --wps-root and --wps-profile, or NMP_DESKTOP_TOOLS / NMP_WPS_ROOT / NMP_WPS_PROFILE.

Generated files go under output/ in this project. Old runs and source are preserved. A successful export does not certify desktop playback. Example data is simulated; replace it with checked inputs before using it to make factual claims.
''', encoding='utf-8')
        (stage / '.gitignore').write_text('output/\n.venv/\n')
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {'project': str(destination), 'source': str(destination / 'project.json'), 'template': template}


def output_base(spec):
    base = spec.parent / 'output'
    if ROOT in base.parents and base.relative_to(ROOT).parts[0] != 'output':
        base = ROOT / 'output'
    return base


def output_dir(spec, kind, supplied=None):
    output = Path(supplied).expanduser().resolve() if supplied else output_base(spec) / (kind + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6])
    if output == ROOT or (ROOT in output.parents and output.relative_to(ROOT).parts[0] != 'output'):
        raise ValueError('Use output/ inside the skill, or an output directory outside it')
    output.mkdir(parents=True, exist_ok=False)
    return output


def export(spec, destination=None, strict=False):
    from .model import load
    from .review import review
    from .pptx_export import build
    from .qa import audit
    original_sha = sha(spec)
    doc = load(spec)
    source_review = review(doc)
    if source_review['errors'] or (strict and source_review['warnings']):
        raise ValueError('Source review requires changes: ' + json.dumps(source_review['issues'], ensure_ascii=False))
    out = output_dir(spec, 'build', destination)
    shutil.copy2(spec, out / 'project.json')
    save(out / 'source-review.json', source_review)
    report = {'status': 'running', 'origin': 'native_pptx_export', 'source_sha256': original_sha,
              'source_review_warnings': source_review['warnings'], 'artifacts': [],
              'desktop_playback': {'status': 'pending', 'reason': 'No desktop capture in this export; use nmp accept for actual playback.'}}
    try:
        for automatic, filename in [(False, 'deck.pptx'), (True, 'deck-auto.pptx')]:
            path = out / filename
            mapping = build(doc, path, auto=automatic)
            save(path.with_suffix('.manifest.json'), {'mapping': mapping, 'source_json_sha256': original_sha})
            native = audit(path)
            save(out / (filename + '.audit.json'), native)
            if native['issues']:
                raise ValueError('Native structure check failed: ' + '; '.join(native['issues']))
            report['artifacts'].append({'path': filename, 'sha256': sha(path), 'kind': 'native_auto_pptx' if automatic else 'native_manual_pptx'})
        if sha(spec) != original_sha or sha(out / 'project.json') != original_sha:
            raise ValueError('Input source changed during export')
        report['status'] = 'passed'
    except BaseException as exc:
        report.update(status='failed', error=str(exc))
        raise
    finally:
        save(out / 'build-report.json', report)
    return {'output': str(out), 'report': str(out / 'build-report.json'), **report}


def accept(args, spec):
    command = [sys.executable, str(ROOT / 'scripts/accept_project.py')]
    paths = options(args)
    if args.resume:
        command += ['--resume', str(Path(args.resume).expanduser().resolve()), '--mode', args.mode]
    else:
        profile = args.profile
        config = spec.parent / 'nmp.json'
        if not profile and config.is_file():
            profile = json.loads(config.read_text()).get('profile')
        profile = profile or 'generic'
        if profile not in ('generic', 'science'):
            raise ValueError('Unknown project profile')
        command += [str(spec), '--profile', profile]
        if profile == 'science':
            csv, figures = spec.parent / 'data/observations.csv', spec.parent / 'data/figures.json'
            if csv.is_file() and figures.is_file():
                command += ['--science-csv', str(csv), '--science-manifest', str(figures)]
            elif config.is_file():
                raise ValueError('Science project data is missing: restore data/observations.csv and data/figures.json')
    output = Path(args.out).expanduser().resolve() if args.out else (output_base(spec) / 'acceptance' if not args.resume else Path(args.resume).expanduser().resolve().parent)
    command += ['--out', str(output)]
    if args.player:
        command += ['--target-player', PLAYERS[args.player]]
    for key, flag in [('tools_root', '--desktop-tools-root'), ('wps_root', '--wps-root'), ('wps_profile', '--wps-profile')]:
        if paths[key]:
            command += [flag, paths[key]]
    if args.run_name:
        command += ['--run-name', args.run_name]
    if args.strict:
        command += ['--strict']
    return subprocess.run(command, cwd=ROOT).returncode


def add_player_options(parser, default=None):
    parser.add_argument('--player', choices=PLAYERS, default=default)
    parser.add_argument('--tools-root')
    parser.add_argument('--wps-root')
    parser.add_argument('--wps-profile')


def main(argv=None):
    from .readiness import STAGES
    parser = argparse.ArgumentParser(description='Native Motion PPT: start, export, preview and verify real playback.')
    parser.add_argument('--version', action='version', version=(ROOT / 'VERSION').read_text().strip())
    commands = parser.add_subparsers(dest='command', required=True)
    new = commands.add_parser('new', help='Create an editable project; no dependencies beyond Python')
    new.add_argument('folder'); new.add_argument('--template', choices=TEMPLATES, default='minimal'); new.add_argument('--title')
    doctor = commands.add_parser('doctor', help='Check only the tools needed for the chosen task')
    doctor.add_argument('--for', dest='stage', choices=STAGES, default='build'); doctor.add_argument('--json', action='store_true'); doctor.add_argument('--spec')
    add_player_options(doctor)
    for name in ['build', 'preview']:
        cmd = commands.add_parser(name, help='Export native manual/auto PPTX' if name == 'build' else 'Generate a portable browser/Remotion design preview')
        cmd.add_argument('project'); cmd.add_argument('--out')
        if name == 'build':
            cmd.add_argument('--strict', action='store_true', help='Also reject source review warnings')
    enhance = commands.add_parser('enhance', help='Add animation to an existing PPT; preserve input and existing animation')
    enhance.add_argument('pptx'); enhance.add_argument('--out', required=True); enhance.add_argument('--plan')
    acceptance = commands.add_parser('accept', help='Run full acceptance or immutable record/check reruns')
    acceptance.add_argument('project', nargs='?'); acceptance.add_argument('--out'); acceptance.add_argument('--resume')
    acceptance.add_argument('--mode', choices=['full', 'record', 'check'], default='full')
    acceptance.add_argument('--profile', choices=['generic', 'science']); acceptance.add_argument('--run-name'); acceptance.add_argument('--strict', action='store_true')
    add_player_options(acceptance)
    args = parser.parse_args(argv)
    try:
        if args.command == 'new':
            result = project_new(args.folder, args.template, args.title)
        elif args.command == 'doctor':
            from .readiness import collect, print_report
            report = collect(PLAYERS.get(args.player), spec=source_path(args.spec) if args.spec else None, **options(args))
            print_report(report, args.stage, args.json)
            return 0 if report['stages'][args.stage]['status'] == 'passed' else 2
        elif args.command in ('build', 'preview'):
            spec = source_path(args.project)
            if not ready(args.command, args, spec):
                return 2
            if args.command == 'build':
                result = export(spec, args.out, args.strict)
            else:
                from .model import load
                from .preview import generate
                doc = load(spec)
                out = output_dir(spec, 'preview', args.out)
                preview = generate(doc, out, remotion=True)
                result = {'preview': str(preview), 'origin': 'code_generated_design_preview', 'is_pptx_playback_recording': False,
                          'serve_command': shlex.join([sys.executable, '-m', 'http.server', '3020', '--directory', str(out)])}
        elif args.command == 'enhance':
            source, output = Path(args.pptx).expanduser().resolve(), Path(args.out).expanduser().absolute()
            if not source.is_file() or source.suffix.lower() != '.pptx':
                raise ValueError('Input must be an existing PPTX')
            report_file = output.with_suffix('.enhance-report.json')
            if output.exists() or output.is_symlink() or source == output.resolve() or report_file.exists():
                raise ValueError('Choose a new PPTX output path; existing files were preserved')
            if not ready('build', args):
                return 2
            source_sha = sha(source)
            command = [sys.executable, str(ROOT / 'scripts/motion_ppt.py'), 'enhance', str(source), '--out', str(output)]
            if args.plan:
                command += ['--plan', str(Path(args.plan).expanduser().resolve())]
            output.parent.mkdir(parents=True, exist_ok=True)
            code = subprocess.run(command, cwd=ROOT).returncode
            if code:
                return code
            from .qa import audit
            native = audit(output, strict=False)
            if sha(source) != source_sha:
                raise ValueError('Input PPTX changed during enhancement')
            report = {'status': 'failed' if native['issues'] else 'passed', 'origin': 'native_pptx_enhancement',
                      'source_pptx_sha256': source_sha, 'output_pptx_sha256': sha(output), 'native_audit': native,
                      'desktop_playback': {'status': 'pending', 'reason': 'Real desktop playback has not been recorded'}}
            save(report_file, report)
            print(json.dumps({'output': str(output), 'report': str(report_file), 'status': report['status']}, ensure_ascii=False, indent=2))
            return 1 if native['issues'] else 0
        else:
            if args.resume and (args.project or args.mode == 'full'):
                raise ValueError('--resume requires --mode record/check and no project argument')
            if not args.resume and (not args.project or args.mode != 'full'):
                raise ValueError('Supply a project for full acceptance, or --resume with --mode record/check')
            spec = source_path(Path(args.resume).expanduser() / 'project.json') if args.resume else source_path(args.project)
            if not args.player and not args.resume:
                args.player = 'wps'
            if args.resume and args.mode == 'record' and not args.player:
                previous = json.loads((Path(args.resume).expanduser() / 'acceptance.json').read_text())
                canonical = previous.get('requested_target_player')
                args.player = next((k for k, v in PLAYERS.items() if v == canonical), None)
                if not args.player:
                    raise ValueError('Resume run has no supported requested player')
            stage = {'full': 'acceptance', 'record': 'playback', 'check': 'analysis'}[args.mode]
            if not ready(stage, args, spec):
                return 2
            return accept(args, spec)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ImportError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        if isinstance(exc, ImportError):
            print('Run nmp.py doctor --for build (or acceptance) for dependency repair commands.', file=sys.stderr)
        return 2
