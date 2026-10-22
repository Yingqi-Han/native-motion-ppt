#!/usr/bin/env python3
"""Verify a single project's manifest, provenance, ZIP and editable skill install."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path,PurePosixPath

from install_skill import install
from native_motion.acceptance import STATES,sha,save


def verify(root):
    root=Path(root).resolve();manifest=json.loads((root/"manifest.json").read_text())
    for name,record in manifest.items():
        path=PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:raise ValueError("Unsafe manifest path")
        actual=root/name
        if not actual.is_file() or actual.is_symlink() or actual.stat().st_size!=record["bytes"] or sha(actual)!=record["sha256"]:
            raise ValueError("Manifest mismatch: "+name)
    data=json.loads((root/"acceptance.json").read_text())
    if data['source']['snapshot'] not in manifest:raise ValueError('Source snapshot is missing from the portable manifest')
    if sha(root/data["source"]["snapshot"])!=data["source"]["sha256"]:raise ValueError("Source snapshot changed")
    checks=data["checks"]
    if any(c["status"] not in STATES for c in checks):raise ValueError("Invalid acceptance state")
    failed=any(c["status"]=="failed" for c in checks) or any(s["status"]!="passed" for s in data["stages"])
    pending=any(c["status"]=="pending" and c["required"] for c in checks)
    expected="failed" if failed else "pending" if pending else "passed"
    if data["acceptance_status"]!=expected:raise ValueError("Overall acceptance contradicts individual checks")
    if data["pipeline_status"]!=("failed" if failed else "completed"):raise ValueError("Unfinished pipeline cannot certify acceptance")
    target=next((c for c in checks if c["id"]=="target-player"),None)
    if data.get('format_version',1)>=2:
        from native_motion.evidence import verify_dual_recordings,verify_reviews
        verify_dual_recordings(root,data);verify_reviews(root,data)
        auto_failed=any(c.get('automatic_status',c['status'])=='failed' for c in checks) or any(s['status']!='passed' for s in data['stages'])
        auto_pending=any(c.get('automatic_status',c['status'])=='pending' and c['required'] and not c.get('review_only',False) for c in checks)
        if data.get('automatic_acceptance_status')!=('failed' if auto_failed else 'pending' if auto_pending else 'passed'):raise ValueError('Automatic summary contradicts raw check states')
        diagnostic=root/'qa/diagnostics/diagnostics.json'
        if diagnostic.is_file():
            from native_motion.diagnostics import verify_diagnostics
            verify_diagnostics(root,diagnostic)
    if data.get('format_version',1)<2 and target and target["status"]=="passed" and data.get("requested_target_player")!="impress-desktop":
        raise ValueError("Impress capture cannot certify another target player")
    for artifact in data["artifacts"]:
        if sha(root/artifact["path"])!=artifact["sha256"]:raise ValueError("Artifact differs from acceptance evidence")
    stages=[s["id"] for s in data["stages"]]
    for implementation in {s['implementation']['snapshot']:s['implementation'] for s in data['stages'] if s.get('implementation')}.values():
        snapshot=root/implementation['snapshot']
        if not snapshot.resolve().is_relative_to(root):raise ValueError('Unsafe implementation snapshot')
        with zipfile.ZipFile(snapshot) as z:
            versions=json.loads(z.read('implementation-manifest.json'))
            digest=hashlib.sha256(json.dumps(versions,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if digest!=implementation['sha256'] or z.testzip():raise ValueError('Implementation revision changed')
            for name,digest in versions.items():
                path=PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts or hashlib.sha256(z.read(name)).hexdigest()!=digest:raise ValueError('Implementation file changed')
    if "design-render" in stages and "native-build" in stages and stages.index("design-render")>stages.index("native-build"):
        raise ValueError("Native export preceded the checked design video")
    if (root/"design-preview.mp4").is_file():
        video=json.loads((root/"qa/video/video-audit.json").read_text())
        if video["is_pptx_playback_recording"] is not False or video["errors"] or video["video_sha256"]!=sha(root/"design-preview.mp4"):
            raise ValueError("Invalid design-preview origin or checks")
    if (root/"player-recording.mp4").is_file():
        proof=json.loads((root/"playback-evidence.json").read_text())
        if proof["origin"]!="native_desktop_screen_capture" or proof["is_pptx_playback_recording"] is not True:
            raise ValueError("Invalid native-recording origin")
        if proof["source_pptx_sha256"]!=sha(root/"deck.pptx") or proof["recording_sha256"]!=sha(root/"player-recording.mp4"):
            raise ValueError("Desktop evidence belongs to another run")
        if proof.get("opened_copy_sha256")!=proof["source_pptx_sha256"]:raise ValueError("Opened playback copy differs")
        for audit in ((root/"qa").rglob("*playback-audit.json") if data.get('format_version',1)<2 else []):
            measured=json.loads(audit.read_text())
            if measured["recording_sha256"]!=proof["recording_sha256"] or measured["source_pptx_sha256"]!=proof["source_pptx_sha256"]:
                raise ValueError("Native measurements belong to another run")
            if audit.name=="native-motion-playback-audit.json":
                if measured["source_json_sha256"]!=sha(root/"project.json") or measured["planned_input_sha256"]!=sha(root/"playback-plan.json"):
                    raise ValueError("Motion measurements belong to a different source or planned input")
                state=next((c["status"] for c in checks if c["id"]=="native-motion"),None)
                if state=="passed" and (measured["status"]!="passed" or measured["errors"]):raise ValueError("Motion acceptance contradicts actual measurements")
    if (root/"regression").is_dir():
        from verify_motion_regression import verify as verify_regression
        verify_regression(root/"regression")
    archive=root/"acceptance-delivery.zip";stamp=json.loads((root/"archive.json").read_text())
    if sha(archive)!=stamp["sha256"]:raise ValueError("Delivery archive changed")
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip():raise ValueError("ZIP CRC failure")
        names=set(zipped.namelist())
        if names!=set(manifest)|{"manifest.json"}:raise ValueError("ZIP differs from delivery manifest")
        for entry in zipped.infolist():
            path=PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or any(p in {"node_modules","__pycache__","player-profile","input"} for p in path.parts):
                raise ValueError("Cache or private files in archive")
            if (entry.external_attr>>16)&0o170000==0o120000:raise ValueError("Symlink in archive")
            if entry.filename in manifest and hashlib.sha256(zipped.read(entry.filename)).hexdigest()!=manifest[entry.filename]["sha256"]:
                raise ValueError("Archived file differs from manifest")
    with tempfile.TemporaryDirectory() as folder:
        installed=install(root/"project",folder)
        subprocess.run([sys.executable,str(Path(installed["path"])/"scripts/validate_skill.py")],check=True,capture_output=True,text=True)
    report={"manifest_files":len(manifest),"archive_entries":len(names),"fresh_install_files":installed["files"],
            "acceptance_status":expected,"target_player_status":next((c["status"] for c in checks if c["id"]=="target-player"),"pending"),
            "design_and_playback_origins_separate":True,"errors":[]}
    save(root/"package-check.json",report);return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("run")
    print(json.dumps(verify(parser.parse_args().run),indent=2))
