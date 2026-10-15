"""Actionable layout/timing diagnostics. Heuristics are reported as heuristics."""
import math
def contrast(fg,bg):
    def lum(c):
        v=[int(c[i:i+2],16)/255 for i in (0,2,4)]
        v=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in v]
        return .2126*v[0]+.7152*v[1]+.0722*v[2]
    a,b=lum(fg),lum(bg);return (max(a,b)+.05)/(min(a,b)+.05)
def blend(fg,bg,alpha):
    return "".join(f"{round(int(fg[i:i+2],16)*alpha+int(bg[i:i+2],16)*(1-alpha)):02X}" for i in (0,2,4))
def effect_times(effect,slide,obj):
    start=(slide["clicks"][effect["click"]-1] if effect["click"] else 0)+effect["at"]
    extra=max(0,len(obj.get("text",""))-1)*effect["letter_delay"] if effect["by_letter"] else 0
    return start,start+effect["duration"]+extra
def review(doc,min_hold=900):
    issues=[];records=[];width,height=doc["canvas"]["width"],doc["canvas"]["height"]
    def add(level,code,si,ident,message,**extra):
        issues.append({"level":level,"code":code,"slide":si+1,"object":ident,"message":message,**extra})
    for si,s in enumerate(doc["slides"]):
        incoming=s["transition"]["duration"] if si else 0;latest=0;last_motion=0;texts=[];fonts=[]
        for o in s["objects"]:
            x,y,w,h=o["box"]
            if not o.get("allow_overflow") and (x<-.5 or y<-.5 or x+w>width+.5 or y+h>height+.5):
                add("error" if o["kind"]=="text" else "warning","outside-canvas",si,o["id"],"Declared object box is outside the canvas",box=o["box"])
            if o["kind"]=="text" and o["opacity"]>0:
                texts.append(o);fonts.append(o["font"])
                threshold=3 if o["size"]>=48 else 4.5
                foreground=blend(o["fill"],s["background"],o["opacity"])
                ratio=contrast(foreground,s["background"])
                if ratio<threshold:add("warning","text-contrast",si,o["id"],"Text may be difficult to read on the declared slide background",ratio=round(ratio,2),threshold=threshold)
                if o["size"]<20*height/1080:
                    add("warning","small-text",si,o["id"],"Small text should be checked at actual viewing size",size=o["size"])
            intervals=[]
            for e in o["animations"]:
                a,b=effect_times(e,s,o)
                if not e["loop"]:
                    last_motion=max(last_motion,b)
                    ambient=e["ambient"]
                    if not ambient:latest=max(latest,b)
                    if incoming+b>s["duration"]:
                        add("error","animation-cut-off",si,o["id"],"Animation cannot finish before the next scene",end_ms=incoming+b,duration=s["duration"])
                property="opacity" if e["kind"] in ("enter","exit") else e["kind"]
                for pa,pb,pkey in intervals:
                    if pkey==property and max(a,pa)<min(b,pb):
                        add("warning","overlapping-effects",si,o["id"],"Two effects write the same property at the same time",property=property)
                intervals.append((a,b,property))
            if o.get("role")=="data" and any(e["kind"]=="scale" for e in o["animations"]):
                offsets=[e for e in o["animations"] if e["kind"] in ("enter","move") and any(v for p in e.get("path",[e.get("from",[0,0]),e.get("to",[0,0])]) for v in p)]
                if offsets:add("warning","data-transform-sync",si,o["id"],"Coupled data scaling and translation depend on player synchronization; prefer a static-geometry wipe")
        for i,a in enumerate(texts):
            if a.get("allow_overlap"):continue
            for b in texts[i+1:]:
                if b.get("allow_overlap"):continue
                ax,ay,aw,ah=a["box"];bx,by,bw,bh=b["box"]
                overlap=max(0,min(ax+aw,bx+bw)-max(ax,bx))*max(0,min(ay+ah,by+bh)-max(ay,by))
                if overlap>min(aw*ah,bw*bh)*.08:
                    add("warning","text-box-overlap",si,a["id"],"Text boxes overlap; inspect the actual glyphs",other=b["id"],area=round(overlap))
        hold=s["duration"]-incoming-latest
        if hold<min_hold:add("warning","short-hold",si,None,"Too little time remains after finite animations",hold_ms=hold,minimum_ms=min_hold)
        if si and s["transition"]["kind"]=="morph":
            previous={o["id"]:o for o in doc["slides"][si-1]["objects"]}
            shared=[o["id"] for o in s["objects"] if o["id"] in previous and o["kind"]==previous[o["id"]]["kind"] and o.get("role") not in ("label","decoration") and (o["kind"]!="text" or o.get("role") in ("title","body","data","visual"))]
            if not shared:add("warning","morph-no-subject",si,None,"Morph has no identifiable shared subject")
        records.append({"slide":si+1,"last_content_animation_ms":incoming+latest,"last_finite_animation_ms":incoming+last_motion,"hold_ms":hold,"fonts":sorted(set(fonts))})
    for warning in doc["warnings"]:issues.append({"level":"warning","code":"model-warning","message":warning})
    return {"errors":sum(i["level"]=="error" for i in issues),"warnings":sum(i["level"]=="warning" for i in issues),
            "issues":issues,"slides":records,"scope":"Source geometry, declared background contrast and scheduled timeline heuristics. Inspect actual rendering before accepting the design."}

def sample_times(slide,index,max_samples=12):
    if max_samples<6:raise ValueError("max_samples must be >= 6")
    duration=slide["duration"];incoming=slide["transition"]["duration"] if index else 0
    mandatory={0,max(0,duration-1)}
    if incoming:mandatory.update({round(incoming/2),round(incoming),min(duration-1,round(incoming+80))})
    events=[]
    for o in slide["objects"]:
        for e in o["animations"]:
            start,end=effect_times(e,slide,o)
            events.extend([incoming+start,incoming+(start+end)/2,incoming+end+1])
    candidates=sorted({round(t) for t in events if 0<=t<duration}-mandatory)
    room=max_samples-len(mandatory)
    if len(candidates)>room:
        indices={round(i*(len(candidates)-1)/max(1,room-1)) for i in range(room)}
        candidates=[candidates[i] for i in sorted(indices)]
    return sorted(mandatory|set(candidates))

