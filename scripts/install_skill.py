#!/usr/bin/env python3
"""Managed installation/upgrades: verify tracked files, preserve edits, keep a backup."""
import argparse,hashlib,json,os,shutil,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKIP={"node_modules","__pycache__","output",".git",".github",".venv",".pytest_cache","dist","showcase"}
RECORD=".native-motion-install.json"
def files(root):
    return {p.relative_to(root).as_posix():p for p in root.rglob("*") if p.is_file() and not p.is_symlink() and not any(k in SKIP for k in p.relative_to(root).parts) and p.suffix!=".pyc" and p.name!=RECORD}
def hashes(items):return {name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in items.items()}
def install(root,workspace,upgrade=False):
    root=Path(root);workspace=Path(workspace).resolve();destination=workspace/".agents/skills/native-motion-ppt"
    src=files(root);expected=hashes(src)
    if destination.is_symlink():raise ValueError("Installation destination is a symlink")
    old={}
    if destination.exists():
        current=hashes(files(destination))
        if current==expected:return {"status":"already installed","path":str(destination)}
        if not upgrade:raise ValueError("Existing version differs; use --upgrade for a managed update")
        record=destination/RECORD
        if not record.exists():raise ValueError("Legacy installation has no baseline; preserve it before a manual migration")
        old=json.loads(record.read_text())
        changed=[n for n,v in old["files"].items() if current.get(n)!=v]
        collisions=[n for n in expected if n in current and n not in old["files"] and current[n]!=expected[n]]
        if changed or collisions:raise ValueError("Local edits preserved; upgrade stopped: "+", ".join(changed+collisions))
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix=".native-motion-stage-",dir=destination.parent));backup=None
    try:
        if destination.exists():shutil.copytree(destination,stage,dirs_exist_ok=True,symlinks=True)
        for n in old.get("files",{}):
            if n not in expected and (stage/n).is_file():(stage/n).unlink()
        for n,p in src.items():
            target=stage/n
            if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent!=stage):
                raise ValueError("Tracked path is a symlink: "+n)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        version=(root/"VERSION").read_text().strip() if (root/"VERSION").exists() else "1.0.0"
        (stage/RECORD).write_text(json.dumps({"name":"native-motion-ppt","version":version,"files":expected},indent=2))
        if destination.exists():
            stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup=workspace/".agents/skill-backups/native-motion-ppt"/stamp
            backup.parent.mkdir(parents=True,exist_ok=True);os.replace(destination,backup)
        try:os.replace(stage,destination)
        except Exception:
            if backup:os.replace(backup,destination)
            raise
    finally:
        if stage.exists():shutil.rmtree(stage)
    return {"status":"upgraded" if backup else "installed","version":version,"path":str(destination),"backup":str(backup) if backup else None,"files":len(src)}
def main():
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--upgrade",action="store_true")
    a=p.parse_args()
    try:print(json.dumps(install(ROOT,Path(a.workspace).expanduser(),a.upgrade),ensure_ascii=False,indent=2))
    except ValueError as e:raise SystemExit(str(e))
if __name__=="__main__":main()

