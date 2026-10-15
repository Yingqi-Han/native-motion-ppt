#!/usr/bin/env python3
"""Extract real desktop landmarks and compare held pages with actual Office renders."""
import argparse
import hashlib
import json
import math
import subprocess
from bisect import bisect_left
from pathlib import Path

from PIL import Image,ImageChops,ImageDraw,ImageFilter,ImageStat


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare_frame(actual,expected):
    a=actual.convert("RGB").resize((320,180)).filter(ImageFilter.GaussianBlur(1.2))
    b=expected.convert("RGB").resize((320,180)).filter(ImageFilter.GaussianBlur(1.2))
    difference=ImageChops.difference(a,b)
    rmse=lambda image:math.sqrt(sum(v*v for v in ImageStat.Stat(image).rms)/3)
    tiles=[]
    for y in range(0,180,36):
        for x in range(0,320,40):
            tiles.append({"box":[x,y,x+40,y+36],"rmse":rmse(difference.crop((x,y,x+40,y+36)))})
    return {"rmse":rmse(difference),"max_tile_rmse":max(t["rmse"] for t in tiles),
            "worst_tile":max(tiles,key=lambda t:t["rmse"])}


def check(args):
    video=Path(args.video).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    evidence=json.loads(Path(args.evidence).read_text());plan=json.loads(Path(args.plan).read_text())
    if evidence.get("origin")!="native_desktop_screen_capture" or evidence.get("is_pptx_playback_recording") is not True:
        raise ValueError("Only actual desktop screen capture is accepted")
    if evidence["recording_sha256"]!=sha(video) or evidence["source_pptx_sha256"]!=sha(args.pptx):
        raise ValueError("Source PPTX or recording changed after capture")
    if plan.get("origin")=="measurement_of_actual_desktop_recording" and (
        plan.get("recording_sha256")!=sha(video) or plan.get("source_pptx_sha256")!=sha(args.pptx)):
        raise ValueError("Observed playback landmarks belong to another recording")
    meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,avg_frame_rate,nb_frames","-show_entries","format=duration","-of","json",str(video)],text=True))
    frames=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","frame=best_effort_timestamp_time","-of","json",str(video)],text=True))["frames"]
    timestamps=[float(f["best_effort_timestamp_time"]) for f in frames]
    requested={.2}
    requested.update(plan.get("observed_landmarks",[]))
    for page in plan["pages"]:
        start=page["page_input_seconds"];base=page["content_base_seconds"]
        requested.update([start+.15,(start+base)/2,base,page["held_probe_seconds"],page["next_page_seconds"]-.25])
        for click in page["click_at_seconds"]:requested.update([click-.1,click+.15,click+.7,click+1.35])
    mapping={}
    for t in sorted(requested):
        i=min(bisect_left(timestamps,t),len(timestamps)-1)
        mapping[t]=i
    indices=sorted(set(mapping.values()))
    select="+".join(f"eq(n\\,{i})" for i in indices)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),"-vf","select="+select,
                    "-fps_mode","passthrough",str(out/"native-%04d.png")],check=True)
    extracted={index:out/f"native-{number:04}.png" for number,index in enumerate(indices,1)}
    references=[Image.open(Path(args.references)/f"slide-{p['slide']:02}.png").convert("RGB") for p in plan["pages"]]
    records=[];errors=[]
    for page,reference in zip(plan["pages"],references):
        index=mapping[page["held_probe_seconds"]];actual=Image.open(extracted[index]).convert("RGB")
        scores=[compare_frame(actual,r) for r in references];measured=scores[page["slide"]-1]
        best=min(range(len(scores)),key=lambda i:scores[i]["rmse"])+1
        if page["looping_objects"]:
            state="pending";reason="Looping objects have no static held pose; inspect native frames"
        else:
            state="passed" if measured["rmse"]<=args.max_rmse and measured["max_tile_rmse"]<=args.max_tile_rmse else "failed"
            reason="Held full-page layout compared at 320×180 with blur; small glyph identity is outside this check"
        row={"slide":page["slide"],"status":state,"reason":reason,"requested_time":page["held_probe_seconds"],
             "actual_timestamp":timestamps[index],"frame_index":index,"image":extracted[index].name,
             "best_reference_slide":best,**measured}
        records.append(row)
        if state=="failed":errors.append({"slide":page["slide"],"time":timestamps[index],"message":"Held native layout differs from Office reference",**measured})
    n=len(indices);height=338;sheet=Image.new("RGB",(1800,math.ceil(n/3)*(height+27)),"#102326");draw=ImageDraw.Draw(sheet)
    samples=[]
    for order,index in enumerate(indices):
        path=extracted[index];x,y=order%3*600,order//3*(height+27)
        sheet.paste(Image.open(path).convert("RGB").resize((600,height)),(x,y))
        draw.text((x+10,y+height+5),f"native frame {index} / {timestamps[index]:.3f}s",fill="#d4ded5")
        samples.append({"frame_index":index,"actual_timestamp":timestamps[index],"image":path.name})
    sheet.save(out/"native-contact.jpg",quality=94)
    report={"origin":"measurement_of_actual_desktop_recording","recording_sha256":sha(video),
            "source_pptx_sha256":sha(args.pptx),"video_metadata":meta,"held_pages":records,"samples":samples,
            "thresholds":{"global_rmse":args.max_rmse,"tile_rmse":args.max_tile_rmse},"errors":errors,
            "scope":"Actual capture timestamps and pixels. Held page resemblance and observed landmarks; not an OCR, fine-glyph, aesthetic or Morph-motion certification"}
    (out/"native-playback-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"native_frames":len(samples),"held_pages":records,"errors":errors},ensure_ascii=False,indent=2))
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video");parser.add_argument("--pptx",required=True);parser.add_argument("--evidence",required=True)
    parser.add_argument("--plan",required=True);parser.add_argument("--references",required=True);parser.add_argument("--out",required=True)
    parser.add_argument("--max-rmse",type=float,default=8);parser.add_argument("--max-tile-rmse",type=float,default=18)
    result=check(parser.parse_args())
    if result["errors"]:raise SystemExit(1)
