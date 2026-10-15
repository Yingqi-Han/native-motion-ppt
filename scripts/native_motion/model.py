"""Validate and normalize the shared object/timing document."""
import copy, json, math, re, subprocess
from pathlib import Path
from fontTools.ttLib import TTFont
from .fonts import resolve_font, metrics
from .geometry import parse_path, path_string

KINDS = {"text", "rect", "ellipse", "line", "polygon", "path", "group"}
EFFECTS = {"enter", "exit", "move", "rotate", "scale"}
HEX = re.compile(r"^[0-9A-Fa-f]{6}$")
IDS = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,100}$")

def number(value, label, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}: expected a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label}: must be >= {minimum}")
    return value

def font_file(family):
    try:
        r = subprocess.run(["fc-match", "-f", "%{file}", family], capture_output=True, text=True, timeout=5)
        p = Path(r.stdout.strip())
        return p if p.is_file() else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

def normalize(source):
    def finite_values(value):
        if isinstance(value,dict):
            for item in value.values():finite_values(item)
        elif isinstance(value,list):
            for item in value:finite_values(item)
        elif isinstance(value,float) and not math.isfinite(value):
            raise ValueError("All numeric fields must be finite")
    finite_values(source)
    from jsonschema import Draft202012Validator
    schema = json.loads((Path(__file__).resolve().parents[2]/"assets/spec.schema.json").read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(source), key=lambda e: str(e.absolute_path))
    if errors:
        e = errors[0]
        raise ValueError(".".join(map(str, e.absolute_path)) + ": " + e.message)
    d = copy.deepcopy(source)
    if d.get("version") != 1:
        raise ValueError("version must be 1")
    d.setdefault("title", "Native Motion")
    d.setdefault("canvas", {"width": 1920, "height": 1080, "fps": 60})
    c = d["canvas"]
    for k in ("width", "height", "fps"):
        c[k] = number(c.get(k, 60 if k == "fps" else None), "canvas." + k, 1)
        if int(c[k]) != c[k]:
            raise ValueError("canvas dimensions and fps must be integers")
    if not 1 <= c["fps"] <= 120:
        raise ValueError("fps must be between 1 and 120")
    theme = d.setdefault("theme", {})
    theme.setdefault("font", "Noto Sans CJK SC")
    theme.setdefault("latin_font", "Space Grotesk SemiBold")
    theme.setdefault("background", "090B12")
    theme.setdefault("foreground", "F1F0EB")
    theme.setdefault("accent", "4148FF")
    slides = d.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("slides must be a nonempty list")
    font_cache = {}
    warnings = []
    for si, s in enumerate(slides):
        s.setdefault("id", f"slide-{si + 1}")
        s.setdefault("duration", 3000)
        number(s["duration"], "duration", 100)
        s.setdefault("background", theme["background"])
        s.setdefault("notes", "")
        s.setdefault("clicks", [])
        last_click = -1
        for t in s["clicks"]:
            number(t, "click time", 0)
            if t <= last_click or t >= s["duration"]:
                raise ValueError("click times must increase and occur within the slide")
            last_click = t
        tr = s.setdefault("transition", {"kind": "fade", "duration": 400})
        tr.setdefault("duration", 400)
        if tr.get("kind") not in ("none", "fade", "push", "wipe", "morph"):
            raise ValueError("Unsupported transition kind")
        number(tr["duration"], "transition duration", 0)
        if tr["kind"]=="none":tr["duration"]=0
        if tr["duration"] >= s["duration"]:
            raise ValueError("transition duration must be shorter than the slide")
        tr.setdefault("direction", "l")
        if tr["direction"] not in ("l", "r", "u", "d"):
            raise ValueError("transition.direction must be l/r/u/d")
        seen = set()
        def objects(items, nested=False):
            if not isinstance(items, list):
                raise ValueError("objects must be a list")
            for o in items:
                ident = o.get("id", "")
                if not IDS.fullmatch(ident) or ident in seen:
                    raise ValueError(f"Slide {si + 1}: missing, invalid or duplicate object id {ident!r}")
                seen.add(ident)
                if o.get("kind") not in KINDS:
                    raise ValueError(f"{ident}: unsupported object kind")
                box = o.get("box")
                if not isinstance(box, list) or len(box) != 4:
                    raise ValueError(f"{ident}: box must be [x,y,width,height]")
                for v in box:
                    number(v, ident + ".box")
                if box[2] <= 0 or (box[3] < 0 if o["kind"] == "line" else box[3] <= 0):
                    raise ValueError(f"{ident}: dimensions must be positive")
                o.setdefault("fill", theme["foreground"])
                o.setdefault("opacity", 1)
                number(o["opacity"], "opacity", 0)
                if o["opacity"] > 1:
                    raise ValueError("opacity must not exceed 1")
                o.setdefault("rotation", 0)
                number(o["rotation"], "rotation")
                if o["kind"]=="text" and o["fill"]=="none":
                    raise ValueError("Text requires an RGB fill")
                if o["kind"]=="line" and o["fill"]=="none" and not o.get("stroke"):
                    raise ValueError("Line requires an RGB fill or stroke")
                for k in ("fill", "stroke"):
                    if k in o and o[k] != "none" and not HEX.fullmatch(o[k]):
                        raise ValueError(f"{ident}: {k} must be six-digit RGB or none")
                if o.get("gradient"):
                    for k in ("from", "to"):
                        if not HEX.fullmatch(o["gradient"][k]):
                            raise ValueError("Invalid gradient color")
                    number(o["gradient"].setdefault("angle", 90), "gradient angle")
                if o["kind"] == "polygon":
                    points = o.get("points", [])
                    if len(points) < 3 or any(len(p) != 2 for p in points):
                        raise ValueError("polygon needs >= 3 [x,y] points")
                    for p in points:
                        for v in p:
                            number(v, "polygon coordinate")
                if o["kind"] == "path":
                    o["commands"]=parse_path(o["d"])
                    o["d"]=path_string(o["commands"])
                if o.get("radius",0)>0 and o["kind"]!="rect":
                    raise ValueError("radius is only supported on rectangles")
                if o["kind"] == "text":
                    if not isinstance(o.get("text"), str):
                        raise ValueError("text must be a string")
                    o.setdefault("size", 64)
                    number(o["size"], "text size", 1)
                    o.setdefault("font", theme["font"])
                    o.setdefault("align", "left")
                    if o["align"] not in ("left", "center", "right"):
                        raise ValueError("text align must be left/center/right")
                    o.setdefault("spacing", 0)
                    o.setdefault("bold", False)
                    o.setdefault("line_height", 1.18)
                    if chr(92)+"n" in o["text"]:
                        warnings.append(f"Slide {si+1} {ident}: literal backslash-n found; check the intended line break")
                    key=(o["font"],o["bold"])
                    if key not in font_cache:
                        info=resolve_font(*key)
                        if not info or not info["matched"]:
                            warnings.append(f"Font {o['font']}: unavailable or substituted")
                        font_cache[key]=metrics(*key)
                    face_metrics = font_cache[key]
                    advances = []
                    for ch in o["text"]:
                        if face_metrics:
                            cmap, widths, upem = face_metrics
                            advances.append(widths.get(cmap.get(ord(ch), ".notdef"), (upem, 0))[0] / upem * o["size"])
                        else:
                            advances.append(o["size"] * (1 if ord(ch) > 255 else .6))
                    o["advances"] = advances
                    if face_metrics:
                        missing=sorted({ch for ch in o["text"] if ch.strip() and ord(ch) not in cmap})
                        if missing:warnings.append(f"Slide {si+1} {ident}: font is missing glyphs {''.join(missing)}")
                    idx=0
                    for line in o["text"].split("\n"):
                        width = sum(advances[idx:idx + len(line)]) + o["spacing"] * max(0, len(line) - 1)
                        if width > box[2] + 2:
                            warnings.append(f"Slide {si+1} {ident}: estimated text width {width:.1f} exceeds {box[2]}")
                        idx+=len(line)+1
                    if len(o["text"].split("\n")) * o["size"] * o["line_height"] > box[3] + 2:
                        warnings.append(f"Slide {si+1} {ident}: text height exceeds box")
                if o["kind"] == "group":
                    if o["opacity"] != 1 or o.get("gradient"):
                        raise ValueError("Group opacity/gradient is unsupported; style its children")
                    objects(o.get("objects", []), True)
                for e in o.setdefault("animations", []):
                    if nested:
                        raise ValueError("Child animations are not supported; animate the parent group")
                    if e.get("kind") not in EFFECTS:
                        raise ValueError("Unsupported animation")
                    e.setdefault("at", 0)
                    e.setdefault("duration", 650)
                    e.setdefault("click", 0)
                    e.setdefault("loop", False)
                    e.setdefault("ambient", False)
                    e.setdefault("auto_reverse", True)
                    e.setdefault("by_letter", False)
                    e.setdefault("letter_delay", 35)
                    e.setdefault("accel", .5 if e["loop"] else .1)
                    e.setdefault("decel", .5 if e["loop"] else .65)
                    if e.get("effect")=="wipe":
                        if e["kind"] not in ("enter","exit") or e["by_letter"]:
                            raise ValueError("wipe requires a whole-object entrance/exit")
                        e.setdefault("direction","up")
                        e.setdefault("from",[0,0]);e.setdefault("to",[0,0])
                        if e.get("path") or any(v for k in ("from","to") for v in e[k]):
                            raise ValueError("wipe must not combine with a motion offset")
                    elif "direction" in e:
                        raise ValueError("animation.direction is only used by wipe")
                    if "effect" in e and e["kind"] not in ("enter","exit"):
                        raise ValueError("animation.effect requires entrance/exit")
                    number(e["at"], "animation.at", 0)
                    number(e["duration"], "animation.duration", 1)
                    number(e["letter_delay"], "letter delay", 0)
                    if not isinstance(e["click"], int) or not 0 <= e["click"] <= len(s["clicks"]):
                        raise ValueError("click must reference a 1-based entry in slide.clicks, or be 0 for automatic")
                    if e["by_letter"] and (o["kind"] != "text" or "\n" in o["text"] or e["kind"] not in ("enter", "exit")):
                        raise ValueError("by_letter requires a single-line text entrance/exit")
                    if e["kind"] in ("enter", "exit") and e["loop"]:
                        raise ValueError("entrance/exit cannot loop")
                    if e["ambient"] and e["kind"] in ("enter", "exit"):
                        raise ValueError("entrance/exit cannot be marked as ambient")
                    if e["kind"] == "scale" and any(v<=0 for k in ("from","to") for v in e.get(k,[1,1])):
                        raise ValueError("Scale factors must be positive")
                    if e["accel"] < 0 or e["decel"] < 0 or e["accel"] + e["decel"] > 1:
                        raise ValueError("accel + decel must be <= 1")
                    for k in ("from", "to"):
                        if k in e:
                            if len(e[k]) != 2:
                                raise ValueError("from/to must be two-element arrays")
                            for v in e[k]:
                                number(v, k)
                    if e.get("path"):
                        count=len(e["path"])
                        if (count!=2 and (count<4 or (count-1)%3)) or any(len(v) != 2 for v in e["path"]):
                            raise ValueError("path requires 2 line points or 3n+1 chained cubic bezier points")
                        for pair in e["path"]:
                            for v in pair:
                                number(v, "path")
                    total = e["at"] + e["duration"] + (max(0, len(o.get("text", "")) - 1) * e["letter_delay"] if e["by_letter"] else 0)
                    start = s["clicks"][e["click"] - 1] if e["click"] else 0
                    incoming=tr["duration"] if si else 0
                    if not e["loop"] and incoming + start + total > s["duration"]:
                        warnings.append(f"Slide {si+1} {ident}: animation ends after slide duration")
        objects(s.get("objects", []))
        if not HEX.fullmatch(s["background"]):
            raise ValueError("slide background must be RGB")
    d["warnings"] = warnings
    return d

def load(path):
    return normalize(json.loads(Path(path).read_text(encoding="utf-8")))

