#!/usr/bin/env python3
"""Check the rendered science film, then seal the video-first handoff.

Narrow tests for this authored example: actual orange-parcel pixels, tone FFTs,
encoded/reference frames, source/audio bindings and reviewed scientific frames.
"""
import argparse
import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path

from native_motion.video_first import digest,seal
from native_motion.acoustics import displacement,wavelength


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--video',type=Path,required=True)
    parser.add_argument('--reference-frames',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--lock',type=Path,required=True)
    parser.add_argument('--visual-review-note',required=True,help='Specific review of the current source frames; never inferred from running pixel checks')
    args=parser.parse_args()
    if not args.visual_review_note.strip():raise ValueError('Review the actual frames and provide a specific note')
    import numpy as np
    from PIL import Image
    from check_native_playback import compare_frame
    args.out.mkdir(parents=True,exist_ok=False)
    story_path=args.project/'src/story.json';story=json.loads(story_path.read_text())
    narration=json.loads((args.project/'public/audio/narration-manifest.json').read_text())
    if narration['story_sha256']!=digest(story_path):raise ValueError('Narration/script mismatch')
    for clip in narration['clips']:
        if digest(args.project/'public/audio'/(clip['scene']+'.wav'))!=clip['sha256']:
            raise ValueError('Narration clip changed')
    metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(args.video)]))
    video=next(s for s in metadata['streams'] if s['codec_type']=='video')
    expected_duration=sum(s['duration_seconds'] for s in story['scenes'])
    errors=[]
    if (video['width'],video['height'],video['avg_frame_rate'],int(video['nb_frames']))!=(1920,1080,'30/1',expected_duration*30):errors.append('Unexpected video dimensions, frame rate or length')
    if not any(s['codec_type']=='audio' for s in metadata['streams']):errors.append('Narration audio missing')
    frames=[round(t*30) for t in story.get('qa_sample_seconds',[3,11,22,30,42,56,65,72])]
    select='+'.join(f'eq(n\\,{n})' for n in frames)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(args.video),'-vf','select='+select,'-fps_mode','passthrough',str(args.out/'frame-%02d.png')],check=True)
    comparisons=[]
    for i,n in enumerate(frames,1):
        comparison=compare_frame(Image.open(args.out/f'frame-{i:02}.png'),Image.open(args.reference_frames/f'element-{n:04}.png'))
        comparisons.append({'frame':n,**comparison})
        if comparison['rmse']>8 or comparison['max_tile_rmse']>18:errors.append('Encoded/reference frame differs: '+str(n))
    # All sampled frames are after the parcel camera has settled at 1.85x.
    parcel_start=story['scenes'][0]['duration_seconds']
    parcel_end=parcel_start+story['scenes'][1]['duration_seconds']
    first=round((parcel_start+2)*30);last=round((parcel_end-1)*30)
    selected=list(range(first,last,3))
    vf=f'select=between(n\\,{first}\\,{last-1})*not(mod(n-{first}\\,3)),crop=210:120:850:540:exact=1'
    process=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-i',str(args.video),'-vf',vf,'-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
    observations=[]
    try:
        for n in selected:
            raw=process.stdout.read(210*120*3)
            if len(raw)!=210*120*3:raise ValueError('Missing decoded parcel frame')
            a=np.frombuffer(raw,dtype=np.uint8).reshape(120,210,3)
            mask=(a[:,:,0]>205)&(a[:,:,1]>100)&(a[:,:,1]<215)&(a[:,:,2]<145)
            yy,xx=np.where(mask)
            if len(xx)<300:raise ValueError('Orange parcel not observed')
            x,y=float(xx.mean()+850+.5),float(yy.mean()+540+.5)
            expected_x=960+1.85*displacement(880,n/30)
            observations.append({'frame':n,'seconds':n/30,'x':x,'y':y,'expected_x':expected_x,'error_px':abs(x-expected_x)})
        if process.stdout.read(1) or process.wait()!=0:raise ValueError('Unexpected decoded parcel frames')
    finally:
        process.stdout.close()
        if process.poll() is None:process.terminate();process.wait()
    max_error=max(o['error_px'] for o in observations);vertical=max(o['y'] for o in observations)-min(o['y'] for o in observations)
    if max_error>2 or vertical>2:errors.append('Parcel pixels differ from the bounded horizontal model')
    if max(o['x'] for o in observations)-min(o['x'] for o in observations)<75:errors.append('Insufficient local oscillation observed')
    tones=[]
    frequency_start=sum(s['duration_seconds'] for s in story['scenes'][:4])
    for at,expected in [(frequency_start+8.2,220),(frequency_start+10.2,440)]:
        raw=subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(at),'-i',str(args.video),'-t','0.4','-ac','1','-ar','48000','-f','f32le','pipe:1'])
        samples=np.frombuffer(raw,dtype=np.float32);spectrum=np.abs(np.fft.rfft(samples*np.hanning(len(samples))))
        hz=float(np.fft.rfftfreq(len(samples),1/48000)[spectrum.argmax()])
        tones.append({'seconds':at,'expected_hz':expected,'measured_hz':hz})
        if abs(hz-expected)>2.5:errors.append('Rendered tone does not match its label')
    if abs(story['facts']['wavelength_440_m']-wavelength(343,440))>1e-12:errors.append('Wavelength number mismatch')
    edit_quality=None
    if story.get('revision')=='continuity-and-measured-sentence-captions':
        from check_sound_edit import analyze
        edit_quality=analyze(args.project,args.video,args.out/'edit')
        errors.extend(edit_quality['errors'])
        if not all(c.get('cues') for c in narration['clips']):errors.append('This revision requires measured sentence cues')
        if not edit_quality['sentence_audio_checks']:errors.append('Encoded narration was not checked')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-framerate','1','-i',str(args.out/'frame-%02d.png'),'-vf','scale=640:360,tile=2x4','-frames:v','1',str(args.out/'contact.jpg')],check=True)
    report={'origin':'rendered_science_video_qa','status':'failed' if errors else 'passed',
            'checked_at':datetime.now(timezone.utc).isoformat(),'video_sha256':digest(args.video),'story_sha256':digest(story_path),
            'metadata':metadata,'frame_comparisons':comparisons,'parcel_max_model_error_px':max_error,
            'parcel_vertical_range_px':vertical,'parcel_observations':observations,'tone_measurements':tones,
            'edit_quality':edit_quality,
            'visual_review':{'note':args.visual_review_note,'reviewed_at':datetime.now(timezone.utc).isoformat(),'source_frame_sha256':{str(n):digest(args.reference_frames/f'element-{n:04}.png') for n in frames}},
            'scope':'Original authored animation, not a PPT/WPS capture. Pixel test covers one tagged parcel after zoom; tone FFT covers two isolated windows. Caption timing provenance is in video-origin.json.','errors':errors}
    quality=args.out/'video-quality.json';quality.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','parcel_max_model_error_px','parcel_vertical_range_px','tone_measurements','errors']},ensure_ascii=False,indent=2))
    if errors:raise SystemExit(1)
    seal(args.video,story_path,quality,args.lock)


if __name__=='__main__':main()
