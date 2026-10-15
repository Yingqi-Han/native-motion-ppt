"""Portable previews for all resolved project font faces and the shared timeline."""
import json,shutil,hashlib
from pathlib import Path
from .fonts import bundle_fonts
ROOT=Path(__file__).resolve().parents[2]
def generate(doc,output,remotion=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/"document.json").write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
    provenance={"artifact_type":"code_generated_design_preview","renderer":"shared SVG timeline / Chromium / Remotion",
                "is_pptx_playback_recording":False,"source_document_sha256":hashlib.sha256((output/"document.json").read_bytes()).hexdigest(),
                "purpose":"Design reference; native desktop playback must be checked separately"}
    (output/"preview-provenance.json").write_text(json.dumps(provenance,indent=2))
    for name in ("preview.html","timeline.mjs"):shutil.copy2(ROOT/"assets"/name,output/name)
    manifest=bundle_fonts(doc,output)
    (output/"fonts.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    html=(output/"preview.html").read_text()
    (output/"preview.html").write_text(html.replace("</head>",'<link rel="stylesheet" href="./fonts.css"></head>'),encoding="utf-8")
    if remotion:
        project=output/"remotion";project.mkdir(exist_ok=True)
        shutil.copytree(ROOT/"assets/remotion",project,dirs_exist_ok=True)
        for name in ("document.json","fonts.json","timeline.mjs"):shutil.copy2(output/name,project/"src"/name)
        shutil.copytree(output/"fonts",project/"public/fonts",dirs_exist_ok=True)
        css=(output/"fonts.css").read_text()
        (project/"public/fonts.css").write_text(css.replace('./fonts/','/fonts/'),encoding="utf-8")
    return output/"preview.html"

