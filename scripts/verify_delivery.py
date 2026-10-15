#!/usr/bin/env python3
"""Check the actual packaged files, native media policy and a fresh skill install."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from install_skill import install
from native_motion.qa import audit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delivery")
    args=parser.parse_args()
    delivery=Path(args.delivery).resolve()
    manifest=json.loads((delivery/"manifest.json").read_text())
    if manifest.get("kind")=="skill_source":
        from native_motion.source_package import verify_source
        print(json.dumps(verify_source(delivery),ensure_ascii=False,indent=2));return
    for name,record in manifest.items():
        path=delivery/name
        if path.stat().st_size!=record["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest()!=record["sha256"]:
            raise ValueError("Manifest mismatch: "+name)
    archive=delivery/"native-motion-ppt-skill.zip"
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            raise ValueError("ZIP checksum failed")
        for item in z.infolist():
            path=PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or any(p in {"node_modules",".cache","__pycache__",".git"} for p in path.parts):
                raise ValueError("Unsafe or cached archive entry: "+item.filename)
            if (item.external_attr>>16)&0o170000==0o120000:
                raise ValueError("Archive contains symlink: "+item.filename)
        version=z.read("native-motion-ppt/VERSION").decode().strip()
        entries=len(z.infolist())
    for name in ["demo.pptx","demo-auto.pptx","scientific.pptx","scientific-auto.pptx"]:
        result=audit(delivery/name)
        if result["issues"] or result["media_parts"]:
            raise ValueError("Native deck failed: "+name)
    for name in ["qa/audit.json","qa/auto/audit.json","qa/science/audit.json","qa/science/auto/audit.json"]:
        data=json.loads((delivery/name).read_text())
        if data["issues"]:
            raise ValueError("PPT QA failed: "+name)
    for name in ["qa/dynamic/preview-audit.json","qa/motion/motion-audit.json","qa/video/video-audit.json",
                 "qa/science/dynamic/preview-audit.json","qa/science/motion/motion-audit.json",
                 "qa/science/video/video-audit.json","qa/science/data/scientific-audit.json"]:
        data=json.loads((delivery/name).read_text())
        if data["errors"]:
            raise ValueError("Preview QA failed: "+name)
    data=json.loads((delivery/"qa/video/video-audit.json").read_text())
    if hashlib.sha256((delivery/"demo-design-preview.mp4").read_bytes()).hexdigest()!=data["video_sha256"]:
        raise ValueError("Packaged video differs from checked video")
    data=json.loads((delivery/"qa/science/video/video-audit.json").read_text())
    if hashlib.sha256((delivery/"scientific-design-preview.mp4").read_bytes()).hexdigest()!=data["video_sha256"]:
        raise ValueError("Packaged scientific video differs from checked video")
    provenance=json.loads((delivery/"delivery-provenance.json").read_text())
    if provenance["design_video"]["is_pptx_playback_recording"] is not False:
        raise ValueError("Code design preview incorrectly identified as desktop recording")
    if provenance["pptx"]["sha256"]!=hashlib.sha256((delivery/"scientific.pptx").read_bytes()).hexdigest():
        raise ValueError("Provenance belongs to another scientific deck")
    if provenance["design_video"]["sha256"]!=hashlib.sha256((delivery/"scientific-design-preview.mp4").read_bytes()).hexdigest():
        raise ValueError("Provenance belongs to another design video")
    if provenance["source_sha256"]!=hashlib.sha256((delivery/"native-motion-ppt/examples/scientific.json").read_bytes()).hexdigest():
        raise ValueError("Packaged design source differs from provenance")
    target=provenance["target_desktop_playback"]
    if target["status"] not in ("pending_retest","user_reported_pass") or target["recording"] is not None:
        raise ValueError("No target-player recording is bundled; distinguish pending or user-reported status")
    if target["status"]=="user_reported_pass" and not target.get("user_feedback",{}).get("quote"):
        raise ValueError("User-reported pass requires the actual feedback")
    desktop_recordings=[]
    for item in provenance.get("independent_desktop_recordings",[]):
        evidence=json.loads((delivery/item["evidence"]).read_text())
        if evidence["origin"]!="native_desktop_screen_capture" or evidence["is_pptx_playback_recording"] is not True:
            raise ValueError("Incorrect desktop-recording provenance")
        if evidence["source_pptx_sha256"]!=hashlib.sha256((delivery/item["pptx"]).read_bytes()).hexdigest():
            raise ValueError("Desktop evidence belongs to another deck")
        if evidence["recording_sha256"]!=hashlib.sha256((delivery/item["video"]).read_bytes()).hexdigest():
            raise ValueError("Desktop recording differs from evidence")
        if evidence.get("opened_copy_sha256",evidence["source_pptx_sha256"])!=evidence["source_pptx_sha256"]:
            raise ValueError("Playback copy differed from original")
        measured=json.loads((delivery/item["bar_audit"]).read_text())
        if measured["errors"] or measured["recording_sha256"]!=evidence["recording_sha256"]:
            raise ValueError("Native bar measurements failed or belong to another recording")
        for bar in measured["summary"]:
            if bar["distinct_top_positions"]<5 or bar["max_bottom_deviation_px"]>measured["tolerance_px"] or bar["max_backward_top_step_px"]>measured["tolerance_px"]:
                raise ValueError("Native bar reveal is absent or unstable")
        desktop_recordings.append({"player":evidence["player"],"version":evidence["version"],"video":item["video"]})
    for name in ["wps-bar-retest.pptx","wps-bar-retest-auto.pptx"]:
        if (delivery/name).is_file():
            result=audit(delivery/name)
            if result["issues"] or result["media_parts"] or len(result["slides"])!=1:
                raise ValueError("One-page native retest failed: "+name)
    with tempfile.TemporaryDirectory() as temporary:
        installed=install(delivery/"native-motion-ppt",temporary)
        source=Path(installed["path"])
        subprocess.run([sys.executable,str(source/"scripts/validate_skill.py")],check=True,capture_output=True,text=True)
    report={"version":version,"manifest_files":len(manifest),"zip_entries":entries,
            "native_pptx":True,"video_matches_checked_source":True,
            "fresh_install_files":installed["files"],"design_video_is_pptx_recording":False,
            "target_desktop_playback":target,"independent_desktop_recordings":desktop_recordings,"errors":[]}
    (delivery/"package-check.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
