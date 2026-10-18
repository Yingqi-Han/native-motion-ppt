#!/usr/bin/env python3
"""Sample actual event boundaries, transition midpoints and stable states in Chromium."""
import argparse,hashlib,json,math,shutil
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from native_motion.browser import browser_path
from native_motion.review import sample_times
def main():
    p=argparse.ArgumentParser();p.add_argument("--url",required=True);p.add_argument("--out",required=True);p.add_argument("--studio")
    p.add_argument("--max-samples",type=int,default=12);p.add_argument("--browser-executable",default=browser_path())
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    errors=[];records=[];shots=[];warnings=[]
    with sync_playwright() as pw:
        kwargs={"headless":True}
        if a.browser_executable:kwargs["executable_path"]=a.browser_executable
        browser=pw.chromium.launch(**kwargs);page=browser.new_page(viewport={"width":1680,"height":1100})
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(a.url,wait_until="networkidle");page.wait_for_function("window.NM?.ready");page.evaluate("NM.pause()")
        doc=page.evaluate("NM.doc");ratio=doc["canvas"]["width"]/doc["canvas"]["height"]
        page.set_viewport_size({"width":1680,"height":max(1100,round(1480/ratio)+230)})
        offset=0
        for i,s in enumerate(doc["slides"]):
            times=sample_times(s,i,a.max_samples);hashes=set()
            picks={times[0],times[len(times)//2],times[-1]}
            for t in times:
                page.evaluate("(t)=>NM.setTime(t)",offset+t)
                page.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
                target=out/f"scene-{i+1:02}-{t:05}.png";page.locator("#frame").screenshot(path=str(target))
                digest=hashlib.sha256(target.read_bytes()).hexdigest();hashes.add(digest)
                if t in picks:shots.append(target)
                state=page.evaluate("""() => {
                  const f=document.querySelector('#frame').getBoundingClientRect(),svg=document.querySelector('#frame svg');
                  const outside=[];
                  for(const text of svg.querySelectorAll('text')){
                    let alpha=1,n=text;while(n&&n!==svg.parentElement){alpha*=Number(getComputedStyle(n).opacity);n=n.parentElement;}
                    if(alpha<.98)continue;
                    const b=text.getBoundingClientRect();
                    if(b.left<f.left-2||b.top<f.top-2||b.right>f.right+2||b.bottom>f.bottom+2)
                      outside.push({text:text.textContent,object:text.closest('[data-object]')?.dataset.object});
                  }
                  const invalid=Array.from(svg.querySelectorAll('*')).some(n=>Array.from(n.attributes).some(a=>['transform','d','opacity','x','y','width','height'].includes(a.name)&&/NaN|Infinity/.test(a.value)));
                  return {svg:1,invalid_geometry:invalid,outside_text:outside,video_or_image:document.querySelectorAll('#frame video,#frame img,#frame canvas').length,aspect:f.width/f.height};
                }""")
                incoming=s["transition"]["duration"] if i else 0
                allowed={o["id"] for o in s["objects"] if o.get("allow_overflow")}
                if t>=incoming:
                    outside=[n for n in state["outside_text"] if n["object"] not in allowed]
                    if outside:errors.append(f"Scene {i+1} at {t}: text outside canvas: {outside}")
                if state["invalid_geometry"]:errors.append(f"Scene {i+1}: invalid SVG numeric geometry")
                if abs(state["aspect"]-ratio)>.01:errors.append("Preview aspect ratio mismatch")
                records.append({"scene":i+1,"time":t,"sha256":digest,**state})
            if len(hashes)==1 and any(o["animations"] for o in s["objects"]):warnings.append(f"Scene {i+1}: no visible change observed")
            offset+=s["duration"]
        if a.studio:
            page.goto(a.studio,wait_until="networkidle");page.wait_for_timeout(1000)
            page.screenshot(path=str(out/"remotion-studio.png"),full_page=True)
            if page.locator('text=NativeMotion').count()==0:errors.append("Remotion Studio composition not found")
        browser.close()
    thumb_h=round(600/ratio);row_h=thumb_h+26
    sheet=Image.new("RGB",(1800,math.ceil(len(shots)/3)*row_h),(15,18,26));draw=ImageDraw.Draw(sheet)
    for i,path in enumerate(shots):
        x=i%3*600;y=i//3*row_h;sheet.paste(Image.open(path).resize((600,thumb_h)),(x,y));draw.text((x+12,y+thumb_h+5),path.stem,fill=(165,175,195))
    sheet.save(out/"dynamic-contact.jpg",quality=93)
    report={"sampling":"adaptive event/transition boundaries","samples":records,"errors":errors,"warnings":warnings,"scope":"Shared-data reconstruction in Chromium; not a PowerPoint recording."}
    (out/"preview-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"samples":len(records),"errors":errors,"warnings":warnings},ensure_ascii=False,indent=2))
    if errors or any(r["video_or_image"] for r in records):raise SystemExit(1)
if __name__=="__main__":main()

