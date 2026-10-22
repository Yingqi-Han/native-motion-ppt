#!/usr/bin/env python3
"""One command: design video, editable PPT, real playback, checks and portable delivery."""
import argparse
import json
import os
import shutil
import shlex
import sys
import uuid
import zipfile
from datetime import datetime,timezone
from pathlib import Path

from build_demo import preview_server
from install_skill import files
from native_motion.acceptance import Ledger,playback_plan,save,sha,write_report
from native_motion.model import load
from record_desktop import toolchain

ROOT=Path(__file__).resolve().parents[1]
EXPECTED=[("source-review","源数据、排版和时序"),("preview","代码预演关键帧"),("design-video","设计视频导出"),
          ("native-structure","原生文件结构"),("static-pages","实际静态页面"),("native-import","原生动画导入"),
          ("desktop-recording","真实播放器录屏"),("native-held-pages","真实到位页面"),("native-motion","实播对象运动"),("target-player","目标播放器覆盖"),
          ("morph-playback","Morph 实际播放"),("visual-review","实际画面审阅"),("source-preserved","原稿与证据绑定")]


def read(path):return json.loads(Path(path).read_text())


def relative(root,path):return Path(path).relative_to(root).as_posix()


def package_run(root):
    """Allowlist evidence, source and previews; exclude profiles, caches and originals' locks."""
    sdk=root/"project";sdk.mkdir(exist_ok=True)
    previous=read(root/"manifest.json") if (root/"manifest.json").is_file() else {}
    for name,path in files(ROOT).items():
        target=sdk/name
        if target.resolve()==path.resolve():continue
        old=previous.get("project/"+name)
        if target.is_file() and old and sha(target)!=old["sha256"]:continue
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    for path in (root/"preview").rglob("*") if (root/"preview").is_dir() else []:
        rel=path.relative_to(root/"preview")
        if not path.is_file() or path.is_symlink() or any(p in {"node_modules",".cache","out","build"} for p in rel.parts):continue
        target=root/"editable-preview"/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    allowed=[]
    for name in ["project.json","deck.pptx","deck-auto.pptx","design-preview.mp4","player-recording.mp4",
                 "playback-evidence.json","playback-plan.json","acceptance.json","report.html","REPORT.md","README.md",'player-recording-auto.mp4','playback-evidence-auto.json']:
        if (root/name).is_file():allowed.append(root/name)
    for folder in ["project","editable-preview","data","qa","logs","regression",'plans','reviews','diagnostic','capture','implementations']:
        if (root/folder).is_dir():
            allowed.extend(p for p in (root/folder).rglob("*") if p.is_file() and not p.is_symlink()
                           and p.suffix not in {".odp"} and not any(k in {"node_modules","__pycache__","player-profile","input"} for k in p.relative_to(root).parts))
    manifest={relative(root,p):{"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(set(allowed))}
    save(root/"manifest.json",manifest)
    archive=root/"acceptance-delivery.zip";stage=root/"acceptance-delivery.writing.zip"
    with zipfile.ZipFile(stage,"w",zipfile.ZIP_DEFLATED) as zipped:
        for p in sorted(set(allowed)):zipped.write(p,relative(root,p))
        zipped.write(root/"manifest.json","manifest.json")
    os.replace(stage,archive)
    save(root/"archive.json",{"file":archive.name,"sha256":sha(archive),"bytes":archive.stat().st_size})
    return archive


def finalize_run(root,visual_note=None,review_payload=None):
    """Bind optional visual review, then verify and seal a consistent delivery."""
    from verify_acceptance import verify
    root=Path(root).resolve();ledger=Ledger.restore(root)
    def refresh_report():
        if ledger.data.get('format_version',1)>=2:
            from native_motion.diagnostics import collect_diagnostics,write_diagnostics
            write_diagnostics(root,root/'qa/diagnostics',collect_diagnostics(root))
        write_report(root,ledger.data)
    if review_payload:
        ledger.review(review_payload)
    if visual_note and ledger.data.get('format_version',1)>=2:
        ledger.review({'reviewer':'specified-by-caller','recordings':{k:v['recording_sha256'] for k,v in ledger.data.get('recordings',{}).items()},
                      'reviews':[{'check_id':'visual-review','status':'passed','note':visual_note,
                                  'evidence':['qa/manual/playback/native-contact.jpg','qa/automatic/playback/native-contact.jpg']}]})
    elif visual_note:
        proof=read(root/"playback-evidence.json")
        if proof["recording_sha256"]!=sha(root/"player-recording.mp4"):
            raise ValueError("Visual review cannot be attached to a replaced recording")
        ledger.check("visual-review","实际画面审阅","passed","qa/playback/native-contact.jpg",visual_note,required=False,
                     reviewed_recording_sha256=proof["recording_sha256"],reviewed_at=datetime.now(timezone.utc).isoformat())
    ledger.finish();refresh_report();package_run(root)
    try:
        verify(root)
        ledger.check("delivery-integrity","交付包与源码校验","passed","manifest.json","ZIP、清单校验值及独立目录的新安装检查通过")
    except Exception as error:
        ledger.check("delivery-integrity","交付包与源码校验","failed",detail=str(error))
        ledger.finish();refresh_report();package_run(root)
        raise
    ledger.finish();refresh_report();archive=package_run(root)
    verify(root)
    return archive


def execute(args):
    if getattr(args,'resume',None):
        from native_motion.desktop_workflow import execute_resume
        return execute_resume(args)
    if getattr(args,'mode','full')!='full':raise ValueError('record/check mode requires --resume')
    if not args.spec:raise ValueError('Full mode requires a source JSON')
    if not getattr(args,'out',None):raise ValueError('Full mode requires --out')
    original=Path(args.spec).resolve()
    if not original.is_file():raise ValueError("Source JSON is missing")
    output=Path(args.out).resolve()
    if output==ROOT or (ROOT in output.parents and output.relative_to(ROOT).parts[0]!="output"):
        raise ValueError("Use output/ under the skill, or a directory outside the skill")
    output.mkdir(parents=True,exist_ok=True)
    name=args.run_name or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:6]
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in name) or name in {".",".."}:
        raise ValueError("Run name must be a simple directory name")
    root=output/name;root.mkdir(exist_ok=False)
    source_sha=sha(original);source=root/"project.json";shutil.copy2(original,source)
    ledger=Ledger(root,{"original":str(original),"snapshot":"project.json","sha256":source_sha})
    args.target_player=getattr(args,'target_player',None) or 'impress-desktop'
    ledger.data.update(format_version=2,requested_target_player=args.target_player,workflow_mode='full');ledger.flush()
    py=sys.executable;doc=None;plan=None
    def command(ident,*params,timeout=600):ledger.command(ident,[py,*params],cwd=ROOT,timeout=timeout)
    def passed(ident,label,path,detail="",required=True):ledger.check(ident,label,"passed",relative(root,path),detail,required)
    try:
        doc=load(source)
        command("source-review","scripts/motion_ppt.py","review",source,"--out",root/"qa/source-review.json")
        review=read(root/"qa/source-review.json")
        ledger.check("source-review","源数据、排版和时序","pending" if review["warnings"] else "passed",
                     "qa/source-review.json",f"{review['errors']} 个错误，{review['warnings']} 个提示；包含遮挡和动作截断检查")
        command("preview-generate","scripts/motion_ppt.py","preview",source,"--out",root/"preview","--remotion")
        with preview_server(root/"preview") as url:
            command("preview-check","scripts/check_preview.py","--url",url,"--out",root/"qa/preview")
            passed("preview","代码预演关键帧",root/"qa/preview/preview-audit.json","按动作和转场采样；这是代码画面")
            if args.actor:
                command("actor-check","scripts/check_motion.py","--url",url,"--object",args.actor,"--max-step",args.max_step,"--out",root/"qa/actor")
                passed("actor-motion","主体连续运动",root/"qa/actor/motion-audit.json","代码时间线逐帧与跨页边界检查")
            if args.profile=="science":
                data=root/"data";data.mkdir(exist_ok=True)
                csv=Path(args.science_csv or ROOT/"examples/data/scientific-demo.csv").resolve()
                manifest=Path(args.science_manifest or ROOT/"examples/data/scientific-manifest.json").resolve()
                shutil.copy2(csv,data/"observations.csv");shutil.copy2(manifest,data/"figures.json")
                command("science-data","scripts/check_scientific.py","--url",url,"--csv",data/"observations.csv","--manifest",data/"figures.json","--out",root/"qa/data")
                passed("science-data","原始数据与图表坐标",root/"qa/data/scientific-audit.json","浏览器几何与输入 CSV 独立核对")
        command("design-render","scripts/render_project.py",root,"--out",root/"design-preview.mp4",timeout=1200)
        passed("design-video","设计视频导出",root/"qa/video/video-audit.json","Remotion 渲染并解码对照源画面；不是 PPT 录屏")
        if getattr(args,'install_wps',False):
            if not args.wps_root:raise ValueError('--install-wps requires --wps-root')
            if not (Path(args.wps_root)/'wps-install.json').is_file():command('wps-install','scripts/install_wps.py','--root',args.wps_root)
        if args.install_desktop:
            try:toolchain(args.desktop_tools_root)
            except ValueError:
                if not args.desktop_tools_root:raise ValueError("--install-desktop requires --desktop-tools-root")
                command("desktop-install","scripts/install_desktop_player.py","--tools-root",args.desktop_tools_root)
        office_args=[]
        if args.desktop_tools_root:
            try:toolchain(args.desktop_tools_root);office_args=["--office-tools-root",args.desktop_tools_root]
            except ValueError:pass
        command("native-build","scripts/motion_ppt.py","build",source,"--out",root/"deck.pptx")
        command("native-auto-build","scripts/motion_ppt.py","build",source,"--out",root/"deck-auto.pptx","--auto")
        command("native-check","scripts/motion_ppt.py","check",root/"deck.pptx","--out",root/"qa/native","--render","--import-check",*office_args)
        command("native-auto-check","scripts/motion_ppt.py","check",root/"deck-auto.pptx","--out",root/"qa/auto")
        passed("native-structure","原生文件结构",root/"qa/native/audit.json","对象、动画目标、媒体数量；手动与自动版分别检查")
        passed("static-pages","实际静态页面",root/"qa/native/audit.json","全部 Office 页面、可检查字形的文本框与画布边界")
        passed("native-import","原生动画导入",root/"qa/native/audit.json","实际 Impress 导入计数与时序；不等同于放映")
        from native_motion.desktop_workflow import run_desktop
        run_desktop(root,ledger,args,doc,'full')
    except Exception as error:
        ledger.data["error"]=str(error)
        if not any(c["status"]=="failed" for c in ledger.data["checks"]):ledger.check("pipeline-error","运行错误","failed",detail=str(error))
    finally:
        preserved=original.is_file() and sha(original)==source_sha and sha(source)==source_sha
        ledger.check("source-preserved","原稿与证据绑定","passed" if preserved else "failed",detail="原稿与输入副本校验值保持一致" if preserved else "原稿或快照在运行中改变")
        known={c["id"] for c in ledger.data["checks"]}
        required=[row for row in EXPECTED if row[0] not in {'desktop-recording','native-held-pages','native-motion'}]
        required +=[(prefix+'-'+mode,mode+' '+label) for mode in ['manual','automatic'] for prefix,label in [('desktop-recording','真实录屏'),('native-phases','页面阶段'),('native-motion','对象运动'),('native-held-pages','到位页面')]]
        for ident,label in required:
            if ident not in known:ledger.check(ident,label,"pending",detail="前置步骤未完成，未验证此项")
        for name,kind in [("project.json","editable_source"),("deck.pptx","native_manual_pptx"),("deck-auto.pptx","native_auto_pptx"),
                          ("design-preview.mp4","code_generated_design_preview")]:
            if (root/name).is_file():ledger.artifact(root/name,kind,is_pptx_playback_recording=(name=="player-recording.mp4"))
        ledger.finish();write_report(root,ledger.data)
        rebuild_args=["python","project/scripts/accept_project.py","project.json","--out","new-runs","--profile",args.profile,"--target-player",args.target_player]
        if args.actor:rebuild_args +=["--actor",args.actor,"--max-step",str(args.max_step)]
        if args.profile=="science":rebuild_args +=["--science-csv","data/observations.csv","--science-manifest","data/figures.json"]
        rebuild=shlex.join(rebuild_args)
        (root/"README.md").write_text("# 可编辑动态 PPT 与验收\n\n先打开 report.html 查看验收范围。\n\ndeck.pptx 为点击版，deck-auto.pptx 为自动版；design-preview.mp4 为代码预演，player-recording.mp4 为点击版真实 GUI 录屏，player-recording-auto.mp4 为自动版实录。\n\n编辑 project.json 后重新制作。Python 依赖在 project/requirements.txt，视频项目在 editable-preview/remotion，GUI 工具另装；安装完整 Noto CJK 与 Space Grotesk 字体。\n\n```bash\n"+rebuild+"\n```\n\nprofile=science 使用科学示例的 CSV/清单约定；修改数据时同步传 --science-csv 与 --science-manifest。原文件、数据与验收证据均保留校验值。\n",encoding="utf-8")
        archive=finalize_run(root)
        print(json.dumps({"run":str(root),"status":ledger.data["acceptance_status"],"report":str(root/"report.html"),"archive":str(archive)},ensure_ascii=False,indent=2),flush=True)
    return root,read(root/"acceptance.json")


def math_timeout(seconds):return max(120,int(seconds)+90)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec",nargs='?');parser.add_argument("--out");parser.add_argument("--run-name")
    parser.add_argument('--mode',choices=['full','record','check'],default='full')
    parser.add_argument('--resume',help='v1.6 run to reuse; always creates a new immutable sibling run')
    parser.add_argument('--wps-root');parser.add_argument('--wps-profile')
    parser.add_argument('--install-wps',action='store_true')
    parser.add_argument("--profile",choices=["generic","science"],default="generic")
    parser.add_argument("--science-csv");parser.add_argument("--science-manifest")
    parser.add_argument("--actor");parser.add_argument("--max-step",type=float,default=24)
    parser.add_argument("--desktop-tools-root");parser.add_argument("--target-player",choices=["impress-desktop","wps-desktop","powerpoint-desktop"],default=None)
    parser.add_argument("--install-desktop",action="store_true")
    parser.add_argument("--guard",type=float,default=2.5);parser.add_argument("--hold",type=float,default=2)
    parser.add_argument("--strict",action="store_true",help="Also return nonzero for pending required coverage")
    args=parser.parse_args()
    if args.profile=="science" and not args.actor:args.actor="sample-token"
    try:
        root,result=execute(args)
        if result["pipeline_status"]=="failed":raise SystemExit(1)
        if args.strict and result["acceptance_status"]!="passed":raise SystemExit(2)
    except (ValueError,FileNotFoundError,FileExistsError) as error:raise SystemExit(str(error))
