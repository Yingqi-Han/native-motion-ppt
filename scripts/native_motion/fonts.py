"""Resolve actual font faces and coverage; preserve all families used by the project."""
import json,subprocess
from functools import lru_cache
from pathlib import Path
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parents[2]
@lru_cache(maxsize=64)
def resolve_font(family,bold=False):
    query=family+(":style=Bold" if bold else "")
    try:
        r=subprocess.run(["fc-match","-f","%{file}\n%{family}\n%{style}\n%{index}",query],capture_output=True,text=True,timeout=5)
        ls=r.stdout.splitlines();file=Path(ls[0])
        if file.is_file():
            resolved=ls[1];matched=family.casefold() in [f.strip().casefold() for f in resolved.split(",")]
            return {"path":str(file),"family":resolved,"style":ls[2],"index":int(ls[3])%65536,"matched":matched}
    except (FileNotFoundError,subprocess.TimeoutExpired,IndexError,ValueError):pass
    packaged=ROOT/"assets/fonts/SpaceGrotesk-SemiBold.ttf"
    if family=="Space Grotesk SemiBold" and packaged.exists():
        return {"path":str(packaged),"family":family,"style":"SemiBold","index":0,"matched":True}
    return None
@lru_cache(maxsize=64)
def metrics(family,bold=False):
    info=resolve_font(family,bold)
    if not info:return None
    with TTFont(info["path"],fontNumber=info["index"]) as f:
        return f.getBestCmap(),f["hmtx"].metrics,f["head"].unitsPerEm
def text_objects(items):
    for o in items:
        if o["kind"]=="text":yield o
        elif o["kind"]=="group":yield from text_objects(o["objects"])

@lru_cache(maxsize=32)
def ink_face(family,bold=False):
    info=resolve_font(family,bold)
    if not info or not info["matched"]:return None
    font=TTFont(info["path"],fontNumber=info["index"])
    return font,font.getBestCmap(),font.getGlyphSet(),font["head"].unitsPerEm,font["name"].getDebugName(6)

@lru_cache(maxsize=4096)
def glyph_ink(family,bold,char):
    from fontTools.pens.boundsPen import BoundsPen
    face=ink_face(family,bold)
    if not face or ord(char) not in face[1]:return None
    pen=BoundsPen(face[2]);face[2][face[1][ord(char)]].draw(pen)
    return pen.bounds,face[3],face[4]
def bundle_fonts(doc,output):
    from fontTools import subset
    output=Path(output);(output/"fonts").mkdir(exist_ok=True,parents=True)
    requests={}
    for s in doc["slides"]:
        for o in text_objects(s["objects"]):
            key=(o["font"],o["bold"]);requests.setdefault(key,set()).update(o["text"])
    css=[];manifest=[];notes=[]
    for i,((family,bold),chars) in enumerate(sorted(requests.items()),1):
        info=resolve_font(family,bold)
        if not info:
            notes.append({"font":family,"bold":bold,"status":"unavailable"});continue
        f=TTFont(info["path"],fontNumber=info["index"])
        options=subset.Options();options.layout_features=["*"];options.recommended_glyphs=True
        options.name_IDs=["*"];options.name_legacy=True;options.name_languages=["*"]
        sub=subset.Subsetter(options=options);sub.populate(text="".join(sorted(chars)));sub.subset(f)
        suffix=".otf" if "CFF " in f else ".ttf";filename=f"face-{i:02}{suffix}"
        f.save(output/"fonts"/filename);f.close()
        weight="700" if bold else "400"
        css.append('@font-face{font-family:'+json.dumps(family)+';src:url("./fonts/'+filename+'");font-weight:'+weight+';}')
        manifest.append({"family":family,"file":"fonts/"+filename,"weight":weight})
        notes.append({"font":family,"bold":bold,"resolved":info["family"],"matched":info["matched"],"file":filename})
    (output/"fonts.css").write_text("\n".join(css),encoding="utf-8")
    (output/"font-audit.json").write_text(json.dumps(notes,ensure_ascii=False,indent=2),encoding="utf-8")
    return manifest

