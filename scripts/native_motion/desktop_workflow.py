"""Shared full/record/check workflow: dual capture, phase audit, evidence and immutable reruns."""
import copy,json,shutil,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
from .acceptance import playback_plan,save,sha,Ledger
from .players import preflight,recording_command,player_matches,PLAYERS
from .model import load

ROOT=Path(__file__).resolve().parents[2]
MODES={'manual':('deck.pptx','player-recording.mp4','playback-evidence.json'),
       'automatic':('deck-auto.pptx','player-recording-auto.mp4','playback-evidence-auto.json')}


def read(p):return json.loads(Path(p).read_text())


def plans(doc,guard=2.5,hold=2):
    automatic={'mode':'automatic','show_after':1,'click_at':[],
               'seconds':1+sum(s['duration']+s['transition']['duration'] for s in doc['slides'])/1000+max(hold,2)+2,
               'scope':'Capture allowance only. Real pixels establish page timings; no advance keys.'}
    manual=playback_plan(doc,guard,hold);manual['mode']='manual'
    return {'manual':manual,'automatic':automatic}


def inspect_recordings(root,target):
    recordings={}
    for mode,(deck,video,proof) in MODES.items():
        evidence=read(root/proof)
        if not player_matches(target,evidence):raise ValueError('Actual recording backend differs from requested target: '+mode)
        if evidence['recording_sha256']!=sha(root/video) or evidence['source_pptx_sha256']!=sha(root/deck):raise ValueError('Recording/PPTX changed: '+mode)
        if evidence.get('opened_copy_sha256')!=evidence['source_pptx_sha256']:raise ValueError('Opened playback copy differs')
        if mode=='automatic' and [a['key'] for a in evidence['actions']]!=['F5']:raise ValueError('Automatic recording contains advance keys')
        recordings[mode]={'video':video,'pptx':deck,'evidence':proof,'player':evidence['player'],
                          'recording_sha256':evidence['recording_sha256'],'source_pptx_sha256':evidence['source_pptx_sha256']}
    return recordings


def run_desktop(root,ledger,args,doc,mode='full'):
    root=Path(root);target=args.target_player;py=sys.executable
    def command(ident,*params,timeout=600):ledger.command(ident,[py,*params],cwd=ROOT,timeout=timeout)
    def check(ident,label,status,path=None,detail='',required=True):ledger.check(ident,label,status,path,detail,required)
    ledger.data.update(format_version=2,workflow_mode=mode,requested_target_player=target)
    from .motion_advice import advise
    save(root/'qa/motion-advice.json',advise(doc))
    ledger.check('motion-advice','源几何编排建议（非实播结论）','passed','qa/motion-advice.json','Advice generated without editing source; playback and narration remain independent',required=False)
    if mode!='check':
        report=preflight(target,args.desktop_tools_root,getattr(args,'wps_root',None),getattr(args,'wps_profile',None),doc)
        save(root/'qa/desktop-preflight.json',report)
        check('desktop-preflight','目标播放器依赖与字体',report['status'],'qa/desktop-preflight.json','; '.join(report['issues']) or 'Required player, tools and fonts are ready; real GUI still checked through recording')
        if report['status']!='passed':
            for name in MODES:check('desktop-recording-'+name,name+' 真实录屏','pending',detail='Target backend unavailable; no substitute player used')
            check('target-player','目标播放器覆盖','pending',detail='Required backend not ready; no fallback')
            check('morph-playback','Morph 实际播放','pending',detail='No target recording')
            check('visual-review','实际画面审阅','pending',detail='No target frames to review')
            return
        input_plans=plans(doc,args.guard,args.hold)
        for name,plan in input_plans.items():save(root/'plans'/(name+'-input.json'),plan)
        shutil.copy2(root/'plans/manual-input.json',root/'playback-plan.json')
        # Capture every required file serially before CPU-heavy analysis.
        for name,(deck,video,proof) in MODES.items():
            out=root/'capture'/name
            params=recording_command(target,root/deck,out,input_plans[name],doc['canvas'],args.desktop_tools_root,getattr(args,'wps_root',None),getattr(args,'wps_profile',None))
            command('record-'+name,*params,timeout=max(120,int(input_plans[name]['seconds'])+90))
            shutil.copy2(out/'player-recording.mp4',root/video);shutil.copy2(out/'playback-evidence.json',root/proof)
        if target=='wps-desktop' and any(s['transition']['kind']=='morph' for s in doc['slides']):
            diagnostic=read(ROOT/'examples/wps-morph-diagnostic.json')
            save(root/'diagnostic/project.json',diagnostic)
            command('morph-probe-build','scripts/motion_ppt.py','build',root/'diagnostic/project.json','--out',root/'diagnostic/deck.pptx')
            probe_plan={'show_after':1,'seconds':9,'click_at':[4]};save(root/'diagnostic/input-plan.json',probe_plan)
            params=recording_command(target,root/'diagnostic/deck.pptx',root/'diagnostic/capture',probe_plan,diagnostic['canvas'],args.desktop_tools_root,args.wps_root,args.wps_profile)
            command('record-morph-probe',*params,timeout=120)
    recordings=inspect_recordings(root,target);ledger.data['recordings']=recordings;ledger.data['actual_player']=PLAYERS[target];ledger.flush()
    check('target-player','目标播放器覆盖','passed',recordings['manual']['evidence'],f'Both manual and automatic captures prove actual {PLAYERS[target]}; package/GUI scope remains explicit')
    morph_states=[]
    for name,(deck,video,proof) in MODES.items():
        check('desktop-recording-'+name,name+' 真实录屏','passed',proof,read(root/proof)['version'])
        phase_out=root/'qa'/name/'phases';phase_params=['scripts/check_playback_phases.py',root/video,'--pptx',root/deck,'--evidence',root/proof,
            '--spec',root/'project.json','--references',root/'qa/native/rendered','--mode',name,'--out',phase_out]
        if name=='manual':phase_params+=['--plan',root/'plans/manual-input.json']
        command('phases-'+name,*phase_params)
        phase=read(phase_out/'phase-audit.json')
        check('native-phases-'+name,name+' 页面与运动阶段',phase['status'],str((phase_out/'phase-audit.json').relative_to(root)),
              'Pages observed by independent reference matching; Morph arrival measured from source-bounded contours')
        morph_states +=[m['status'] for m in phase['morphs']]+[u['status'] for u in phase['uncovered_morphs']]
        if phase['plan_status']!='passed':
            for ident,label in [('native-motion','对象运动'),('native-held-pages','到位画面')]:check(ident+'-'+name,name+' '+label,'pending',detail='Page identity/phase evidence insufficient')
            continue
        observed=phase_out/'observed-playback-plan.json';motion_out=root/'qa'/name/'motion'
        command('motion-'+name,'scripts/check_native_motion.py',root/video,'--pptx',root/deck,'--evidence',root/proof,'--spec',root/'project.json',
                '--plan',observed,'--references',root/'qa/native/rendered','--out',motion_out,'--max-step',args.max_step,'--phases',phase_out/'phase-audit.json')
        measured=read(motion_out/'native-motion-playback-audit.json')
        from .phase_timeline import timeline
        events=timeline(phase,measured);events.update(phase_audit_sha256=sha(phase_out/'phase-audit.json'),motion_audit_sha256=sha(motion_out/'native-motion-playback-audit.json'))
        save(root/'qa'/name/'observed-phases.json',events)
        check('native-motion-'+name,name+' 实播对象运动',measured['status'],str((motion_out/'native-motion-playback-audit.json').relative_to(root)),
              f"Measured {measured['frames_decoded_for_activity']} actual frames, {len(measured['objects'])} objects; raw scans and phase-separated results retained")
        out=root/'qa'/name/'playback'
        command('frames-'+name,'scripts/check_native_playback.py',root/video,'--pptx',root/deck,'--evidence',root/proof,
                '--plan',motion_out/'observed-playback-plan.json','--references',root/'qa/native/rendered','--out',out)
        held=read(out/'native-playback-audit.json');state='pending' if any(p['status']=='pending' for p in held['held_pages']) else 'passed'
        check('native-held-pages-'+name,name+' 真实到位页面',state,str((out/'native-playback-audit.json').relative_to(root)),f"{len(held['held_pages'])} actual held pages compared with Office references")
    has_morph=any(s['transition']['kind']=='morph' for s in doc['slides'])
    if has_morph and target=='wps-desktop' and (root/'diagnostic/capture/playback-evidence.json').is_file():
        command('morph-probe-check','scripts/check_native_morph.py',root/'diagnostic/capture/player-recording.mp4','--pptx',root/'diagnostic/deck.pptx',
                '--evidence',root/'diagnostic/capture/playback-evidence.json','--start',3,'--end',7,'--out',root/'diagnostic/morph-audit.json')
        probe=read(root/'diagnostic/morph-audit.json');morph_states.append(probe['status'])
    elif has_morph:morph_states.append('pending')
    state='failed' if 'failed' in morph_states else 'pending' if 'pending' in morph_states else 'passed'
    check('morph-playback','Morph 实际播放',state,'diagnostic/morph-audit.json' if (root/'diagnostic/morph-audit.json').is_file() else None,
          'Isolated no-object-animation probe AND all supported main-deck transitions measured' if has_morph else 'No Morph in this project')
    check('automatic-advance','自动动作与翻页',read(root/'qa/automatic/phases/phase-audit.json')['plan_status'],'qa/automatic/phases/phase-audit.json',
          'Only F5 was sent; all page identities must be observed in order')
    command('review-frames','scripts/extract_review_frames.py',root)
    check('visual-review','实际画面与讲解质量审阅','pending',detail='Review both current recordings and actual frames; attach structured SHA-bound review. Machine checks do not prove aesthetics.')
    for name,(deck,video,proof) in MODES.items():
        ledger.artifact(root/video,'native_desktop_screen_capture',is_pptx_playback_recording=True,mode=name)
        ledger.artifact(root/proof,'native_playback_evidence',mode=name)


def execute_resume(args):
    from accept_project import finalize_run
    from verify_acceptance import verify
    parent=Path(args.resume).resolve();old=read(parent/'acceptance.json')
    if old.get('format_version',1)<2:raise ValueError('Fast reruns require a v1.6.0 run with dependency/recording bindings')
    verify(parent)
    target=args.target_player or old['requested_target_player']
    if args.mode=='check' and target!=old['requested_target_player']:raise ValueError('Check-only cannot change the recorded backend')
    args.target_player=target
    original=parent/old['source']['snapshot'];doc=load(original)
    if args.spec and sha(args.spec)!=sha(original):raise ValueError('Changed source requires a full run; old PPTs/recordings cannot certify it')
    output=Path(args.out).resolve() if args.out else parent.parent;output.mkdir(parents=True,exist_ok=True)
    name=args.run_name or parent.name+'-'+args.mode+'-'+uuid.uuid4().hex[:6];root=output/name
    if Path(name).name!=name or name in {'.','..'}:raise ValueError('Unsafe run name')
    root.mkdir(exist_ok=False)
    ledger=Ledger(root,{'original':str(original),'snapshot':'project.json','sha256':sha(original)})
    ledger.data.update(format_version=2,workflow_mode=args.mode,requested_target_player=target,lineage={'parent_acceptance_sha256':sha(parent/'acceptance.json'),'parent_manifest_sha256':sha(parent/'manifest.json'),'mode':args.mode,'copied':[]})
    manifest=read(parent/'manifest.json')
    selected=[]
    for name in manifest:
        if name in {'project.json','deck.pptx','deck-auto.pptx','design-preview.mp4','playback-plan.json'} or name.startswith(('plans/','data/','qa/native/','qa/auto/','qa/preview/','qa/source-review','qa/video/','qa/actor/','qa/data/')):selected.append(name)
        if args.mode=='check' and (name in {'player-recording.mp4','player-recording-auto.mp4','playback-evidence.json','playback-evidence-auto.json'} or name.startswith(('diagnostic/','qa/desktop-preflight','capture/manual/','capture/automatic/'))):selected.append(name)
    try:
        for name in sorted(set(selected)):
            src=parent/name;dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
            ledger.data['lineage']['copied'].append({'path':name,'sha256':sha(src),'bytes':src.stat().st_size})
        reusable={'source-review','preview','actor-motion','science-data','design-video','native-structure','static-pages','native-import'}
        for c in old['checks']:
            if c['id'] in reusable:
                if c['status']=='failed':raise ValueError('Reusable source/native prerequisite failed: '+c['id'])
                ledger.check(c['id'],c['label'],c.get('automatic_status',c['status']),c.get('evidence'),c['detail'],c['required'],reused_from_parent=True)
        if args.mode=='check':
            c=next((c for c in old['checks'] if c['id']=='desktop-preflight'),None)
            if c:ledger.check(c['id'],c['label'],c.get('automatic_status',c['status']),c.get('evidence'),'Reused installation snapshot; check-only launches no player',c['required'])
        ledger.flush();run_desktop(root,ledger,args,doc,args.mode)
    except Exception as exc:ledger.check('pipeline-error','运行错误','failed',detail=str(exc))
    finally:
        ledger.check('source-preserved','输入与依赖绑定','passed' if sha(original)==old['source']['sha256'] and sha(root/'project.json')==old['source']['sha256'] else 'failed',detail='Immutable new run; selected dependency SHA-256 recorded in lineage')
        for name,kind in [('project.json','editable_source'),('deck.pptx','native_manual_pptx'),('deck-auto.pptx','native_auto_pptx'),('design-preview.mp4','code_generated_design_preview')]:
            if (root/name).is_file():ledger.artifact(root/name,kind,is_pptx_playback_recording=False)
        finalize_run(root)
    return root,read(root/'acceptance.json')
