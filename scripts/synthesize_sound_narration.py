#!/usr/bin/env python3
"""Generate original Chinese narration with an external offline Sherpa TTS model.

The model and its Python environment stay outside the skill and delivery files.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--story',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--speed',type=float,default=.9)
    parser.add_argument('--model-url',default='https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-vits-zh-ll.tar.bz2')
    args=parser.parse_args()
    import numpy as np
    import sherpa_onnx
    import soundfile as sf
    source=args.story.read_bytes();story=json.loads(source)
    args.out.mkdir(parents=True,exist_ok=False)
    config=sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(args.model/'model.onnx'),
             lexicon=str(args.model/'lexicon.txt'),tokens=str(args.model/'tokens.txt'),
             noise_scale=.35,noise_scale_w=.5),num_threads=2,provider='cpu'),
        rule_fsts=str(args.model/'phone.fst'))
    if not config.validate():raise ValueError('Invalid offline voice model')
    tts=sherpa_onnx.OfflineTts(config);records=[]
    for scene in story['scenes']:
        if not scene['narration']:continue
        audio=tts.generate(scene['narration'],sid=0,speed=args.speed)
        data=np.asarray(audio.samples,dtype=np.float32)
        peak=float(np.max(np.abs(data)))
        if not math.isfinite(peak) or peak <= .001:raise ValueError('Empty speech output')
        data=data*(.82/peak)
        path=args.out/(scene['id']+'.wav');sf.write(path,data,audio.sample_rate)
        duration=len(data)/audio.sample_rate
        if duration+.6 > scene['duration_seconds']-.7:
            raise ValueError(f"Narration overflows scene {scene['id']}: {duration:.2f}s")
        records.append({'scene':scene['id'],'text':scene['narration'],'duration_seconds':duration,
                        'sample_rate':audio.sample_rate,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        print(scene['id'],round(duration,2),flush=True)
    sample_rate=48000
    for freq in [220,440]:
        n=int(sample_rate*.85);t=np.arange(n)/sample_rate
        envelope=np.minimum(1,t/.025)*np.minimum(1,(.85-t)/.06)
        sf.write(args.out/f'tone-{freq}.wav',.16*np.sin(2*np.pi*freq*t)*envelope,sample_rate)
    (args.out/'narration-manifest.json').write_text(json.dumps({
        'format_version':1,'origin':'offline_synthetic_narration','engine':'sherpa-onnx',
        'engine_version':sherpa_onnx.__version__,'speaker_id':0,'speed':args.speed,
        'model_url':args.model_url,
        'model_sha256':hashlib.sha256((args.model/'model.onnx').read_bytes()).hexdigest(),
        'story_sha256':hashlib.sha256(source).hexdigest(),'clips':records},
        ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
