#!/usr/bin/env python3
"""Report real capabilities without installing anything."""
import argparse,importlib.util,json,platform,shutil,subprocess,sys
from pathlib import Path
modules={k:bool(importlib.util.find_spec(k)) for k in ["pptx","lxml","jsonschema","fontTools","PIL","fitz","playwright","numpy"]}
commands={k:shutil.which(k) for k in ["python","node","npm","soffice","chromium","ffmpeg","ffprobe"]}
fonts={}
if shutil.which("fc-match"):
 for name in ["Space Grotesk SemiBold","Noto Sans CJK SC"]:
  r=subprocess.run(["fc-match","-f","%{family}",name],capture_output=True,text=True)
  fonts[name]=r.stdout.strip()
root=Path(__file__).resolve().parents[1]
report={"python":platform.python_version(),"core_pptx":all(modules[k] for k in ["pptx","lxml","jsonschema","fontTools"]),
"modules":modules,"commands":commands,"font_matches":fonts,"packaged_latin_font":(root/"assets/fonts/SpaceGrotesk-SemiBold.ttf").is_file(),
"static_office_render":bool(commands["soffice"] and modules["fitz"] and modules["PIL"]),
"browser_sampling":bool(modules["playwright"] and commands["chromium"]),
"remotion_project_generation":bool(commands["node"] and commands["npm"]),
"native_playback_measurement":bool(modules["numpy"] and modules["PIL"] and modules["pptx"] and commands["ffmpeg"] and commands["ffprobe"]),
"microsoft_powerpoint_live_test":False}
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--target-player',choices=['impress-desktop','wps-desktop','powerpoint-desktop'])
parser.add_argument('--desktop-tools-root');parser.add_argument('--wps-root');parser.add_argument('--wps-profile');parser.add_argument('--spec');parser.add_argument('--strict',action='store_true')
args=parser.parse_args()
if args.target_player:
 from native_motion.players import preflight
 from native_motion.model import load
 report['selected_desktop_backend']=preflight(args.target_player,args.desktop_tools_root,args.wps_root,args.wps_profile,load(args.spec) if args.spec else None)
print(json.dumps(report,ensure_ascii=False,indent=2))
if args.strict and report.get('selected_desktop_backend',{}).get('status')=='pending':sys.exit(2)
if not report["core_pptx"]:sys.exit(1)

