"""Bind a completed video and its checks before deriving a presentation."""
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal(video,story,quality,out):
    video,story,quality,out=map(lambda p:Path(p).resolve(),(video,story,quality,out))
    if out.exists():raise ValueError('Preserve the previous video lock')
    report=json.loads(quality.read_text())
    if report.get('status')!='passed' or report.get('origin')!='rendered_science_video_qa':
        raise ValueError('Complete video checks before deriving the PPT')
    if report.get('video_sha256')!=digest(video) or report.get('story_sha256')!=digest(story):
        raise ValueError('Video or story differs from its quality report')
    out.parent.mkdir(parents=True,exist_ok=True)
    data={'format_version':1,'stage':'video_completed_before_ppt','sealed_at':datetime.now(timezone.utc).isoformat(),
          'video':{'path':os.path.relpath(video,out.parent),'sha256':digest(video)},
          'story':{'path':os.path.relpath(story,out.parent),'sha256':digest(story)},
          'quality':{'path':os.path.relpath(quality,out.parent),'sha256':digest(quality)},
          'scope':'Binds this authored video, source script and actual checks. Not WPS playback evidence.'}
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return data


def verify(lock):
    lock=Path(lock).resolve();data=json.loads(lock.read_text())
    if data.get('format_version')!=1 or data.get('stage')!='video_completed_before_ppt':
        raise ValueError('A completed video lock is required first')
    paths={}
    for kind in ['video','story','quality']:
        p=(lock.parent/data[kind]['path']).resolve()
        if not p.is_file() or digest(p)!=data[kind]['sha256']:
            raise ValueError('Locked '+kind+' changed or is missing')
        paths[kind]=p
    q=json.loads(paths['quality'].read_text())
    if q.get('status')!='passed' or q.get('video_sha256')!=data['video']['sha256'] or q.get('story_sha256')!=data['story']['sha256']:
        raise ValueError('The locked quality record does not match the completed video')
    return data,paths
