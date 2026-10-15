#!/usr/bin/env python3
"""Install a Debian GUI Impress/X11 toolchain locally, without changing system packages."""
import argparse
import getpass
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def install(destination):
    release=dict(line.split("=",1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    if release.get("ID","").strip('"')!="debian" or platform.machine()!="x86_64":
        raise ValueError("This installer supports Debian amd64; use the system's GUI LibreOffice installer elsewhere")
    suite=release["VERSION_CODENAME"].strip('"')
    if not suite.isalnum():
        raise ValueError("Unsupported Debian suite")
    destination=Path(destination).resolve();apt=destination/"apt";root=destination/"root"
    for folder in ["lists/partial","archives/partial","state"]:
        (apt/folder).mkdir(parents=True,exist_ok=True)
    (apt/"sources.list").write_text(f"deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian {suite} main\n")
    config=apt/"apt.conf"
    config.write_text(f'''Dir::Etc::main "/dev/null";
Dir::Etc::parts "-";
Dir::Etc::sourcelist "{apt}/sources.list";
Dir::Etc::sourceparts "-";
Dir::State "{apt}/state";
Dir::State::status "/var/lib/dpkg/status";
Dir::State::lists "{apt}/lists";
Dir::Cache::archives "{apt}/archives";
APT::Sandbox::User "{getpass.getuser()}";
Acquire::Retries "1";
Acquire::https::Timeout "20";
Debug::NoLocking "true";
''')
    command=["/usr/bin/apt-get","-c",str(config)]
    subprocess.run([*command,"update"],check=True)
    subprocess.run([*command,"--download-only","--no-install-recommends","-y","install",
                    "xvfb","xdotool","openbox","libreoffice-impress","libreoffice-core"],check=True)
    root.mkdir(exist_ok=True);packages=[]
    for package in sorted((apt/"archives").glob("*.deb")):
        subprocess.run(["dpkg-deb","-x",str(package),str(root)],check=True)
        packages.append({"file":package.name,"bytes":package.stat().st_size,
                         "sha256":hashlib.sha256(package.read_bytes()).hexdigest()})
    for path in root.rglob("*"):
        if path.is_symlink():
            target=path.readlink()
            if target.is_absolute() and (root/target.relative_to("/")).exists():
                relative=os.path.relpath(root/target.relative_to("/"),path.parent)
                path.unlink();path.symlink_to(relative)
    office=root/"usr/lib/libreoffice"
    target=root/"etc/libreoffice/registry/main.xcd";target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(office/"share/.registry/main.xcd",target)
    link=office/"share/registry/main.xcd"
    if link.is_symlink():link.unlink()
    link.symlink_to(os.path.relpath(target,link.parent))
    rc=office/"program/fundamentalrc"
    rc.write_text(rc.read_text().replace("BRAND_BASE_DIR=file:///usr/lib/libreoffice","BRAND_BASE_DIR="+office.as_uri()))
    env=os.environ.copy()
    env.update(URE_BOOTSTRAP=(office/"program/fundamentalrc").as_uri(),UNO_PATH=str(office/"program"),
               LD_LIBRARY_PATH=str(office/"program")+":"+str(root/"usr/lib/x86_64-linux-gnu")+":"+env.get("LD_LIBRARY_PATH",""))
    version=subprocess.check_output([str(office/"program/soffice"),"--version"],env=env,text=True).strip()
    report={"player":version,"tools_root":str(destination),"source":"signed Debian package repository",
            "system_packages_changed":False,"packages":packages}
    (destination/"installed-packages.json").write_text(json.dumps(report,indent=2)+"\n")
    return {k:v for k,v in report.items() if k!="packages"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools-root",required=True)
    args=parser.parse_args()
    print(json.dumps(install(args.tools_root),indent=2))
