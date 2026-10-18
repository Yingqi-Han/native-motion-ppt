#!/usr/bin/env python3
"""Observe automatic/manual page phases and native Morph contours from a real recording."""
import argparse,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
from check_native_motion import probe,decode,frame_at
from native_motion.acceptance import save,sha
from native_motion.model import load
from native_motion.phases import classify_pages,morph_candidates,contour,analyse_morph


def check(args):
    video=Path(args.video).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    evidence=json.loads(Path(args.evidence).read_text());doc=load(args.spec)
    if evidence.get('origin')!='native_desktop_screen_capture' or evidence.get('is_pptx_playback_recording') is not True:raise ValueError('Only actual desktop capture is accepted')
    if evidence['recording_sha256']!=sha(video) or evidence['source_pptx_sha256']!=sha(args.pptx):raise ValueError('Stale video/PPTX evidence')
    if args.mode=='automatic' and [a['key'] for a in evidence['actions']]!=['F5']:raise ValueError('Automatic playback must contain only F5, no advance keys')
    plan=json.loads(Path(args.plan).read_text()) if args.plan else None
    if args.mode=='manual' and plan is None:raise ValueError('Manual mode requires the actual input plan')
    meta,times=probe(video);stream=meta['streams'][0]
    show_keys=[a.get('at_wall_seconds') for a in evidence['actions'] if a['key']=='F5']
    if len(show_keys)!=1 or isinstance(show_keys[0],bool) or not isinstance(show_keys[0],(float,int)) or not math.isfinite(show_keys[0]) or not 0<=show_keys[0]<times[-1]:raise ValueError('Capture evidence requires one valid actual F5 wall-clock timestamp')
    show_key=float(show_keys[0])
    if (stream['width'],stream['height'])!=(doc['canvas']['width'],doc['canvas']['height']):raise ValueError('Capture/source dimensions differ')
    refs=[np.array(Image.open(Path(args.references)/f'slide-{i+1:02}.png').convert('RGB').resize((320,180)).filter(ImageFilter.GaussianBlur(1.2))) for i in range(len(doc['slides']))]
    frames=[]
    for _,_,p in decode(video,'scale=320:180:flags=area',(320,180),range(len(times)),times):frames.append(np.array(Image.fromarray(p).filter(ImageFilter.GaussianBlur(1.2))))
    pages,starts,activity,events=classify_pages(times,frames,refs,plan if args.mode=='manual' else None,show_key if args.mode=='automatic' else None)
    trustworthy=all(p['status']=='passed' for p in pages) and all(t is not None for t in starts)
    end=times[-1]-.05
    observed={'origin':'measurement_of_actual_desktop_recording','mode':args.mode,'show_after':1,'seconds':float(meta['format']['duration']),
              'click_at':plan['click_at'] if plan else [],'pages':[], 'observed_landmarks':sorted(set(t for e in events for t in [e['start'],e['end']]))}
    if trustworthy:
        for i,p in enumerate(pages):
            row=dict(plan['pages'][i]) if plan else {'slide':i+1,'click_at_seconds':[],'bar_objects':[],'looping_objects':[]}
            row.update(page_input_seconds=starts[i],next_page_seconds=starts[i+1] if i+1<len(starts) else end,
                       held_probe_seconds=p['held_timestamp'],content_base_seconds=starts[i],bar_start_seconds=starts[i],bar_end_seconds=(starts[i+1] if i+1<len(starts) else end)-.2)
            observed['pages'].append(row)
    candidates,uncovered=morph_candidates(doc);morphs=[];full_frames={}
    def held(i):
        if i not in full_frames:full_frames[i]=np.array(frame_at(video,pages[i]['held_frame_index'],out/f'held-{i+1:02}.png'))
        return full_frames[i]
    if trustworthy:
        for c in candidates:
            i=c['slide']-1;first=contour(held(i-1)[c['roi'][1]:c['roi'][3],c['roi'][0]:c['roi'][2]],c,c['source_boxes'][0])
            last=contour(held(i)[c['roi'][1]:c['roi'][3],c['roi'][0]:c['roi'][2]],c,c['source_boxes'][1])
            start=max(0,starts[i]-.2);finish=min(pages[i]['held_timestamp'],starts[i]+doc['slides'][i]['transition']['duration']/1000+2.0)
            ids=[j for j,t in enumerate(times) if start<=t<=finish];records=[]
            x0,y0,x1,y1=c['roi'];f=f'select=between(n\\,{ids[0]}\\,{ids[-1]}),crop={x1-x0}:{y1-y0}:{x0}:{y0}:exact=1'
            seed=[(first[0]+first[2])/2,(first[1]+first[3])/2] if first else None
            for j,t,p in decode(video,f,(x1-x0,y1-y0),ids,times,end=finish):
                box=contour(p,c,seed=seed);records.append({'frame_index':j,'timestamp':t,'box':box})
                if box:seed=[(box[0]+box[2])/2,(box[1]+box[3])/2]
            r={**c,**analyse_morph(records,first,last),'records':records};morphs.append(r)
        for p in observed['pages']:
            incoming=[m for m in morphs if m['slide']==p['slide']]
            if incoming and all(m['status']=='passed' for m in incoming):
                p['object_motion_starts']={m['object']:m['settled_seconds'] for m in incoming}
                p['phase_basis']='measured_incoming_morph_arrival_plateau'
    for m in morphs:
        if m.get('observed_transition_seconds'):
            a,b=m['observed_transition_seconds'];observed['observed_landmarks'] +=[a+(b-a)*f for f in [0,.25,.5,.75,1]]
    observed['observed_landmarks']=sorted(set(observed['observed_landmarks']))
    bindings={'recording_sha256':sha(video),'source_pptx_sha256':sha(args.pptx),'source_json_sha256':sha(args.spec),
              'playback_evidence_sha256':sha(args.evidence),'actual_show_key_seconds':show_key,
              'planned_input_sha256':sha(args.plan) if args.plan else None}
    observed.update(bindings)
    states=[p['status'] for p in pages]+[m['status'] for m in morphs]+[u['status'] for u in uncovered]
    status='failed' if 'failed' in states else 'pending' if 'pending' in states or not trustworthy else 'passed'
    report={'format_version':2,'origin':'measurement_of_actual_desktop_recording','status':status,'mode':args.mode,**bindings,
            'pages':pages,'page_starts':starts,'activity_intervals':events,'morphs':morphs,'uncovered_morphs':uncovered,
            'capture_frames':len(times),'plan_status':'passed' if trustworthy else 'pending',
            'scope':'Full-page independent references and actual activity identify pages. PPT boxes/colors bound contour search, not motion evaluation. Only supported isolated contours are certified; ambiguous/occluded/text Morph stays pending.'}
    save(out/'phase-audit.json',report)
    save(out/'observed-playback-plan.json',observed)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('video');p.add_argument('--pptx',required=True);p.add_argument('--evidence',required=True)
    p.add_argument('--spec',required=True);p.add_argument('--references',required=True);p.add_argument('--plan');p.add_argument('--mode',choices=['manual','automatic'],required=True);p.add_argument('--out',required=True)
    r=check(p.parse_args());print(json.dumps({k:v for k,v in r.items() if k not in ['morphs','activity_intervals']},ensure_ascii=False,indent=2))
    if r['status']=='failed':raise SystemExit(1)
