#!/usr/bin/env python3
"""Package portable sources and a checked demo without dependency/cache trees."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKIP={"node_modules","__pycache__","output",".git",".venv",".pytest_cache"}
def copy_preview(folder,destination):
 font_files={Path(f["file"]).name for f in json.loads((folder/"fonts.json").read_text())}
 for path in folder.rglob("*"):
  rel=path.relative_to(folder)
  if not path.is_file() or path.is_symlink() or any(k in {"node_modules",".cache","out","build"} for k in rel.parts):continue
  if "fonts" in rel.parts and path.name not in font_files:continue
  dest=destination/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
 for name in ["Space-Grotesk-LICENSE.txt","Noto-CJK-COPYRIGHT.txt"]:
  shutil.copy2(ROOT/"assets/fonts"/name,destination/"fonts"/name)
def main():
 p=argparse.ArgumentParser();p.add_argument("--out",required=True);p.add_argument("--source-only",action="store_true",help="Package the installable skill without requiring generated demo outputs");a=p.parse_args()
 if a.source_only:
  from native_motion.source_package import package_source
  print(json.dumps(package_source(ROOT,a.out),ensure_ascii=False,indent=2));return
 out=Path(a.out).resolve()
 if out==ROOT or ROOT in out.parents:raise ValueError("Delivery folder must be outside source folder")
 out.mkdir(parents=True,exist_ok=True)
 source=out/"native-motion-ppt";source.mkdir(exist_ok=True)
 for path in ROOT.rglob("*"):
  rel=path.relative_to(ROOT)
  if not path.is_file() or path.is_symlink() or any(k in SKIP for k in rel.parts) or path.suffix==".pyc":continue
  dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
 demos={"output/demo.pptx":"demo.pptx","output/demo-auto.pptx":"demo-auto.pptx",
 "output/demo-preview.mp4":"demo-design-preview.mp4","output/qa/rendered/demo.pdf":"demo.pdf",
 "output/qa/rendered/contact.jpg":"preview.jpg","output/qa/dynamic/dynamic-contact.jpg":"dynamic-frames.jpg"}
 for src,name in demos.items():
  if not (ROOT/src).is_file():raise ValueError("Missing checked demo: "+src)
  shutil.copy2(ROOT/src,out/name)
 extras={"output/portrait.pptx":"portrait.pptx","output/portrait-timed.json":"portrait-source.json","output/review.json":"design-review.json",
         "output/qa/portrait/rendered/portrait.pdf":"portrait.pdf"}
 science={"output/science/scientific.pptx":"scientific.pptx",
          "output/science/scientific-auto.pptx":"scientific-auto.pptx",
          "output/science/scientific-design-preview.mp4":"scientific-design-preview.mp4",
          "output/science/qa/rendered/scientific.pdf":"scientific.pdf",
          "output/science/qa/rendered/contact.jpg":"scientific-pages.jpg",
          "output/science/qa/dynamic/dynamic-contact.jpg":"scientific-dynamic-frames.jpg",
          "output/science/review.json":"scientific-design-review.json",
          "output/science/delivery-provenance.json":"delivery-provenance.json"}
 for src in science:
  if not (ROOT/src).is_file():raise ValueError("Missing checked scientific demo: "+src)
 extras.update(science)
 for name in ["wps-bar-retest.pptx","wps-bar-retest-auto.pptx","wps-bar-retest-source.json"]:
  extras["output/science/"+name]=name
 desktop={"output/desktop/impress-player-recording.mp4":"impress-player-recording.mp4",
          "output/desktop/playback-evidence.json":"impress-playback-evidence.json",
          "output/desktop/playback-contact.jpg":"native-playback-frames.jpg",
          "output/desktop/automatic-readonly/player-recording.mp4":"impress-bar-auto-recording.mp4",
          "output/desktop/automatic-readonly/playback-evidence.json":"impress-bar-auto-evidence.json"}
 has_desktop=bool(json.loads((ROOT/"output/science/delivery-provenance.json").read_text()).get("independent_desktop_recordings"))
 if has_desktop:extras.update(desktop)
 for src,name in extras.items():
  if (ROOT/src).is_file():shutil.copy2(ROOT/src,out/name)
 provenance_path=out/"delivery-provenance.json"
 provenance=json.loads(provenance_path.read_text())
 provenance["design_video"]["path"]="scientific-design-preview.mp4"
 provenance["pptx"]["path"]="scientific.pptx"
 provenance["source_path"]="native-motion-ppt/examples/scientific.json"
 for item in provenance.get("independent_desktop_recordings",[]):
  evidence=out/item["evidence"]
  data=json.loads(evidence.read_text())
  data["recording"]=item["video"]
  data["source_pptx"]=item["pptx"]
  evidence.write_text(json.dumps(data,indent=2)+"\n")
 provenance_path.write_text(json.dumps(provenance,indent=2)+"\n")
 # Include the actual portable dual-output preview and Remotion source.
 copy_preview(ROOT/"output/preview",source/"examples/generated-preview")
 copy_preview(ROOT/"output/science/preview",source/"examples/generated-science-preview")
 shutil.copytree(ROOT/"output/qa",out/"qa",ignore=shutil.ignore_patterns("*.png","*.odp"),dirs_exist_ok=True)
 shutil.copytree(ROOT/"output/science/qa",out/"qa/science",ignore=shutil.ignore_patterns("*.png","*.odp"),dirs_exist_ok=True)
 desktop_qa=out/"qa/desktop";desktop_qa.mkdir(parents=True,exist_ok=True)
 for src,dest in {"output/desktop/native-bar-playback-audit.json":"manual-bars.json",
                  "output/desktop/automatic-readonly/native-bar-playback-audit.json":"auto-bars.json",
                  "output/desktop/python-tests.log":"python-tests.log",
                  "output/desktop/node-tests.log":"node-tests.log",
                  "output/desktop/capture.log":"manual-capture.log",
                  "output/desktop/automatic-readonly/capture.log":"auto-capture.log"}.items():
  if has_desktop and (ROOT/src).is_file():shutil.copy2(ROOT/src,desktop_qa/dest)
 if (ROOT/"QA_REPORT.md").exists():shutil.copy2(ROOT/"QA_REPORT.md",out/"QA_REPORT.md")
 archive=out/"native-motion-ppt-skill.zip"
 with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
  for path in sorted(source.rglob("*")):
   if path.is_file():z.write(path,path.relative_to(out))
  for name in list(demos.values())+list(extras.values())+["QA_REPORT.md"]:
   if (out/name).is_file():z.write(out/name,name)
  for path in sorted((out/"qa").rglob("*")):
   if path.is_file():z.write(path,path.relative_to(out))
 manifest={}
 for path in sorted(out.iterdir()):
  if path.is_file() and path.name!="manifest.json":manifest[path.name]={"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
 (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
 print(json.dumps({"archive":str(archive),"source":str(source),"files":len(manifest)},indent=2))
if __name__=="__main__":main()

