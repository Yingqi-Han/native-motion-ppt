#!/usr/bin/env python3
"""Derive editable teaching slides only after the original science film is sealed."""
import argparse
import copy
import json
import math
from datetime import datetime,timezone
from pathlib import Path

from native_motion.acoustics import displacement,parcels
from native_motion.recipes import fade_in,wipe_in
from native_motion.video_first import verify,digest

BG,WHITE,MUTED,CYAN,ORANGE,LINE='0B1930','F5F2E8','A7B6C8','6CE2D0','FFAC4B','29415C'
SANS,LATIN='Noto Sans CJK SC','Space Grotesk SemiBold'
TIMES=[3,11,22,30,42,56,65,72]


def text(ident,value,box,size=40,color=WHITE,role='body',**extra):
    font=extra.pop('font',SANS)
    return dict(id=ident,kind='text',text=value,box=box,size=size,fill=color,font=font,role=role,**extra)


def rect(ident,box,color=BG,**extra):return dict(id=ident,kind='rect',box=box,fill=color,**extra)


def path(ident,box,d,color=CYAN,width=4,**extra):
    return dict(id=ident,kind='path',box=box,d=d,fill='none',stroke=color,stroke_width=width,role='visual',**extra)


def arrow(ident,x,y,width,label,color=CYAN,double=False,click=None):
    d=f'M 0 12 L {width} 12 M {width-17} 2 L {width} 12 L {width-17} 22'
    if double:d+=' M 17 2 L 0 12 L 17 22'
    line=path(ident,[x,y-12,width,24],d,color)
    caption=text(ident+'-label',label,[x,y-77,width,62],40,color,'caption',align='center')
    if click is not None:
        line=wipe_in(line,at=0,duration=800,click=click,direction='right')
        caption=fade_in(caption,at=450,duration=400,click=click)
    return [line,caption]


def viewport():
    # Fixed matching masks define a deliberate figure viewport on every slide.
    # They are behind all labels and remain stationary during native Morph.
    return [rect('clip-left',[0,355,150,530],role='decoration'),
            rect('clip-right',[1770,355,150,530],role='decoration'),
            rect('clip-top',[0,0,1920,355],role='decoration'),
            rect('clip-bottom',[0,885,1920,195],role='decoration')]


def field(story,time,zoom=1,dim=1,bands=False):
    model=story['model'];dots=parcels(time,model);objects=[]
    def point(x,y):return (960+(x-880)*zoom,600+(y-530)*zoom) if zoom!=1 else (x,y)
    if bands:
        lam=model['wavelength_px'];phase=(time/model['period_seconds'])%1
        for i,n in enumerate(range(-3,5)):
            x=model['origin_x']+lam*(phase+.5+n)
            if 180<x<1790:
                objects.append(rect(f'pressure-band-{i}',[x-50,375,100,380],CYAN,opacity=.12,role='visual'))
    for col in range(model['columns']):
        column=[p for p in dots if p['column']==col];x,y0=point(column[0]['x'],model['origin_y'])
        radius=6.8*zoom;children=[]
        for p in column:
            if p['tagged']:continue
            _,y=point(p['x'],p['y'])
            children.append(dict(id=p['id'],kind='ellipse',box=[0,y-y0,2*radius,2*radius],fill=WHITE,opacity=.88*dim,role='visual'))
        objects.append(dict(id=f'air-column-{col}',kind='group',box=[x-radius,y0-radius,2*radius,(model['rows']-1)*model['row_spacing_px']*zoom+2*radius],objects=children,role='visual',allow_overflow=True))
    marker=next(p for p in dots if p['tagged']);x,y=point(marker['x'],marker['y'])
    r=11*zoom
    objects += [dict(id='tagged-parcel',kind='ellipse',box=[x-r,y-r,2*r,2*r],fill=ORANGE,role='visual'),
                dict(id='tagged-halo',kind='ellipse',box=[x-20*zoom,y-20*zoom,40*zoom,40*zoom],fill='none',stroke=ORANGE,stroke_width=2.2*zoom,role='visual')]
    return objects


def closed_horizontal_cycle(time=11,zoom=1.85):
    phase=2*math.pi*((880-340)/480-time/3);a=24*zoom;base=a*math.sin(phase)
    points=[[0,0]]
    for i in range(4):
        p,q=phase-i*math.pi/2,phase-(i+1)*math.pi/2
        points.extend([[a*math.sin(p)-base-a*math.pi/6*math.cos(p),0],
                       [a*math.sin(q)-base+a*math.pi/6*math.cos(q),0],
                       [a*math.sin(q)-base,0]])
    points[-1]=[0,0]
    return points


def generate(story):
    slides=[];mapping=[]
    for index,scene in enumerate(story['scenes']):
        prefix=scene['id'];objects=[];annotations=[];clicks=[]
        if index in [0,1,2,3,6]:
            objects=field(story,TIMES[index],zoom=1.85 if index==1 else 1,
                          dim=.2 if index==1 else .4 if index==3 else 1,bands=index==2)
        objects+=viewport()
        title='记住这两个方向。' if index==6 else '让一个标记，讲清一个概念。' if index==7 else scene['title']
        objects += [text('brand','SOUND / 看见声音',[120,65,1200,44],25,CYAN,'label'),
                    text(prefix+'-folio',f'{index+1:02} / 08',[1600,65,200,44],25,MUTED,'label',align='right'),
                    text(prefix+'-title',title,[120,170,1680,210 if index==0 else 106],80,WHITE,'title',bold=True),
                    text(prefix+'-caption',scene['subtitle'],[180,935,1560,65],40,WHITE,'caption',align='center'),
                    text(prefix+'-scope','平均运动示意 · 位移与时间已放大 · 未画热运动',[120,1023,1420,34],20,MUTED,'caption')]
        if index==0:
            annotations += [dict(id='speaker',kind='polygon',box=[130,452,121,196],points=[[0,53],[56,53],[121,0],[121,196],[56,143],[0,143]],fill=CYAN,role='visual')]
        elif index==1:
            for o in objects:
                if o['id'] in ['tagged-parcel','tagged-halo']:
                    o['animations']=[dict(kind='move',at=200,duration=3000,path=closed_horizontal_cycle(),accel=0,decel=0)]
            annotations+=arrow('local-motion',840,795,240,'局部往复',ORANGE,True)
            annotations += [path('mean-position',[960,500,.01,200],'M 0 0 L 0 200',ORANGE,1.5,opacity=.45)]
        elif index==2:
            clicks=[1700]
            annotations+=arrow('wave-travel',420,835,1100,'疏密变化与能量向前传播',click=1)
            annotations += [text('frozen-pressure','定格观察压缩区；连续传播见对应视频。',[380,330,1350,50],30,MUTED,'caption')]
        elif index==3:
            annotations+=arrow('local-direction',700,470,420,'空气的平均振动',ORANGE,True)
            annotations+=arrow('wave-direction',440,760,1060,'声波的传播方向')
            annotations += [text('parallel-label','平行',[1430,490,300,140],90,WHITE,'title',bold=True)]
        elif index==4:
            for freq,lam,period,origin,y,physical in [(220,640,4,180,465,'1.56 m'),(440,320,2,340,715,'0.78 m')]:
                annotations.append(text(f'freq-{freq}',f'{freq} Hz',[120,y-58,240,90],58,CYAN,'label'))
                for row,dy in enumerate([-18,18]):
                    for j in range(26):
                        x0=350+j*51;x=x0+displacement(x0,4,25,lam,period,origin)
                        annotations.append(dict(id=f'freq-{freq}-{row}-{j}',kind='ellipse',box=[x-7,y+dy-7,14,14],fill=WHITE,role='visual'))
                annotations.append(path(f'lambda-brace-{freq}',[500,y+65,lam,14],f'M 0 0 L 0 14 L {lam} 14 L {lam} 0',ORANGE,3))
                annotations.append(text(f'lambda-{freq}','λ ≈ '+physical,[500,y+90,lam,58],36,ORANGE,'label',align='center'))
            annotations.append(text('frequency-frozen','定格测量波长',[1400,340,370,50],30,ORANGE,'caption',align='right'))
        elif index==5:
            clicks=[2500]
            annotations += [text('air-condition','20°C 空气 · v ≈ 343 m/s',[130,340,1400,72],46,MUTED,'caption'),
                            text('wavelength-formula','λ = v / f',[130,480,700,130],84,CYAN,'body'),
                            fade_in(text('wavelength-inputs','343 / 440',[130,610,700,120],70,WHITE,'data'),click=1),
                            fade_in(text('wavelength-result','0.78',[900,450,440,240],180,ORANGE,'data',bold=True),click=1,at=650,duration=650),
                            fade_in(text('wavelength-unit','米',[1390,530,180,120],80,ORANGE,'label'),click=1,at=650,duration=650)]
            annotations+= [fade_in(rect(f'compression-{i}',[x-17,700,34,140],CYAN,opacity=.17,role='visual'),click=1,at=1000) for i,x in enumerate([900,1640])]
            for o in arrow('one-wavelength',900,780,740,'相邻压缩区之间，一个波长',CYAN,True):
                annotations.append(fade_in(o,click=1,at=1000))
        elif index==6:
            annotations+=arrow('recap-local',750,355,260,'空气局部往复',ORANGE,True)
            annotations+=arrow('recap-wave',450,840,1050,'声波向外传播')
        else:
            annotations += [text('source-observation','观察方法：University of Salford / Dan Russell',[130,380,1650,80],42,MUTED),
                            text('source-facts','事实核对：UCLA Physics · Sound Waves',[130,470,1650,80],42,MUTED),
                            text('source-original','原创中文脚本、图形与程序动画 · 离线合成旁白',[130,610,1650,80],42,CYAN),
                            text('source-access','完整网址、模型说明和对应视频信息见备注。',[130,730,1650,70],32,MUTED,'caption')]
        objects+=annotations
        notes=scene['narration']+'\n\n'+story['model_scope']+'\n参考：\n'+'\n'.join(s['title']+'\n'+s['url'] for s in story['sources'])
        if index==1:notes+='\n教学版只给标记点做一次有限往复；背景粒子是冻结参考，连续场动画见原视频。'
        slides.append(dict(id='sound-'+prefix,duration=6000 if index==7 else 8000,background=BG,
                           transition=dict(kind='morph' if index in [1,2,3] else 'fade',duration=1600 if index in [1,2,3] else 450),
                           clicks=clicks,objects=objects,notes=notes))
        mapping.append({'slide':index+1,'scene':prefix,'video_start_seconds':sum(s['duration_seconds'] for s in story['scenes'][:index]),
                        'video_end_seconds':sum(s['duration_seconds'] for s in story['scenes'][:index+1]),
                        'representative_frame':TIMES[index]*30,'adaptation':'Native editable reconstruction; continuous wave field becomes a teaching snapshot, with a finite marker cycle and semantic reveals. Not lossless video conversion.'})
    return dict(version=1,title='声音走了，空气也走了吗？ · 对应教学 PPT',canvas=story['canvas'],
                theme=dict(font=SANS,latin_font=LATIN,background=BG,foreground=WHITE,accent=CYAN),slides=slides),mapping


def create(lock,out):
    data,paths=verify(lock);out=Path(out)
    if out.exists():raise ValueError('Preserve previous PPT projects; choose a new output directory')
    story=json.loads(paths['story'].read_text());doc,mapping=generate(story)
    out.mkdir(parents=True,exist_ok=False)
    (out/'project.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    (out/'nmp.json').write_text(json.dumps({'format_version':1,'source':'project.json','template':'sound-video-first','profile':'generic'},indent=2)+'\n')
    (out/'video-to-ppt.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),
       'video_locked_at':data['sealed_at'],'video_sha256':data['video']['sha256'],'video_lock_sha256':digest(lock),
       'story_sha256':data['story']['sha256'],'mapping':mapping},ensure_ascii=False,indent=2)+'\n')
    return {'project':str(out.resolve()),'slides':len(doc['slides']),'video_completed_before_ppt':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--video-lock',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(create(args.video_lock,args.out),ensure_ascii=False,indent=2))
