#!/usr/bin/env python3
"""CLI for the Native Motion PPT skill. Run --help for commands."""
import argparse,json,sys
from pathlib import Path
from native_motion.model import load
from native_motion.pptx_export import build,enhance,inventory
from native_motion.qa import audit,render,import_check
from native_motion.preview import generate
from native_motion.choreography import choreograph
from native_motion.review import review

def save(path,data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest="command",required=True)
    p=sub.add_parser("build");p.add_argument("spec");p.add_argument("--out",required=True);p.add_argument("--auto",action="store_true")
    p=sub.add_parser("preview");p.add_argument("spec");p.add_argument("--out",required=True);p.add_argument("--remotion",action="store_true")
    p=sub.add_parser("check");p.add_argument("pptx");p.add_argument("--out",required=True);p.add_argument("--allow-images",action="store_true");p.add_argument("--render",action="store_true");p.add_argument("--import-check",action="store_true")
    p.add_argument("--office-tools-root")
    p=sub.add_parser("enhance");p.add_argument("pptx");p.add_argument("--out",required=True);p.add_argument("--clicks",type=int,default=2);p.add_argument("--replace-animation",action="store_true");p.add_argument("--plan")
    p=sub.add_parser("inspect");p.add_argument("pptx");p.add_argument("--out",required=True)
    p=sub.add_parser("validate");p.add_argument("spec")
    p=sub.add_parser("review");p.add_argument("spec");p.add_argument("--out",required=True);p.add_argument("--min-hold",type=float,default=900);p.add_argument("--fail-on-warning",action="store_true")
    p=sub.add_parser("choreograph");p.add_argument("spec");p.add_argument("--out",required=True);p.add_argument("--mode",choices=["auto","click"],default="auto");p.add_argument("--fit-duration",action="store_true");p.add_argument("--min-hold",type=float,default=900)
    a=ap.parse_args()
    if a.command in ("build","preview","validate","review","choreograph"):
        doc=load(a.spec)
        if a.command=="build":
            mapping=build(doc,a.out,a.auto);save(Path(a.out).with_suffix(".manifest.json"),{"version":1,"mapping":mapping,"warnings":doc["warnings"],"spec":str(Path(a.spec).resolve())})
            print(a.out)
        elif a.command=="preview":print(generate(doc,a.out,a.remotion))
        elif a.command=="review":
            report=review(doc,a.min_hold);save(a.out,report);print(json.dumps(report,ensure_ascii=False,indent=2))
            if report["errors"] or (a.fail_on_warning and report["warnings"]):return 1
        elif a.command=="choreograph":
            timed,report=choreograph(doc,a.mode,a.fit_duration,a.min_hold);save(a.out,timed);save(Path(a.out).with_suffix(".choreography.json"),report);print(a.out)
        else:print(json.dumps({"valid":True,"warnings":doc["warnings"],"slides":len(doc["slides"])},ensure_ascii=False,indent=2))
    elif a.command=="enhance":
        if Path(a.pptx).resolve()==Path(a.out).resolve():raise ValueError("Write to a new path; preserve the original")
        plan=json.loads(Path(a.plan).read_text(encoding="utf-8")) if a.plan else None
        print(json.dumps(enhance(a.pptx,a.out,a.clicks,a.replace_animation,plan),ensure_ascii=False,indent=2))
    elif a.command=="inspect":
        save(a.out,inventory(a.pptx));print(a.out)
    else:
        out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
        report=audit(a.pptx,not a.allow_images)
        office={}
        if a.office_tools_root:
            from record_desktop import toolchain
            tools,env=toolchain(a.office_tools_root);env["SAL_USE_VCLPLUGIN"]="svp"
            office={"office_executable":tools["office"],"office_env":env}
        if a.render:
            report["static_render"]=render(a.pptx,out/"rendered",**office)
            if report["static_render"]["missing_text"] or report["static_render"]["text_outside_canvas"] or report["static_render"]["text_outside_declared_box"]:report["issues"].append("Static text verification failed")
        if a.import_check:
            report["animation_import"]=import_check(a.pptx,out/"imported",**office)
            native=report["slides"];imp=report["animation_import"]["counts"]
            for key,expected in [("animateMotion",sum(s["animMotion"] for s in native)),("animateTransform",sum(s["animRot"]+s["animScale"] for s in native)),("iterate",sum(s["iterate"] for s in native))]:
                if imp[key]!=expected:report["issues"].append(f"Impress import changed {key}: {expected} -> {imp[key]}")
            loops=sum(s["loop_effects"] for s in native)
            if report["animation_import"]["loop_effects"]!=loops:report["issues"].append("Impress import changed loop effects")
        save(out/"audit.json",report);print(json.dumps(report,ensure_ascii=False,indent=2))
        if report["issues"]:return 1
    return 0
if __name__=="__main__":
    try:sys.exit(main())
    except (ValueError,FileNotFoundError) as exc:
        print(f"Error: {exc}",file=sys.stderr);sys.exit(2)

