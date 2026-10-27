#!/usr/bin/env python3
"""Prepare the authored sound-science Remotion project, before making any PPT.

Requires original narration clips and full installed Noto Sans CJK SC fonts.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMPONENTS=['QuestionScene','ParcelScene','CompressionScene','ParallelScene',
            'FrequencyScene','WavelengthScene','RecapScene','CreditsScene']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def captions(story,audio):
    durations={c['scene']:c['duration_seconds'] for c in audio['clips']}
    clips={c['scene']:c for c in audio['clips']}
    result={};global_cues=[];start=0
    for scene in story['scenes']:
        measured=clips.get(scene['id'],{}).get('cues')
        if measured is not None:
            if ''.join(c['text'] for c in measured)!=scene['narration']:
                raise ValueError('Measured captions do not match the narration')
            previous=0;rows=[]
            for cue in measured:
                a,b=cue['start_seconds'],cue['end_seconds']
                if not 0<=previous<=a<b<=durations[scene['id']]+1e-8:
                    raise ValueError('Invalid measured sentence boundaries')
                previous=b
                rows.append(dict(text=cue['text'],startMs=round((.6+a)*1000),endMs=round((.6+b)*1000),timestampMs=None,confidence=None))
                global_cues.append((start+.6+a,start+.6+b,cue['text']))
            result[scene['id']]=rows;start+=scene['duration_seconds'];continue
        chunks=[]
        for sentence in re.findall(r'[^。！？]+[。！？]?',scene['narration']):
            if len(sentence)<=29:chunks.append(sentence);continue
            current=''
            for part in re.findall(r'[^，；]+[，；]?',sentence):
                if current and len(current)+len(part)>29:chunks.append(current);current=''
                current+=part
            if current:chunks.append(current)
        cursor=.6;total=sum(map(len,chunks)) or 1;rows=[]
        for chunk in chunks:
            end=cursor+durations[scene['id']]*len(chunk)/total
            rows.append(dict(text=chunk,startMs=round(cursor*1000),endMs=round(end*1000),timestampMs=None,confidence=None))
            global_cues.append((start+cursor,start+end,chunk));cursor=end
        result[scene['id']]=rows;start+=scene['duration_seconds']
    return result,global_cues


def prepare(story_path,audio_dir,destination):
    destination=Path(destination)
    if destination.exists():raise ValueError('Preserve the previous project; use a new output directory')
    story_path,audio_dir=Path(story_path),Path(audio_dir)
    story=json.loads(story_path.read_text());manifest=json.loads((audio_dir/'narration-manifest.json').read_text())
    if manifest['story_sha256']!=sha(story_path):raise ValueError('Narration belongs to a different script')
    if len(story['scenes'])!=len(COMPONENTS) or story['canvas']!={'width':1920,'height':1080,'fps':30}:
        raise ValueError('This authored example requires its eight scenes at 1920x1080/30')
    for clip in manifest['clips']:
        if sha(audio_dir/(clip['scene']+'.wav'))!=clip['sha256']:raise ValueError('Narration changed: '+clip['scene'])
        scene=next(s for s in story['scenes'] if s['id']==clip['scene'])
        if clip['duration_seconds']+1.3>scene['duration_seconds']:raise ValueError('Narration exceeds scene')
        if clip['scene']=='frequency' and clip['duration_seconds']+.6>=8:
            raise ValueError('Narration would overlap the isolated tone comparison')
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'assets/science-video',destination)
    public=destination/'public';public.mkdir();shutil.copytree(audio_dir,public/'audio')
    shutil.copy2(story_path,destination/'src/story.json')
    cc,cues=captions(story,manifest)
    (destination/'src/captions.json').write_text(json.dumps(cc,ensure_ascii=False,indent=2)+'\n')
    def stamp(t):
        n=round(t*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
    (destination/'captions.zh-CN.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{t}' for i,(a,b,t) in enumerate(cues))+'\n')
    imports='\n'.join(f"import {{{c}}} from './{c}';" for c in COMPONENTS)
    scenes='\n'.join(f'<Series.Sequence name="{s["id"]}" durationInFrames={{{s["duration_seconds"]}*fps}} premountFor={{fps}}><{c}/></Series.Sequence>' for s,c in zip(story['scenes'],COMPONENTS))
    total=sum(s['duration_seconds'] for s in story['scenes'])*30
    registrations='\n'.join(f'<Composition id="{s["id"].title()}" component={{{c}}} width={{1920}} height={{1080}} fps={{30}} durationInFrames={{{s["duration_seconds"]*30}}}/>' for s,c in zip(story['scenes'],COMPONENTS))
    (destination/'src/Root.tsx').write_text(f"import React from 'react';\nimport {{Composition,Folder,Series,useVideoConfig}} from 'remotion';\n{imports}\nexport const SoundJourney:React.FC=()=>{{const {{fps}}=useVideoConfig();return <Series>{scenes}</Series>}};\nexport const Root:React.FC=()=> <><Composition id=\"SoundJourney\" component={{SoundJourney}} width={{1920}} height={{1080}} fps={{30}} durationInFrames={{{total}}}/><Folder name=\"Scenes\">{registrations}</Folder></>;\n")
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from native_motion.fonts import resolve_font
    text=''.join(p.read_text() for p in (destination/'src').glob('*') if p.is_file())
    font_records=[]
    for bold,style in [(False,'Regular'),(True,'Bold')]:
        info=resolve_font('Noto Sans CJK SC',bold)
        if not info or not info['matched']:raise ValueError('Install full Noto Sans CJK SC fonts')
        font=TTFont(info['path'],fontNumber=info['index']);options=subset.Options();options.recalc_timestamp=False
        sub=subset.Subsetter(options);sub.populate(text=text);sub.subset(font);font.flavor='woff'
        target=public/f'NotoSansSC-{style}.woff';font.save(target);font.close()
        font_records.append({'family':'Noto Sans CJK SC','style':style,'index':info['index'],'subset':target.name,'sha256':sha(target)})
    for name in ['SpaceGrotesk-SemiBold.ttf','Space-Grotesk-LICENSE.txt','Noto-CJK-COPYRIGHT.txt']:
        shutil.copy2(ROOT/'assets/fonts'/name,public/name)
    (destination/'font-manifest.json').write_text(json.dumps(font_records,indent=2)+'\n')
    (destination/'video-origin.json').write_text(json.dumps({'origin':'original_authored_science_animation',
       'is_pptx_playback_recording':False,'story_sha256':sha(story_path),'narration_manifest_sha256':sha(audio_dir/'narration-manifest.json'),
       'duration_seconds':total/30,'caption_timing':'Independently synthesized sentence sample boundaries; not word-forced alignment.' if all('cues' in c for c in manifest['clips']) else 'Sentence durations allocated by text length within each measured narration clip; not word-forced alignment.',
       'ppt_started':False},indent=2)+'\n')
    (destination/'README.md').write_text('''# 声波科普：先视频，后 PPT

这是独立原创科普动画成片的源工程，不是 WPS 录屏。参考与事实来源在 src/story.json，中文脚本和旁白均为本项目重新制作，未使用参考视频片段。所有场景单独注册，可在 Studio 打开；粒子阵列由同一个模型模板控制。

```bash
npm ci
npm run studio
npm run render -- --browser-executable=/path/to/chromium
```

默认画面 1920×1080、30fps、74秒。public/audio 为合成中文旁白和本项目生成的220/440Hz纯音。外部TTS模型与播放器不打包。字幕是 Caption JSON 与 SRT，按实际音频长度分句近似对齐，未做词级强制对齐。

先完成视频与物理/音频/画面检查，封存 VIDEO_LOCK.json，再制作对应 PPT。PPT 是使用已知对象和分镜重新制作的原生教学版本，不声称 MP4 无损转为原生动画。
''',encoding='utf-8')
    readme=destination/'README.md'
    text=readme.read_text().replace('74秒',f'{total/30:g}秒')
    if all('cues' in c for c in manifest['clips']):
        text=text.replace('按实际音频长度分句近似对齐，未做词级强制对齐','按独立合成句子的实际音频边界对齐，未做词级强制对齐')
    readme.write_text(text)
    return {'project':str(destination.resolve()),'duration_seconds':total/30,'caption_cues':len(cues)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--story',type=Path,default=ROOT/'examples/science-video/sound-story.json')
    parser.add_argument('--audio-dir',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.story,args.audio_dir,args.out),ensure_ascii=False,indent=2))
