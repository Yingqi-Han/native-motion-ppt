#!/usr/bin/env python3
"""Compare decoded MP4 frames with the current shared-data browser renderer."""
import argparse
import hashlib
import io
import json
import math
import shutil
import subprocess
from pathlib import Path
from native_motion.browser import browser_path

from PIL import Image, ImageChops, ImageDraw, ImageStat
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--url",required=True)
    parser.add_argument("--out",required=True)
    parser.add_argument("--max-rmse",type=float,default=5)
    parser.add_argument("--browser-executable",default=browser_path())
    args=parser.parse_args()
    output=Path(args.out)
    output.mkdir(parents=True,exist_ok=True)
    video=Path(args.video).resolve()
    info=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,r_frame_rate,nb_frames","-show_entries","format=duration,size",
        "-of","json",str(video)],text=True))
    stream=info["streams"][0]
    fps_a,fps_b=map(int,stream["r_frame_rate"].split("/"))
    fps=fps_a/fps_b
    records,errors,images=[],[],[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=args.browser_executable)
        page=browser.new_page(viewport={"width":stream["width"],"height":stream["height"]})
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(args.url,wait_until="networkidle")
        page.wait_for_function("window.NM?.ready")
        doc=page.evaluate("NM.doc")
        if (stream["width"],stream["height"],fps)!=(doc["canvas"]["width"],doc["canvas"]["height"],doc["canvas"]["fps"]):
            errors.append("Video dimensions or fps differ from the source")
        duration=sum(s["duration"] for s in doc["slides"])/1000
        if abs(float(info["format"]["duration"])-duration)>1/fps:
            errors.append("Video duration differs from the source")
        page.add_style_tag(content="body{padding:0!important}header,nav,#scenes,.note{display:none!important}#frame{max-width:none!important;width:100vw!important;height:100vh!important;margin:0!important;border:0!important}")
        # Check scene seams/holds and the full progression of directional reveals.
        picks={0};offset=0
        for i,slide in enumerate(doc["slides"]):
            if i:
                edge=round(offset/1000*fps)
                picks.update({edge-1,edge,edge+1})
                picks.add(round((offset+slide["transition"]["duration"]/2)/1000*fps))
            picks.add(round((offset+slide["duration"]*.7)/1000*fps))
            for obj in slide["objects"]:
                for animation in obj["animations"]:
                    if animation.get("effect")!="wipe":
                        continue
                    click=animation.get("click",0)
                    start=offset+animation["at"]+(slide["clicks"][click-1] if click else 0)
                    for fraction in (0,.1,.25,.5,.75,.9,1):
                        picks.add(round((start+animation["duration"]*fraction)/1000*fps))
            offset+=slide["duration"]
        total_frames=round(duration*fps)
        picks={min(total_frames-1,max(0,frame)) for frame in picks}
        for frame in sorted(picks):
            page.evaluate("t=>NM.setTime(t)",frame/fps*1000)
            page.evaluate("()=>new Promise(r=>requestAnimationFrame(r))")
            source=Image.open(io.BytesIO(page.locator("#frame").screenshot())).convert("RGB")
            target=output/f"video-{frame:04}.png"
            subprocess.run(["ffmpeg","-v","error","-y","-i",str(video),"-vf",f"select=eq(n\\,{frame})",
                "-frames:v","1",str(target)],check=True)
            decoded=Image.open(target).convert("RGB")
            if decoded.size!=source.size:
                errors.append(f"Frame {frame}: browser size mismatch")
                continue
            rms=ImageStat.Stat(ImageChops.difference(source,decoded)).rms
            rmse=math.sqrt(sum(v*v for v in rms)/3)
            records.append({"frame":frame,"time_ms":frame/fps*1000,"rmse":rmse})
            if rmse>args.max_rmse:
                errors.append(f"Frame {frame}: video/source RMSE {rmse:.3f} exceeds {args.max_rmse}")
            images.append((frame,decoded.copy()))
        browser.close()
    h=round(600*stream["height"]/stream["width"])
    sheet=Image.new("RGB",(1800,math.ceil(len(images)/3)*(h+26)),"#090b12")
    draw=ImageDraw.Draw(sheet)
    for i,(frame,img) in enumerate(images):
        x,y=i%3*600,i//3*(h+26)
        sheet.paste(img.resize((600,h)),(x,y))
        draw.text((x+10,y+h+5),f"frame {frame:04} / {frame/fps:.3f}s",fill="#b0b6c5")
    sheet.save(output/"video-contact.jpg",quality=94)
    report={"video":str(video),"video_origin":"code_generated_design_preview","is_pptx_playback_recording":False,
            "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest(),"metadata":info,"frames":records,"errors":errors,
            "scope":"Decoded MP4 compared with current Chromium source at directional-reveal progress, scene seams and held frames; not native desktop playback."}
    (output/"video-audit.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({"frames":len(records),"max_rmse":max((r["rmse"] for r in records),default=0),"errors":errors},indent=2))
    if errors:
        raise SystemExit(1)


if __name__=="__main__":
    main()
