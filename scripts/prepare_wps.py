#!/usr/bin/env python3
"""Open a real private WPS GUI for first-launch inspection; never auto-accept dialogs."""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from record_wps import digest, toolchain, stop


def prepare(args):
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    profile=Path(args.wps_profile).resolve()
    if profile.is_relative_to(out):raise ValueError('Keep private profiles outside the delivery directory')
    tools,env=toolchain(args.tools_root,args.wps_root)
    info=json.loads((Path(args.wps_root)/'wps-install.json').read_text())
    if info['status']!='installed_pending_gui_test' or digest(info['executable'])!=info['executable_sha256']:
        raise ValueError('A dependency-complete, checksum-pinned installation is required')
    n=next(i for i in range(91,120) if not Path(f'/tmp/.X11-unix/X{i}').exists() and not Path(f'/tmp/.X{i}-lock').exists())
    env['DISPLAY']=f':{n}';player_env=env.copy()
    for key in ['URE_BOOTSTRAP','UNO_PATH','SAL_USE_VCLPLUGIN']:player_env.pop(key,None)
    player_env.update(LD_LIBRARY_PATH=':'.join(info['library_paths'])+':'+env.get('LD_LIBRARY_PATH',''),
                      QT_PLUGIN_PATH=str(Path(info['executable']).parent/'qt/plugins'),
                      XDG_CONFIG_HOME=str(profile/'config'),XDG_CACHE_HOME=str(profile/'cache'),XDG_DATA_HOME=str(profile/'data'))
    processes=[];handles=[]
    def spawn(cmd,name,child_env):
        log=(out/name).open('w');handles.append(log)
        p=subprocess.Popen(cmd,env=child_env,stdout=log,stderr=log,start_new_session=True);processes.append(p);return p
    try:
        x=spawn([tools['xvfb'],env['DISPLAY'],'-screen','0','1920x1080x24','-dpi','96','-nolisten','tcp','-noreset'],'xvfb.log',env)
        deadline=time.monotonic()+10
        while not Path(f'/tmp/.X11-unix/X{n}').exists():
            if x.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Xvfb startup failed')
            time.sleep(.05)
        spawn([tools['openbox'],'--sm-disable'],'window-manager.log',env)
        spawn([info['executable'],str(Path(args.pptx).resolve())],'player.log',player_env)
        (out/'session.json').write_text(json.dumps({'display':env['DISPLAY'],'xdotool':tools['xdotool'],
            'tools_library_path':env.get('LD_LIBRARY_PATH',''),'note':'Inspect latest.png; use this display with xdotool to handle only known dialogs. No automatic acceptance.'},indent=2)+'\n')
        print(json.dumps({'display':env['DISPLAY'],'snapshot':str(out/'latest.png'),'session':str(out/'session.json')},indent=2),flush=True)
        end=time.monotonic()+args.seconds
        while time.monotonic()<end:
            subprocess.run([tools['ffmpeg'],'-hide_banner','-loglevel','error','-y','-f','x11grab','-video_size','1920x1080',
                '-i',env['DISPLAY'],'-frames:v','1','-update','1',str(out/'latest.png')],env=env,check=True)
            time.sleep(2)
    finally:
        for p in reversed(processes):stop(p)
        for h in handles:h.close()


if __name__=='__main__':
    def interrupt(signum,frame):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupt)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pptx');p.add_argument('--out',required=True)
    p.add_argument('--wps-root',required=True);p.add_argument('--wps-profile',required=True);p.add_argument('--tools-root');p.add_argument('--seconds',type=float,default=120)
    prepare(p.parse_args())
