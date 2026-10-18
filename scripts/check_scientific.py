#!/usr/bin/env python3
"""Measure chart semantics in Chromium against the editable source observations."""
import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
from pathlib import Path
from native_motion.browser import browser_path

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
POSITION="""({id,time})=>{
 NM.setTime(time);
 const svg=document.querySelector('#frame svg'),o=svg.querySelector(`[data-object="${CSS.escape(id)}"]`);
 if(!o)return null;
 const b=o.getBBox(),m=svg.getCTM().inverse().multiply(o.getCTM());
 const center=new DOMPoint(b.x+b.width/2,b.y+b.height/2).matrixTransform(m);
 const corners=[[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]]
  .map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
 const clip=o.querySelector('[data-wipe-clip]');
 return {center:[center.x,center.y],bottom:Math.max(...corners.map(p=>p.y)),
   matrix:[m.a,m.b,m.c,m.d,m.e,m.f],clip:clip?['x','y','width','height'].map(k=>Number(clip.getAttribute(k))):null};
}"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",required=True)
    parser.add_argument("--out",required=True)
    parser.add_argument("--manifest",default=str(ROOT/"examples/data/scientific-manifest.json"))
    parser.add_argument("--csv",default=str(ROOT/"examples/data/scientific-demo.csv"))
    args=parser.parse_args()
    source=Path(args.csv)
    manifest=json.loads(Path(args.manifest).read_text())
    errors=[];records=[]
    if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest["source_sha256"]:
        errors.append("Figure metadata is stale relative to its data source")
    data=list(csv.DictReader(source.open(encoding="utf-8")))
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=browser_path())
        page=browser.new_page(viewport={"width":1680,"height":1100})
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(args.url,wait_until="networkidle");page.wait_for_function("window.NM?.ready")
        doc=page.evaluate("NM.doc");fps=doc["canvas"]["fps"]
        offsets=[];offset=0
        for slide in doc["slides"]:
            offsets.append(offset);offset+=slide["duration"]
        maximum_baseline_error=0;baseline_frames=0
        for figure in manifest["figures"]:
            index=figure["slide"]-1;slide=doc["slides"][index]
            if figure["kind"]=="positive-bar":
                for frame in range(math.ceil(slide["duration"]/1000*fps)):
                    t=offsets[index]+frame/fps*1000
                    for bar in figure["bars"]:
                        state=page.evaluate(POSITION,{"id":bar["id"],"time":t})
                        if state is None:
                            errors.append("Missing native bar: "+bar["id"]);continue
                        error=abs(state["bottom"]-bar["baseline"])
                        maximum_baseline_error=max(maximum_baseline_error,error)
                        if figure.get("geometry_stays_static"):
                            if any(abs(a-b)>.0001 for a,b in zip(state["matrix"],[1,0,0,1,0,0])):
                                errors.append("A static-geometry data bar has a transform")
                            clip=state["clip"]
                            if clip and abs(clip[1]+clip[3]-bar["box"][3])>.02:
                                errors.append("Bottom wipe clip does not meet the fixed baseline")
                        baseline_frames+=1
                if maximum_baseline_error>.02:errors.append("Bar reveal moved the shared zero baseline")
            if figure.get("axes_stay_static"):
                axes=[o for o in slide["objects"] if any(key in o["id"] for key in ("-grid-","-tick-","-baseline","-unit","-category-"))]
                if any(o["animations"] for o in axes):errors.append(f"Scene {index+1}: data axes animate")
            time=offsets[index]+slide["duration"]-1
            if figure["kind"]=="sampled-line":
                raw=[r for r in data if r["kind"]=="line" and r["series"]==figure["data_series"]]
                x,y,w,h=figure["box"];low,high=figure["domain"]
                for i,row in enumerate(raw):
                    expected=[x+(float(row["x"])-figure["x"][0])/(figure["x"][-1]-figure["x"][0])*w,
                              y+h-(float(row["value"])-low)/(high-low)*h]
                    actual=page.evaluate(POSITION,{"id":f"{figure['prefix']}-point-{i}","time":time})
                    if not actual or math.dist(actual["center"],expected)>.02:errors.append("Line sample plotted at the wrong coordinate")
                    records.append({"kind":"line-sample","index":i,"value":float(row["value"]),"expected":expected,"actual":actual})
            if figure["kind"]=="observations-iqr-median":
                x,y,w,h=figure["box"];low,high=figure["domain"]
                for i,stat in enumerate(figure["statistics"]):
                    values=[float(r["value"]) for r in data if r["kind"]=="dot" and r["series"]==stat["label"]]
                    median=statistics.median(values);q1,_,q3=statistics.quantiles(values,n=4,method="inclusive")
                    if (median,q1,q3)!=(stat["median"],stat["q1"],stat["q3"]):errors.append("Distribution statistics differ from source observations")
                    actual=page.evaluate(POSITION,{"id":f"{figure['prefix']}-median-{i}","time":time})
                    yy=y+h-(median-low)/(high-low)*h
                    if not actual or abs(actual["center"][1]-yy)>.02:errors.append("Median marker plotted at the wrong height")
                    records.append({"kind":"distribution-summary","label":stat["label"],"median":median,"q1":q1,"q3":q3,"actual":actual})
                    for j,value in enumerate(values):
                        actual=page.evaluate(POSITION,{"id":f"{figure['prefix']}-observation-{i}-{j}","time":time})
                        if not actual or abs(actual["center"][1]-(y+h-(value-low)/(high-low)*h))>.02:
                            errors.append("Observation plotted at the wrong height")
        browser.close()
    report={"source_sha256":manifest["source_sha256"],"baseline_measurements":baseline_frames,
            "max_baseline_error_px":maximum_baseline_error,"records":records,"errors":errors,
            "scope":"Actual Chromium geometry compared with source CSV; native timing checked separately."}
    output=Path(args.out);output.mkdir(parents=True,exist_ok=True)
    (output/"scientific-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!="records"},indent=2))
    if errors:raise SystemExit(1)


if __name__=="__main__":main()
