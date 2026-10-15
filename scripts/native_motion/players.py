"""Explicit desktop backends and dependency/font preflight; never substitute a player."""
import json
import os
import subprocess
from pathlib import Path

from .acceptance import sha

PLAYERS={'impress-desktop':'LibreOffice Impress','wps-desktop':'WPS Office Presentation (Linux)'}

def player_matches(target,evidence):
    return evidence.get('player')==PLAYERS.get(target) and evidence.get('origin')=='native_desktop_screen_capture' and evidence.get('is_pptx_playback_recording') is True


def preflight(target,tools_root=None,wps_root=None,wps_profile=None,doc=None):
    result={'target':target,'status':'pending','issues':[],'fonts':[],'scope':'Dependency/font readiness only. Real recording and GUI checkpoints are checked separately.'}
    if target not in PLAYERS:
        result['issues'].append('This environment has no real backend for '+target);return result
    try:
        if target=='wps-desktop':
            from record_wps import toolchain
            tools,env=toolchain(tools_root,wps_root or True)
            if not wps_root:raise ValueError('--wps-root is required; no Impress substitution')
            root=Path(wps_root).resolve();meta=json.loads((root/'wps-install.json').read_text())
            if meta['status']!='installed_pending_gui_test':raise ValueError('WPS installation has unresolved dependencies')
            if sha(meta['executable'])!=meta['executable_sha256']:raise ValueError('WPS executable checksum changed')
            if not wps_profile or not (Path(wps_profile)/'config/Kingsoft/Office.conf').is_file():raise ValueError('Prepare real first launch and supply external --wps-profile')
            player_env=env.copy();player_env['LD_LIBRARY_PATH']=':'.join(meta['library_paths'])+':'+env.get('LD_LIBRARY_PATH','')
            plugin=Path(meta['executable']).parent/'qt/plugins/platforms/libqxcb.so'
            for binary in [Path(meta['executable']),plugin]:
                ld=subprocess.run(['ldd',str(binary)],env=player_env,text=True,capture_output=True)
                if ld.returncode or 'not found' in ld.stdout:raise ValueError('Missing startup libraries: '+str(binary))
            env.update(XDG_CONFIG_HOME=str(Path(wps_profile).resolve()/'config'),XDG_DATA_HOME=str(Path(wps_profile).resolve()/'data'),XDG_CACHE_HOME=str(Path(wps_profile).resolve()/'cache'))
            result.update(package_version=meta['package_version'],package_sha256=meta['package_sha256'],executable_sha256=meta['executable_sha256'])
        else:
            from record_desktop import toolchain
            tools,env=toolchain(tools_root)
        def text_objects(items):
            for o in items:
                if o['kind']=='text':yield o
                if o['kind']=='group':yield from text_objects(o['objects'])
        families=sorted({o['font'] for s in (doc or {}).get('slides',[]) for o in text_objects(s['objects'])})
        for family in families:
            match=subprocess.check_output(['fc-match','-f','%{family}\n%{file}',family],env=env,text=True).splitlines()
            matched=bool(match) and family.casefold() in [x.strip().casefold() for x in match[0].split(',')]
            result['fonts'].append({'requested':family,'resolved':match[0] if match else None,'file':match[1] if len(match)>1 else None,'matched':matched})
            if not matched:result['issues'].append('Font substitution in the actual player XDG environment: '+family)
        result['status']='pending' if result['issues'] else 'passed'
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:result['issues'].append(str(exc))
    return result


def recording_command(target,deck,out,plan,canvas,tools_root=None,wps_root=None,wps_profile=None):
    if target not in PLAYERS:raise ValueError('No available native backend: '+target)
    script='scripts/record_wps.py' if target=='wps-desktop' else 'scripts/record_desktop.py'
    cmd=[script,deck,'--out',out,'--seconds',plan['seconds'],'--show-after',plan['show_after'],
         '--width',canvas['width'],'--height',canvas['height'],'--fps',canvas['fps']]
    if tools_root:cmd+=['--tools-root',tools_root]
    if target=='wps-desktop':
        if not wps_root or not wps_profile:raise ValueError('WPS requires --wps-root and --wps-profile')
        cmd+=['--wps-root',wps_root,'--wps-profile',wps_profile]
    for t in plan['click_at']:cmd+=['--click-at',t]
    return cmd
