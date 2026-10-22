#!/usr/bin/env python3
"""Extract held pages and measured Morph quarter-points from the current real recordings."""
import argparse,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from check_native_motion import probe
from native_motion.acceptance import sha,save


def review_indices(phases,held,times,show_key):
    indices={p['frame_index'] for p in (held or {}).get('held_pages',[])}
    for page in phases.get('pages',[]):
        if page.get('held_frame_index') is not None:indices.add(page['held_frame_index'])
    for m in phases.get('morphs',[]):
        if not m.get('observed_transition_seconds'):continue
        a,b=m['observed_transition_seconds']
        for fraction in [0,.25,.5,.75,1]:
            t=a+(b-a)*fraction;indices.add(min(range(len(times)),key=lambda i:abs(times[i]-t)))
    basis='measured_phase_or_held_probes'
    if not indices:
        basis='context_only_not_page_identity'
        start=min(times[-1],show_key+.6)
        for fraction in [0,.25,.5,.75,1]:
            t=start+(times[-1]-start)*fraction;indices.add(min(range(len(times)),key=lambda i:abs(times[i]-t)))
    if any(type(i) is not int or not 0<=i<len(times) for i in indices):raise ValueError('Review probe lies outside actual recording')
    return sorted(indices),basis


def extract(root):
    root=Path(root).resolve();data=json.loads((root/'acceptance.json').read_text());reports={}
    for mode,recording in data['recordings'].items():
        video=root/recording['video']
        if sha(video)!=recording['recording_sha256']:raise ValueError('Current recording changed')
        phases=json.loads((root/'qa'/mode/'phases/phase-audit.json').read_text())
        if phases['recording_sha256']!=recording['recording_sha256']:raise ValueError('Review phases belong to another recording')
        path=root/'qa'/mode/'playback/native-playback-audit.json'
        held=json.loads(path.read_text()) if path.is_file() else None
        if held and held['recording_sha256']!=recording['recording_sha256']:raise ValueError('Held probes belong to another recording')
        proof=json.loads((root/recording['evidence']).read_text());keys=[a['at_wall_seconds'] for a in proof['actions'] if a['key']=='F5']
        if len(keys)!=1:raise ValueError('Review requires one actual F5 input')
        _,times=probe(video);indices,basis=review_indices(phases,held,times,keys[0])
        out=root/'qa/visual-review'/mode;out.mkdir(parents=True,exist_ok=True)
        filt='+'.join(f'eq(n\\,{i})' for i in indices)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(video),'-vf','select='+filt,'-fps_mode','passthrough',str(out/'frame-%03d.png')],check=True)
        width=420;cell=264;sheet=Image.new('RGB',(width*3,math.ceil(len(indices)/3)*cell),'#102326');draw=ImageDraw.Draw(sheet);rows=[]
        for j,i in enumerate(indices):
            path=out/f'frame-{j+1:03d}.png';im=Image.open(path).convert('RGB');im.thumbnail((420,236));x=j%3*width;y=j//3*cell
            sheet.paste(im,(x,y));draw.text((x+8,y+240),f'actual frame {i} / {times[i]:.4f}s',fill='white')
            rows.append({'path':path.relative_to(root).as_posix(),'frame_index':i,'timestamp':times[i],'sha256':sha(path)})
        sheet.save(out/'contact.jpg',quality=94)
        reports[mode]={'origin':'actual_desktop_capture_frame_extraction','recording_sha256':sha(video),'samples':rows,'contact':(out/'contact.jpg').relative_to(root).as_posix(),
                       'selection_basis':basis,'scope':'Context-only samples do not establish page identity, arrival, motion or acceptance'}
        save(out/'index.json',reports[mode])
    save(root/'qa/visual-review/index.json',reports);return reports


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');a=p.parse_args();r=extract(a.run);print(json.dumps({k:len(v['samples']) for k,v in r.items()}))
