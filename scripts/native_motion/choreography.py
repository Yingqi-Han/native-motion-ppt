"""Compile semantic roles into restrained native reveals, preserving authored actions."""
import copy
from .model import normalize
def choreograph(source,mode="auto",fit_duration=False,min_hold=900):
    if mode not in ("auto","click") or min_hold<0:raise ValueError("Invalid choreography mode or hold")
    d=copy.deepcopy(source);records=[];previous={}
    for si,s in enumerate(d["slides"]):
        s.setdefault("duration",3000);s.setdefault("clicks",[])
        groups={};title_end=800
        for o in s["objects"]:
            if o.get("animations"):continue
            role=o.get("role","decoration")
            if role in ("title","visual","caption"):
                if s.get("transition",{}).get("kind")=="morph" and o["id"] in previous and previous[o["id"]]["kind"]==o["kind"]:continue
                at={"title":100,"visual":0,"caption":550}[role]
                duration={"title":680,"visual":780,"caption":420}[role]
                o["animations"]=[{"kind":"enter","at":at,"duration":duration,"from":[0,48 if role=="title" else 22]}]
                records.append({"slide":si+1,"object":o["id"],"role":role,"click":0,"at":at,"reason":"Reveal the visual hierarchy"})
            elif role in ("body","data"):
                groups.setdefault(o.get("reveal_group",1),[]).append(o)
        for gi,(group,items) in enumerate(sorted(groups.items())):
            at=900+gi*700;click=0
            if mode=="click":
                at=max(at,s["clicks"][-1]+700 if s["clicks"] else 0)
                s["clicks"].append(at);click=len(s["clicks"]);at=0
            for j,o in enumerate(items):
                o["animations"]=[{"kind":"enter","at":at+j*100,"duration":480,"click":click,"from":[0,22]}]
                records.append({"slide":si+1,"object":o["id"],"role":o["role"],"click":click,"at":at+j*100,"semantic_group":group})
        incoming=s.get("transition",{}).get("duration",400) if si and s.get("transition",{}).get("kind","fade")!="none" else 0
        ends=[]
        for o in s["objects"]:
            for e in o.get("animations",[]):
                if not e.get("loop"):
                    start=s["clicks"][e.get("click",0)-1] if e.get("click",0) else 0
                    letters=max(0,len(o.get("text",""))-1)*e.get("letter_delay",35) if e.get("by_letter") else 0
                    ends.append(start+e.get("at",0)+e.get("duration",650)+letters+incoming)
        if fit_duration:s["duration"]=max(s["duration"],max(ends,default=0)+min_hold)
        previous={o["id"]:o for o in s["objects"]}
    return normalize(d),{"mode":mode,"generated":records,"preserved_existing_animations":True,"min_hold":min_hold}

