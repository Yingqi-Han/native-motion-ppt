#!/usr/bin/env python3
"""Measure a native actor on every preview frame, including exact scene seams."""
import argparse
import json
import math
import shutil
from pathlib import Path
from native_motion.browser import browser_path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright


MEASURE = """({time, id}) => {
  NM.setTime(time);
  const svg=document.querySelector('#frame svg');
  const actor=svg.querySelector(`[data-object="${CSS.escape(id)}"]`);
  if(!actor) return null;
  const box=actor.getBBox();
  const matrix=svg.getCTM().inverse().multiply(actor.getCTM());
  const center=new DOMPoint(box.x+box.width/2,box.y+box.height/2).matrixTransform(matrix);
  const corners=[[box.x,box.y],[box.x+box.width,box.y],[box.x+box.width,box.y+box.height],[box.x,box.y+box.height]]
    .map(([x,y])=>new DOMPoint(x,y).matrixTransform(matrix));
  return {time,center:[center.x,center.y],
    width:Math.max(...corners.map(p=>p.x))-Math.min(...corners.map(p=>p.x)),
    height:Math.max(...corners.map(p=>p.y))-Math.min(...corners.map(p=>p.y)),
    transform:actor.getAttribute('transform')};
}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--object", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-step", type=float, default=8,
                        help="Maximum center movement in design pixels per frame")
    parser.add_argument("--browser-executable", default=browser_path())
    args = parser.parse_args()
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    errors, records, boundaries, shots = [], [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=args.browser_executable)
        page = browser.new_page(viewport={"width":1680, "height":1100})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_function("window.NM?.ready")
        page.evaluate("NM.pause()")
        doc = page.evaluate("NM.doc")
        fps = doc["canvas"]["fps"]
        step = 1000 / fps
        offset = 0
        previous_present = False
        for index, slide in enumerate(doc["slides"]):
            present = any(o["id"] == args.object for o in slide["objects"])
            if present:
                for frame in range(math.ceil(slide["duration"] / step)):
                    t = offset + frame * step
                    if t >= offset + slide["duration"]:
                        break
                    record = page.evaluate(MEASURE, {"time": t, "id": args.object})
                    if record:
                        record["scene"] = index + 1
                        records.append(record)
                if previous_present:
                    a = page.evaluate(MEASURE, {"time":offset-.001, "id":args.object})
                    b = page.evaluate(MEASURE, {"time":offset, "id":args.object})
                    if a and b:
                        delta = math.dist(a["center"], b["center"])
                        size_delta = max(abs(a[k]-b[k]) for k in ("width", "height"))
                        boundaries.append({"time":offset, "center_jump_px":delta,
                                           "size_jump_px":size_delta})
                        if delta > .01 or size_delta > .01:
                            errors.append(f"Scene {index+1}: pose reset at boundary")
                incoming = slide["transition"]["duration"] if index else 0
                picks = sorted({0, round(incoming/2), incoming,
                                round(slide["duration"]*.25), round(slide["duration"]*.5),
                                round(slide["duration"]*.75), slide["duration"]-1})
                for t in picks:
                    page.evaluate("t=>NM.setTime(t)", offset+t)
                    page.evaluate("()=>new Promise(r=>requestAnimationFrame(r))")
                    path = output / f"actor-{index+1:02}-{t:05}.png"
                    page.locator("#frame").screenshot(path=str(path))
                    shots.append(path)
            previous_present = present
            offset += slide["duration"]
        browser.close()
    if not records:
        errors.append("Actor was not found")
    if any(not all(math.isfinite(v) for v in r["center"]+[r["width"],r["height"]]) for r in records):
        errors.append("Non-finite actor geometry")
    pairs = [(a,b) for a,b in zip(records,records[1:]) if b["time"]-a["time"] < step*1.01]
    maximum = max((math.dist(a["center"],b["center"]) for a,b in pairs),default=0)
    size_step = max((max(abs(a[k]-b[k]) for k in ("width","height")) for a,b in pairs),default=0)
    if maximum > args.max_step:
        errors.append(f"Actor center moved {maximum:.3f}px in one frame")
    aspect = doc["canvas"]["width"] / doc["canvas"]["height"]
    thumb_height = round(600/aspect)
    sheet = Image.new("RGB", (1800, math.ceil(len(shots)/3)*(thumb_height+28)), "#090b12")
    draw = ImageDraw.Draw(sheet)
    for i,path in enumerate(shots):
        x,y = i%3*600, i//3*(thumb_height+28)
        sheet.paste(Image.open(path).convert("RGB").resize((600,thumb_height)),(x,y))
        draw.text((x+10,y+thumb_height+6),path.stem,fill="#b0b6c5")
    if shots:
        sheet.save(output/"motion-contact.jpg",quality=94)
    report = {"actor":args.object,"fps":fps,"frames":len(records),
              "max_center_step_px":maximum,"max_size_step_px":size_step,
              "boundaries":boundaries,"errors":errors,"samples":records,
              "scope":"Every scheduled browser frame; exact pose seams. Native PPT is checked separately."}
    (output/"motion-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!="samples"},ensure_ascii=False,indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
