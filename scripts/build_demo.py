#!/usr/bin/env python3
"""Design video first, then native PPT; report desktop playback as a separate layer."""
import argparse
import contextlib
import functools
import hashlib
import http.server
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def run(*args,cwd=ROOT):
    subprocess.run([str(a) for a in args],cwd=cwd,check=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass


@contextlib.contextmanager
def preview_server(folder,port=0):
    handler=functools.partial(QuietHandler,directory=str(folder))
    server=http.server.ThreadingHTTPServer(("127.0.0.1",port),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        yield f"http://localhost:{server.server_port}/preview.html"
    finally:
        server.shutdown();server.server_close()


def render_design(base,name,py,port,destination=None,legacy_alias=True):
    project=base/"preview/remotion"
    signature=hashlib.sha256((project/"package-lock.json").read_bytes()).hexdigest()
    stamp=project/"node_modules/.native-motion-lock"
    if not stamp.is_file() or stamp.read_text()!=signature:
        run("npm","ci","--no-audit","--no-fund",cwd=project)
        stamp.write_text(signature)
    run("npm","run","typecheck",cwd=project)
    browser=shutil.which("chromium")
    extra=["--browser-executable="+browser] if browser else []
    destination=Path(destination) if destination else base/(name+"-design-preview.mp4")
    stage=destination.with_name(destination.stem+".rendering.mp4")
    run("node","node_modules/@remotion/cli/remotion-cli.js","render","src/index.tsx","NativeMotion",stage,
        "--concurrency=2","--log=error",*extra,cwd=project)
    with preview_server(base/"preview",port) as url:
        run(py,"scripts/check_video.py",stage,"--url",url,"--out",base/"qa/video")
    stage.replace(destination)
    report=base/"qa/video/video-audit.json"
    data=json.loads(report.read_text());data["video"]=str(destination)
    report.write_text(json.dumps(data,indent=2))
    if legacy_alias:shutil.copy2(destination,base/(name+"-preview.mp4"))
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video",action="store_true")
    parser.add_argument("--port",type=int,default=0)
    parser.add_argument("--example",choices=["brand","science"],default="brand")
    parser.add_argument("--target-player",choices=["wps-desktop","powerpoint-desktop","unspecified"],default="unspecified")
    args=parser.parse_args();py=sys.executable
    science=args.example=="science";base=ROOT/("output/science" if science else "output")
    name="scientific" if science else "demo"
    spec=ROOT/("examples/scientific.json" if science else "examples/demo.json")
    deck=base/(name+".pptx");automatic=base/(name+"-auto.pptx")
    run(py,"scripts/doctor.py")
    run(py,"scripts/create_science_demo.py" if science else "scripts/create_demo.py")
    run(py,"scripts/motion_ppt.py","review",spec,"--out",base/"review.json","--fail-on-warning")
    run(py,"scripts/motion_ppt.py","preview",spec,"--out",base/"preview","--remotion")
    with preview_server(base/"preview",args.port) as url:
        run(py,"scripts/check_preview.py","--url",url,"--out",base/"qa/dynamic")
        run(py,"scripts/check_motion.py","--url",url,"--object","sample-token" if science else "sculpture",
            "--max-step","24" if science else "8","--out",base/"qa/motion")
        if science:run(py,"scripts/check_scientific.py","--url",url,"--out",base/"qa/data")
    video=render_design(base,name,py,args.port) if args.video else None
    # Native export follows design rendering; its playback is a separate verification stage.
    run(py,"scripts/motion_ppt.py","build",spec,"--out",deck)
    run(py,"scripts/motion_ppt.py","build",spec,"--out",automatic,"--auto")
    run(py,"scripts/motion_ppt.py","check",deck,"--out",base/"qa","--render","--import-check")
    run(py,"scripts/motion_ppt.py","check",automatic,"--out",base/"qa/auto")
    if not science:
        run(py,"scripts/motion_ppt.py","choreograph","examples/roles-portrait.json","--mode","click","--fit-duration","--out","output/portrait-timed.json")
        run(py,"scripts/motion_ppt.py","build","output/portrait-timed.json","--out","output/portrait.pptx")
        run(py,"scripts/motion_ppt.py","check","output/portrait.pptx","--out","output/qa/portrait","--render","--import-check")
    provenance={"pipeline_order":["shared_scene_design",*( ["design_preview_render"] if video else [] ),"native_pptx_export","native_structure_and_import_checks","target_desktop_playback"],
        "design_video":{"path":str(video) if video else None,"origin":"Remotion/shared-code rendering","is_pptx_playback_recording":False,
                        "sha256":hashlib.sha256(video.read_bytes()).hexdigest() if video else None},
        "pptx":{"path":str(deck),"sha256":hashlib.sha256(deck.read_bytes()).hexdigest()},
        "source_sha256":hashlib.sha256(spec.read_bytes()).hexdigest(),
        "target_desktop_playback":{"player":args.target_player,"status":"pending_retest","recording":None,
                                   "system":None,"player_version":None,
                                   "note":"Code-preview QA and Office import do not establish target desktop playback"}}
    (base/"delivery-provenance.json").write_text(json.dumps(provenance,indent=2))
    print("Native deck prepared for desktop playback:",deck)
    print("Design preview origin: code-generated; target recording: not available")


if __name__=="__main__":main()
