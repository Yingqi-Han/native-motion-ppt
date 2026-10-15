#!/usr/bin/env python3
"""Install the checksum-pinned vendor Linux package in a task directory only."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parent


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def install(root,package=None):
    if platform.system()!='Linux' or platform.machine()!='x86_64':raise ValueError('Requires Linux amd64')
    meta=json.loads((HERE.parent/'assets/wps-official-package.json').read_text());root=Path(root).resolve()
    marker=root/'wps-install.json'
    if marker.exists():raise FileExistsError('Preserve an existing installation; select another root')
    root.mkdir(parents=True,exist_ok=True)
    if package:package=Path(package).resolve()
    else:
        package=root/'vendor-package.deb';partial=root/'vendor-package.partial'
        try:
            with urllib.request.urlopen(meta['url'],timeout=30) as response,partial.open('wb') as target:
                written=0;next_log=32*1024*1024
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk:break
                    written+=len(chunk)
                    if written>meta['bytes']:raise ValueError('Package exceeded its independently recorded size')
                    target.write(chunk)
                    if written>=next_log:print(f'Downloaded {written:,} bytes',flush=True);next_log+=32*1024*1024
            partial.replace(package)
        except (urllib.error.URLError,OSError) as error:
            raise RuntimeError('Official download failed through the configured network route; no mirror or proxy bypass attempted: '+str(error)) from error
        finally:
            if partial.exists():partial.unlink()
    if package.stat().st_size!=meta['bytes'] or digest(package)!=meta['sha256']:
        raise ValueError('Vendor package differs from the pinned independent checksum/size')
    fields={name:subprocess.check_output(['dpkg-deb','-f',str(package),name],text=True).strip()
            for name in ['Package','Version','Architecture']}
    if fields['Package']!='wps-office' or fields['Architecture']!='amd64' or not fields['Version'].startswith(meta['version']):
        raise ValueError('Unexpected Debian package identity')
    dest=root/'root';dest.mkdir(exist_ok=False)
    subprocess.run(['dpkg-deb','-x',str(package),str(dest)],check=True)
    office=dest/'opt/kingsoft/wps-office/office6';executable=office/'wpp'
    if not executable.is_file():raise ValueError('Verified package has no presentation executable')
    env=os.environ.copy();library_paths=[office,root/'deps/usr/lib/x86_64-linux-gnu']
    env['LD_LIBRARY_PATH']=':'.join(str(p) for p in library_paths)+':'+env.get('LD_LIBRARY_PATH','')
    checks=[subprocess.run(['ldd',str(p)],env=env,capture_output=True,text=True)
            for p in [executable,office/'qt/plugins/platforms/libqxcb.so']]
    missing=[line.strip() for result in checks for line in result.stdout.splitlines() if 'not found' in line]
    report={'player':meta['player'],'package_version':fields['Version'],'version_scope':'Verified vendor package metadata; GUI About still to check',
            'package_sha256':meta['sha256'],'package_bytes':meta['bytes'],'vendor_url':meta['url'],
            'executable':str(executable),'executable_sha256':digest(executable),'library_paths':list(map(str,library_paths)),
            'package_fields':fields,'missing_startup_libraries':missing,'status':'dependencies_missing' if missing or any(r.returncode for r in checks) else 'installed_pending_gui_test',
            'system_packages_changed':False,'native_playback_tested':False}
    marker.write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',required=True);parser.add_argument('--package')
    args=parser.parse_args();print(json.dumps(install(args.root,args.package),indent=2))
