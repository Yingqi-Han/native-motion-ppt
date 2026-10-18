"""Dependency diagnostics which run even when none of the optional libraries exist."""
import importlib.util
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ('pptx', 'lxml', 'jsonschema', 'fontTools', 'PIL')
MODULES = (*CORE, 'fitz', 'playwright', 'numpy')
STAGES = ('build', 'preview', 'render', 'browser', 'video', 'analysis', 'playback', 'acceptance')


def available(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def repair(label, *argv):
    arguments = [str(a) for a in argv]
    return {'label': label, 'argv': arguments, 'command': subprocess.list2cmdline(arguments) if os.name == 'nt' else shlex.join(arguments)}


def collect(target=None, tools_root=None, wps_root=None, wps_profile=None, spec=None):
    from .browser import browser_path
    modules = {name: available(name) for name in MODULES}
    commands = {name: shutil.which(name) for name in ('python', 'node', 'npm', 'soffice', 'chromium', 'ffmpeg', 'ffprobe', 'fc-match')}
    browser_error = None
    try:
        browser = browser_path()
    except ValueError as exc:
        browser, browser_error = None, str(exc)
    fonts = {}
    if commands['fc-match']:
        for family in ('Space Grotesk SemiBold', 'Noto Sans CJK SC', 'Noto Serif CJK SC'):
            try:
                match = subprocess.run(['fc-match', '-f', '%{family}', family], capture_output=True, text=True, timeout=5)
                fonts[family] = match.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                fonts[family] = None
    office = commands['soffice']
    if tools_root:
        candidate = Path(tools_root).expanduser() / 'root/usr/lib/libreoffice/program/soffice'
        office = str(candidate.resolve()) if candidate.is_file() else None
    doc, source_error, missing_fonts = None, None, []
    if spec and all(modules[x] for x in CORE):
        try:
            from .model import load
            from .fonts import text_objects, resolve_font
            doc = load(spec)
            requests = {(o['font'], o['bold']) for s in doc['slides'] for o in text_objects(s['objects'])}
            for family, bold in sorted(requests):
                face = resolve_font(family, bold)
                if not face or not face['matched']:
                    missing_fonts.append(family + (' (bold)' if bold else ''))
        except (ImportError, ValueError, OSError) as exc:
            source_error = str(exc)
    node_version = None
    if commands['node']:
        try:
            node_version = subprocess.check_output([commands['node'], '--version'], text=True, timeout=5).strip()
        except (OSError, subprocess.SubprocessError):
            pass
    backend = None
    if target:
        if not all(modules[x] for x in CORE):
            backend = {'target': target, 'status': 'pending', 'issues': ['Core dependencies are missing; player/font checks not performed'], 'fonts': []}
        else:
            try:
                from .players import preflight
                backend = preflight(target, tools_root, wps_root, wps_profile, doc)
            except (ImportError, ValueError, OSError) as exc:
                backend = {'target': target, 'status': 'pending', 'issues': [str(exc)], 'fonts': []}
    core_repair = repair('Install native export dependencies', sys.executable, '-m', 'pip', 'install', '-r', ROOT / 'requirements-core.txt')
    full_repair = repair('Install preview and analysis dependencies', sys.executable, '-m', 'pip', 'install', '-r', ROOT / 'requirements.txt')
    browser_repair = repair('Install a Chromium browser for Playwright', sys.executable, '-m', 'playwright', 'install', 'chromium')
    stages = {}

    def stage(name, required_modules=CORE, required_commands=(), needs_browser=False, needs_office=False, needs_player=False, needs_fonts=False):
        missing = ['Python module: ' + m for m in required_modules if not modules[m]]
        missing += ['Command: ' + c for c in required_commands if not commands[c]]
        fixes = []
        if sys.version_info < (3, 10):
            missing.append('Python 3.10+ is required')
            fixes.append({'label': 'Install Python 3.10 or newer', 'url': 'https://www.python.org/downloads/'})
        if source_error:
            missing.append('Source JSON: ' + source_error)
        if any(not modules[m] for m in required_modules):
            fixes.append(core_repair if set(required_modules).issubset(CORE) else full_repair)
        if needs_browser and not browser:
            missing.append(browser_error or 'Chromium executable is not installed')
            if not modules['playwright'] and full_repair not in fixes:
                fixes.append(full_repair)
            fixes.append(browser_repair)
        if needs_fonts and missing_fonts:
            missing += ['Requested font is unavailable or substituted: ' + f for f in missing_fonts]
            fixes.append({'label': 'Install the full requested fonts before preview/render; bundled Latin font supports the minimal starter', 'reference': str(ROOT / 'references/first-project.md')})
        if needs_office and not office:
            missing.append('LibreOffice static renderer')
            fixes.append(repair('Install Debian amd64 desktop tools, or supply an installed office toolchain', sys.executable, ROOT / 'scripts/install_desktop_player.py', '--tools-root', Path.home() / '.local/share/native-motion-ppt/desktop'))
        node_supported = bool(node_version and node_version.lstrip('v').split('.')[0].isdigit() and int(node_version.lstrip('v').split('.')[0]) >= 20)
        if 'node' in required_commands and commands['node'] and not node_supported:
            missing.append('Node.js 20+ is required; found ' + str(node_version))
        if any(c in required_commands and not commands[c] for c in ('node', 'npm')) or ('node' in required_commands and not node_supported):
            fixes.append({'label': 'Install Node.js 20+ including npm', 'url': 'https://nodejs.org/en/download'})
        if any(c in required_commands and not commands[c] for c in ('ffmpeg', 'ffprobe')):
            fixes.append({'label': 'Install FFmpeg and ffprobe using your operating system package manager', 'url': 'https://ffmpeg.org/download.html'})
        if needs_player and (not backend or backend.get('status') != 'passed'):
            missing += (backend or {}).get('issues', ['Select a real desktop backend with --target-player'])
            fixes.append({'label': 'Prepare the chosen real player and fonts; never substitute another backend', 'reference': str(ROOT / 'references/wps-playback.md' if target == 'wps-desktop' else ROOT / 'references/desktop-playback.md')})
        stages[name] = {'status': 'pending' if missing else 'passed', 'missing': missing, 'repairs': fixes}

    stage('build')
    stage('preview', needs_fonts=True)
    stage('render', (*CORE, 'fitz'), needs_office=True, needs_fonts=True)
    stage('browser', (*CORE, 'playwright'), needs_browser=True, needs_fonts=True)
    stage('video', (*CORE, 'playwright'), ('node', 'npm', 'ffmpeg', 'ffprobe'), needs_browser=True, needs_fonts=True)
    stage('analysis', (*CORE, 'numpy'), ('ffmpeg', 'ffprobe'))
    stage('playback', (*CORE, 'numpy'), ('ffmpeg', 'ffprobe'), needs_player=True)
    stage('acceptance', MODULES, ('node', 'npm', 'ffmpeg', 'ffprobe'), needs_browser=True, needs_office=True, needs_player=True, needs_fonts=True)
    result = {'python': platform.python_version(), 'core_pptx': all(modules[m] for m in CORE), 'modules': modules,
              'commands': commands, 'font_matches': fonts, 'packaged_latin_font': (ROOT / 'assets/fonts/SpaceGrotesk-SemiBold.ttf').is_file(),
              'static_office_render': stages['render']['status'] == 'passed', 'browser_sampling': stages['browser']['status'] == 'passed',
              'remotion_project_generation': bool(commands['node'] and commands['npm']),
              'native_playback_measurement': stages['analysis']['status'] == 'passed', 'microsoft_powerpoint_live_test': False,
              'browser_executable': browser, 'office_executable': office, 'node_version': node_version, 'source_font_issues': missing_fonts, 'stages': stages,
              'scope': 'Dependency readiness only. Export, browser previews and real desktop playback have separate evidence.'}
    if backend:
        result['selected_desktop_backend'] = backend
    return result


def print_report(report, stage=None, as_json=False):
    if stage:
        report = {**report, 'requested_stage': stage, 'status': report['stages'][stage]['status']}
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    selected = [stage] if stage else STAGES
    for name in selected:
        row = report['stages'][name]
        print(f"{name}: {row['status']}")
        for missing in row['missing']:
            print('  - ' + missing)
        for fix in row['repairs']:
            print('  ' + fix['label'] + ': ' + fix.get('command', fix.get('reference', fix.get('url', ''))))
    print(report['scope'])
