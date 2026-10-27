#!/usr/bin/env python3
"""Check actual cut continuity, global progress and measured sentence/audio timing.

Specific to the authored sound example; never WPS playback evidence.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def analyze(project,video,out):
 import numpy as np
 from PIL import Image,ImageDraw
 project,video,out=Path(project),Path(video),Path(out);out.mkdir(parents=True,exist_ok=False)
 story=json.loads((project/'src/story.json').read_text());captions=json.loads((project/'src/captions.json').read_text())
 manifest=json.loads((project/'public/audio/narration-manifest.json').read_text())
 errors=[];cuts=[];contacts=[]
 for cut in [story['scenes'][0]['duration_seconds'],sum(s['duration_seconds'] for s in story['scenes'][:2])]:
  frames=list(range(round(cut*30)-4,round(cut*30)+5));select='+'.join(f'eq(n\\,{n})' for n in frames)
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(video),'-vf',f'select={select},crop=400:250:760:440:exact=1','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
  a=np.frombuffer(raw,dtype=np.uint8).reshape(-1,250,400,3)
  if len(a)!=len(frames):raise ValueError('Missing cut samples')
  points=[]
  for n,f in zip(frames,a):
   mask=(f[:,:,0]>205)&(f[:,:,1]>100)&(f[:,:,1]<215)&(f[:,:,2]<145)
   yy,xx=np.where(mask)
   if len(xx)<100:raise ValueError('Tagged parcel not isolated at cut')
   points.append({'frame':n,'x':float(xx.mean()+760+.5),'y':float(yy.mean()+440+.5)})
   tile=Image.new('RGB',(400,280),'#0b1930');tile.paste(Image.fromarray(f),(0,0));ImageDraw.Draw(tile).text((8,258),f'actual frame {n} @ {n/30:.3f}s',fill='white');contacts.append(tile)
  maximum=max(float(np.hypot(b['x']-a['x'],b['y']-a['y'])) for a,b in zip(points,points[1:]))
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(video),'-vf',f'select={select},crop=1920:4:0:1076:exact=1','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
  progress=[];duration=sum(s['duration_seconds'] for s in story['scenes'])
  for n,f in zip(frames,np.frombuffer(raw,dtype=np.uint8).reshape(-1,4,1920,3)):
   row=f[2];indices=np.where((row[:,1]>150)&(row[:,2]>140)&(row[:,0]<180))[0]
   width=int(indices[-1]+1) if len(indices) else 0;expected=1920*(n/30)/duration
   progress.append({'frame':n,'width_px':width,'expected_px':expected,'error_px':abs(width-expected)})
  max_progress=max(p['error_px'] for p in progress)
  if maximum>3:errors.append(f'Tagged parcel jumps at {cut}s: {maximum:.2f}px/frame')
  if max_progress>3 or any(b['width_px']+1<a['width_px'] for a,b in zip(progress,progress[1:])):errors.append(f'Global progress resets/drifts at {cut}s')
  cuts.append({'seconds':cut,'max_adjacent_step_px':maximum,'parcel_points':points,'max_progress_error_px':max_progress,'progress':progress})
 canvas=Image.new('RGB',(400*6,280*3),'#0b1930')
 for i,im in enumerate(contacts):canvas.paste(im,((i%6)*400,(i//6)*280))
 canvas.save(out/'actual-cuts.jpg')
 # Compare encoded narration against the independently generated sentence stems.
 rate=8000
 def audio(path):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ac','1','-ar',str(rate),'-f','f32le','pipe:1']),dtype=np.float32)
 encoded=audio(video);sentences=[];start=0
 for scene in story['scenes']:
  clip=next((c for c in manifest['clips'] if c['scene']==scene['id']),None)
  if not clip:start+=scene['duration_seconds'];continue
  stem=audio(project/'public/audio'/(scene['id']+'.wav'))
  for i,cue in enumerate(clip.get('cues',[])):
   row=captions[scene['id']][i]
   if row['text']!=cue['text'] or abs(row['startMs']-(cue['start_seconds']+.6)*1000)>1 or abs(row['endMs']-(cue['end_seconds']+.6)*1000)>1:errors.append('Caption does not match measured sentence: '+scene['id'])
   source_at=cue['start_seconds']+.12;length=min(.7,cue['end_seconds']-source_at-.08)
   if length<.2:raise ValueError('Sentence too short for waveform check')
   reference=stem[round(source_at*rate):round((source_at+length)*rate)].astype(np.float64)
   expected=round((start+.6+source_at)*rate);radius=round(.08*rate)
   search=encoded[expected-radius:expected+radius+len(reference)].astype(np.float64)
   dots=np.correlate(search,reference,'valid');energies=np.convolve(search**2,np.ones(len(reference)),'valid')
   correlations=dots/np.sqrt(np.maximum(energies*np.sum(reference**2),1e-16));best=int(correlations.argmax())
   corr=float(correlations[best]);offset=(best-radius)/rate
   if corr<.96 or abs(offset)>1/30:errors.append('Encoded sentence timing/audio mismatch: '+scene['id'])
   sentences.append({'scene':scene['id'],'cue':i,'text':cue['text'],'normalized_correlation':corr,'offset_seconds':offset})
  start+=scene['duration_seconds']
 report={'origin':'measurement_of_original_authored_science_video','video_sha256':sha(video),'story_sha256':sha(project/'src/story.json'),'status':'failed' if errors else 'passed','cuts':cuts,'sentence_audio_checks':sentences,'sentence_timing_scope':'Generated sentence boundaries and encoded waveform correlation, not word ASR or full human listening review. Legacy sources without measured cues are not certified for sentence timing.','thresholds':{'max_cut_step_px':3,'max_progress_error_px':3,'min_audio_correlation':.96,'max_audio_offset_seconds':1/30},'errors':errors}
 (out/'edit-quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',required=True);p.add_argument('--video',required=True);p.add_argument('--out',required=True);a=p.parse_args();r=analyze(a.project,a.video,a.out)
 print(json.dumps({'status':r['status'],'max_cut_steps':[c['max_adjacent_step_px'] for c in r['cuts']],'sentence_audio_checks':len(r['sentence_audio_checks']),'errors':r['errors']},ensure_ascii=False,indent=2));raise SystemExit(1 if r['errors'] else 0)
