"""Run evidence, conservative playback plans and portable acceptance reports."""
import hashlib
import html
import json
import math
import os
import signal
import subprocess
import time
import zipfile
from datetime import datetime,timezone
from pathlib import Path

from .review import effect_times

STATES={"passed","failed","pending"}
LABELS={"passed":"通过","failed":"失败","pending":"待检查"}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    stage=path.with_name(path.name+".writing")
    stage.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(stage,path)


def implementation_snapshot(root):
    """Preserve the code/assets used by a stage, even while improving the checker."""
    source=Path(__file__).resolve().parents[2]
    paths=sorted([*source.joinpath('scripts').rglob('*.py'),*(p for p in source.joinpath('assets').rglob('*') if p.is_file())])
    blobs={p.relative_to(source).as_posix():p.read_bytes() for p in paths if not p.is_symlink() and '__pycache__' not in p.parts and 'node_modules' not in p.parts}
    manifest={n:hashlib.sha256(b).hexdigest() for n,b in blobs.items()}
    digest=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    dest=Path(root)/'implementations'/(digest+'.zip');dest.parent.mkdir(exist_ok=True)
    if not dest.exists():
        with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
            for name,blob in blobs.items():z.writestr(name,blob)
            z.writestr('implementation-manifest.json',json.dumps(manifest,sort_keys=True))
    return {'sha256':digest,'snapshot':dest.relative_to(root).as_posix()}


def playback_plan(doc,guard=2.5,hold=2.0):
    """Schedule manual clicks with transition/startup allowance and explicit held probes."""
    if not math.isfinite(guard) or not math.isfinite(hold) or guard<2 or hold<1:
        raise ValueError("Playback guard >=2s and reading hold >=1s are required")
    show_after=1.0;cursor=show_after;clicks=[];pages=[]
    for index,slide in enumerate(doc["slides"]):
        base=cursor+guard
        local_clicks=[base+t/1000 for t in slide["clicks"]]
        clicks.extend(local_clicks)
        end=max((effect_times(e,slide,o)[1]/1000 for o in slide["objects"]
                 for e in o["animations"] if not e["loop"]),default=0)
        probe=base+max(end,1)+hold
        next_page=max(cursor+guard+slide["duration"]/1000,probe+1)
        bars=[o["id"] for o in slide["objects"] if o.get("role")=="data" and o["kind"]=="rect"
              and o["fill"]!="none" and not o.get("gradient") and not o["rotation"] and o["opacity"]==1
              and any(e["kind"]=="enter" and e.get("effect")=="wipe"
              and e.get("direction")=="up" for e in o["animations"])]
        pages.append({"slide":index+1,"page_input_seconds":cursor,"content_base_seconds":base,
                      "click_at_seconds":local_clicks,"held_probe_seconds":probe,
                      "next_page_seconds":next_page,"bar_objects":bars,
                      "bar_start_seconds":base-.2,"bar_end_seconds":probe+.25,
                      "looping_objects":[o["id"] for o in slide["objects"] if any(e["loop"] for e in o["animations"])]})
        if index+1<len(doc["slides"]):clicks.append(next_page)
        cursor=next_page
    return {"show_after":show_after,"seconds":cursor+1,"click_at":clicks,"pages":pages,
            "scope":"Manual playback with reading/transition allowance; actual frames must confirm each page"}


class Ledger:
    def __init__(self,root,source):
        self.root=Path(root)
        self.data={"format_version":1,"started_at":datetime.now(timezone.utc).isoformat(),
                   "pipeline_status":"running","source":source,"checks":[],"stages":[],"artifacts":[],
                   "scope":"Code design, native file, actual desktop playback and target-player coverage are independent"}
        self.flush()

    @classmethod
    def restore(cls,root):
        ledger=cls.__new__(cls);ledger.root=Path(root)
        ledger.data=json.loads((ledger.root/"acceptance.json").read_text())
        return ledger

    def flush(self):save(self.root/"acceptance.json",self.data)

    def check(self,ident,label,state,evidence=None,detail="",required=True,**extra):
        if state not in STATES:raise ValueError("Unknown acceptance state")
        row={"id":ident,"label":label,"status":state,"automatic_status":state,"reviewed_status":None,"review_only":ident=='visual-review',"required":required,"detail":detail,**extra}
        if evidence:row["evidence"]=evidence
        self.data["checks"]=[c for c in self.data["checks"] if c["id"]!=ident]+[row]
        self.flush();return row

    def review(self,payload):
        """Attach an immutable review bound to all real recordings and machine evidence."""
        expected={name:info['recording_sha256'] for name,info in self.data.get('recordings',{}).items()}
        if payload.get('recordings')!=expected or not expected:raise ValueError('Review must bind every current recording SHA-256')
        for name,info in self.data['recordings'].items():
            if sha(self.root/info['video'])!=expected[name]:raise ValueError('Review cannot attach to a replaced recording')
        rows={c['id']:c for c in self.data['checks']}
        prepared=[]
        for item in payload.get('reviews',[]):
            row=rows.get(item.get('check_id'))
            if not row:raise ValueError('Unknown review check')
            if row['id']=='target-player' or row['id'].startswith('target-player-'):raise ValueError('Reviews cannot certify a different player')
            if row.get('automatic_status',row['status'])=='failed' and item.get('status')=='passed':raise ValueError('Fix and retest a failed automatic check; a review cannot override it')
            if item.get('status') not in STATES or not str(item.get('note','')).strip():raise ValueError('Review requires a status and concrete note')
            evidence=[]
            for name in item.get('evidence',[]):
                path=self.root/name
                if not path.resolve().is_relative_to(self.root.resolve()) or path.is_symlink() or not path.is_file():raise ValueError('Review evidence must be a regular file inside this run')
                evidence.append({'path':name,'sha256':sha(path)})
            if not evidence:raise ValueError('Review requires actual frame/measurement evidence')
            record={'check_id':row['id'],'automatic_status':row.get('automatic_status',row['status']),'reviewed_status':item['status'],
                    'note':item['note'],'recordings':expected,'evidence':evidence,'reviewer':payload.get('reviewer','unspecified'),
                    'machine_evidence_sha256':sha(self.root/row['evidence']) if row.get('evidence') else None,
                    'reviewed_at':datetime.now(timezone.utc).isoformat()}
            prepared.append((row,record))
        if not prepared:raise ValueError('No review items')
        for row,record in prepared:
            ident=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()
            path=Path('reviews')/(ident+'.json');save(self.root/path,record)
            row.update(reviewed_status=record['reviewed_status'],status=record['reviewed_status'],review=path.as_posix(),review_note=record['note'])
        self.flush()

    def command(self,ident,command,cwd=None,timeout=600):
        started=time.monotonic();log=self.root/"logs"/(ident+".log");log.parent.mkdir(exist_ok=True)
        stage={"id":ident,"command":[str(x) for x in command],"started_at":datetime.now(timezone.utc).isoformat(),
               "status":"running","log":log.relative_to(self.root).as_posix()}
        stage['implementation']=implementation_snapshot(self.root)
        self.data["stages"].append(stage);self.flush()
        print(f"[{ident}] running",flush=True)
        try:
            with log.open("w") as output:
                process=subprocess.Popen([str(x) for x in command],cwd=cwd,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                try:code=process.wait(timeout=timeout)
                except BaseException:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
                    raise
            stage["returncode"]=code
            if code:raise RuntimeError(f"Stage {ident} exited {code}; see {stage['log']}")
            stage["status"]="passed"
        except BaseException as exc:
            stage["status"]="failed";stage["error"]=str(exc) or type(exc).__name__
            self.check(ident,ident,"failed",stage["log"],stage["error"])
            raise
        finally:
            stage["elapsed_seconds"]=round(time.monotonic()-started,3);self.flush()
        print(f"[{ident}] passed",flush=True)

    def artifact(self,path,kind,**extra):
        path=Path(path)
        self.data["artifacts"].append({"path":path.relative_to(self.root).as_posix(),"kind":kind,
                                       "sha256":sha(path),"bytes":path.stat().st_size,**extra})
        self.flush()

    def finish(self):
        checks=self.data["checks"]
        failed=any(c["status"]=="failed" for c in checks) or any(s["status"]!="passed" for s in self.data["stages"])
        pending=any(c["status"]=="pending" and c["required"] for c in checks)
        self.data["pipeline_status"]="failed" if failed else "completed"
        self.data["acceptance_status"]="failed" if failed else "pending" if pending else "passed"
        auto_failed=any(c.get('automatic_status',c['status'])=='failed' for c in checks) or any(s['status']!='passed' for s in self.data['stages'])
        auto_pending=any(c.get('automatic_status',c['status'])=='pending' and c['required'] and not c.get('review_only',False) for c in checks)
        self.data['automatic_acceptance_status']='failed' if auto_failed else 'pending' if auto_pending else 'passed'
        self.data["finished_at"]=datetime.now(timezone.utc).isoformat();self.flush()


def write_report(root,data):
    root=Path(root);esc=lambda v:html.escape(str(v))
    rows=[];markdown=["# 制作与验收报告","",f"最终验收：{LABELS[data.get('acceptance_status','pending')]}",
                       f"自动检查：{LABELS[data.get('automatic_acceptance_status',data.get('acceptance_status','pending'))]}",
                       f"运行状态：{data['pipeline_status']}","", "| 检查 | 自动 | 审阅 | 最终 | 说明 |","| --- | --- | --- | --- | --- |"]
    for check in data["checks"]:
        state=check["status"];evidence=check.get("evidence")
        link=f'<a href="{esc(evidence)}">检查记录</a>' if evidence else ""
        automatic=check.get('automatic_status',state);reviewed=check.get('reviewed_status');review_link=f'<a href="{esc(check["review"])}">审阅依据</a>' if check.get('review') else ''
        rows.append(f'<tr><td>{esc(check["label"])}</td><td>{LABELS[automatic]}</td><td>{LABELS[reviewed] if reviewed else "未审阅"} {review_link}</td><td><span class="state {state}">{LABELS[state]}</span></td><td>{esc(check["detail"])} {link}</td></tr>')
        markdown.append(f"| {check['label']} | {LABELS[automatic]} | {LABELS[reviewed] if reviewed else '未审阅'} | {LABELS[state]} | {check['detail'].replace('|','／').replace(chr(10),' ')} |")
    files="".join(f'<a class="file" href="{esc(a["path"])}">{esc(a["path"])} <small>{a["bytes"]:,} B</small></a>' for a in data["artifacts"])
    videos=[]
    for name,label,caption in [("design-preview.mp4","代码设计预演","Remotion 渲染；用于核对设计与节奏"),
                               ("player-recording.mp4","点击版真实放映",data.get('actual_player','真实桌面播放器')+'；手动节奏可长于设计视频'),
                               ("player-recording-auto.mp4","自动版真实放映",data.get('actual_player','真实桌面播放器')+'；仅 F5 后自行播放')]:
        if (root/name).is_file():
            poster=""
            if name=="design-preview.mp4" and (root/"preview/document.json").is_file():
                doc=json.loads((root/"preview/document.json").read_text())
                frame=round(doc["slides"][0]["duration"]*.7/1000*doc["canvas"]["fps"])
                candidate=f"qa/video/video-{frame:04}.png"
                if (root/candidate).is_file():poster=f' poster="{candidate}"'
            elif (root/"qa/playback/native-playback-audit.json").is_file():
                native=json.loads((root/"qa/playback/native-playback-audit.json").read_text())
                if native["held_pages"]:
                    candidate="qa/playback/"+native["held_pages"][0]["image"]
                    if (root/candidate).is_file():poster=f' poster="{esc(candidate)}"'
            videos.append(f'<div><h3>{label}</h3><video controls preload="metadata" src="{name}"{poster}></video><p>{caption}</p></div>')
    sheets=[]
    for name,label in [("qa/native/rendered/contact.jpg","实际静态页面"),("qa/playback/native-contact.jpg","实际放映关键帧"),("qa/manual/playback/native-contact.jpg","点击版实际关键帧"),("qa/automatic/playback/native-contact.jpg","自动版实际关键帧"),("qa/visual-review/manual/contact.jpg","点击版停留与 Morph 四分位实帧"),("qa/visual-review/automatic/contact.jpg","自动版停留与 Morph 四分位实帧")]:
        if (root/name).is_file():sheets.append(f'<details><summary>{label}</summary><img src="{name}" alt="{label}"></details>')
    motion=''
    motion_path=root/"qa/motion/native-motion-playback-audit.json"
    if motion_path.is_file():
        measured=json.loads(motion_path.read_text())
        motion=f'<h2>实际运动过程</h2><p>扫描 {measured["frames_decoded_for_activity"]} 帧，追踪 {len(measured["objects"])} 个对象。<a href="qa/motion/motion-report.html">打开运动曲线与录像联动检查</a></p>'
    if (root/"regression/regression-check.json").is_file():
        motion+='<p>检测器回归：<a href="regression/fault/qa/motion/motion-report.html">故意含跳动的实播样本</a> · <a href="regression/fixed/qa/motion/motion-report.html">修复后的实播对照</a>。两份样本用于检查检测器，不计入本项目的播放结果。</p>'
    for mode,label in [('manual','点击版'),('automatic','自动版')]:
        path=root/'qa'/mode/'motion/native-motion-playback-audit.json'
        if path.is_file():motion+=f'<p>{label}：<a href="qa/{mode}/motion/motion-report.html">对象曲线与录像</a> · <a href="qa/{mode}/phases/phase-audit.json">实际阶段与 Morph</a> · <a href="qa/{mode}/observed-phases.json">入场／页内运动／停留时间线</a></p>'
    if (root/'qa/diagnostics/diagnostics.html').is_file():
        motion+='<h2>问题与复验建议</h2><p><a href="qa/diagnostics/diagnostics.html">查看失败、待检原因与实际片段定位</a>。解释报告保留原始状态；没有测得的时间不生成异常定位。</p>'
        markdown +=['','[问题、待检原因与复验建议](qa/diagnostics/diagnostics.html)']
    source=esc(data["source"]["sha256"][:16]);status=data.get("acceptance_status","pending");auto_status=data.get('automatic_acceptance_status',status)
    counts={key:sum(c["status"]==key for c in data["checks"]) for key in STATES}
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>制作与验收</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f4f2ea;color:#112b2c;font:15px/1.65 system-ui,"Noto Sans CJK SC",sans-serif}main{max-width:1180px;margin:auto;padding:50px 28px}header{border-bottom:1px solid #ccd3c9;padding-bottom:26px;margin-bottom:32px}.eyebrow{font-size:12px;letter-spacing:2px;color:#637775}h1{font-size:40px;line-height:1.2;letter-spacing:-1px;margin:18px 0}h2{font-size:23px;margin:36px 0 16px}h3{font-size:17px;margin:0 0 12px}p{color:#536965}.state{display:inline-block;padding:3px 12px;border-radius:3px;font-size:13px;white-space:nowrap}.passed{background:#dae8df;color:#005c50}.failed{background:#f0d7ce;color:#9a3a21}.pending{background:#eee5cc;color:#7d601d}.media{display:grid;grid-template-columns:1fr 1fr;gap:22px}.media video{width:100%;aspect-ratio:16/9;background:#102326}table{width:100%;border-collapse:collapse}th{text-align:left;font-weight:500;color:#647774}td,th{padding:15px 10px;border-bottom:1px solid #d7ddd3;vertical-align:top}td:first-child{width:25%}td:nth-child(2){width:12%}a{color:#00766a;text-underline-offset:3px}.files{display:grid;grid-template-columns:1fr 1fr;gap:10px}.file{padding:14px;background:#eaece3;text-decoration:none;overflow-wrap:anywhere}.file small{display:block;color:#667c75}details{margin:12px 0;border-top:1px solid #ccd3c9;padding:16px 0}summary{cursor:pointer}img{width:100%;height:auto;margin-top:15px}footer{margin-top:35px;font-size:12px;color:#657b73}@media(max-width:700px){main{padding:28px 16px}.media,.files{grid-template-columns:1fr}h1{font-size:30px}td,th{padding:10px 5px}}
    </style><main>'''
    page+=f'<header><div class="eyebrow">NATIVE MOTION / ACCEPTANCE</div><h1>制作与验收</h1><span class="state {status}">最终：{LABELS[status]}</span> <span class="state {auto_status}">自动检查：{LABELS[auto_status]}</span>　{counts["passed"]} 项通过 · {counts["pending"]} 项待检查 · {counts["failed"]} 项失败<p>同一份源数据，分别检查设计、原生文件与真实放映。输入校验值：{source}</p></header>'
    page+='<section class="media">'+"".join(videos)+'</section>'+motion+'<h2>验收结果</h2><div style="overflow:auto"><table><thead><tr><th>检查</th><th>自动</th><th>审阅</th><th>最终</th><th>依据与范围</th></tr></thead><tbody>'+"".join(rows)+'</tbody></table></div><h2>关键帧</h2>'+"".join(sheets)+'<h2>可编辑文件与证据</h2><div class="files">'+files+'</div><footer>采集帧率不等于播放器重绘率。其他播放器的放映证据不能代替目标 WPS / PowerPoint。细小字形与审美仍需查看原图。</footer></main></html>'
    (root/"report.html").write_text(page,encoding="utf-8")
    markdown +=["","代码预演、实际静态页面、真实录屏和目标播放器验证分别记载。","",
                 "可编辑工程与运行结果见 acceptance-delivery.zip。"]
    (root/"REPORT.md").write_text("\n".join(markdown)+"\n",encoding="utf-8")
