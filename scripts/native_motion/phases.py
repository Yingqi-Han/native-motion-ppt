"""Infer page/transition phases from decoded pixels; source boxes only bound tracking."""
import math
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from .playback_motion import stable_runs,intervals,thumbnail_score,colored_box


def classify_pages(times,frames,references,manual_plan=None,show_key_seconds=None):
    """Use all-page independent references, not a hardcoded folio, palette or timestamp."""
    scores=np.empty((len(frames),len(references),2),dtype=float);activity=[];previous=None
    for i,frame in enumerate(frames):
        change=thumbnail_score(frame,previous)[1] if previous is not None else 0
        activity.append({'timestamp':times[i],'frame_index':i,'max_tile_change_rmse':change});previous=frame
        for j,ref in enumerate(references):scores[i,j]=thumbnail_score(frame,ref)
    events=intervals(times,[x['max_tile_change_rmse']>1.2 for x in activity])
    merit=scores[:,:,0]+.25*scores[:,:,1];best=np.argmin(merit,axis=1)
    sorted_scores=np.sort(merit,axis=1)
    unique=np.ones(len(times),dtype=bool) if len(references)==1 else sorted_scores[:,1]-sorted_scores[:,0]>.35
    pages=[];previous_end=0
    for j in range(len(references)):
        valid=(scores[:,j,0]<=8)&(scores[:,j,1]<=18)&(best==j)&unique
        valid &= np.array([x['max_tile_change_rmse']<=1.2 for x in activity])
        if manual_plan:
            window=manual_plan['pages'][j]
            valid &= (np.array(times)>max(window['click_at_seconds'],default=window['page_input_seconds'])+.2)&(np.array(times)<window['next_page_seconds']-.2)
            # Input association can disambiguate visually identical pages in manual mode.
            if not unique.any():valid=(scores[:,j,0]<=8)&(scores[:,j,1]<=18)&(np.array(times)>window['page_input_seconds']+.3)&(np.array(times)<window['next_page_seconds']-.2)
        else:valid &= np.array(times)>previous_end+.05
        runs=stable_runs(times,valid.tolist())
        if not runs:
            pages.append({'slide':j+1,'status':'pending','reason':'No unambiguous stable reference match for this page'});continue
        a,b=runs[-1] if manual_plan else runs[0]
        pick=max(a,b-round(.35/max(.001,float(np.median(np.diff(times))))))
        pages.append({'slide':j+1,'status':'passed','stable_interval_seconds':[times[a],times[b]],'held_timestamp':times[pick],
                      'held_frame_index':pick,'reference_rmse':float(scores[pick,j,0]),'reference_tile_rmse':float(scores[pick,j,1])})
        previous_end=times[b]
    if not manual_plan:
        # The first stable match locates identity; the last stable run before the next
        # page provides a complete held reference, including late automatic reveals.
        anchors=[p.get('stable_interval_seconds',[times[-1]])[0] for p in pages]
        for j,p in enumerate(pages):
            if p['status']!='passed':continue
            upper=anchors[j+1] if j+1<len(pages) else times[-1]+.01
            valid=(scores[:,j,0]<=8)&(scores[:,j,1]<=18)&(best==j)&unique
            valid &= (np.array(times)>=anchors[j])&(np.array(times)<upper)&np.array([x['max_tile_change_rmse']<=1.2 for x in activity])
            runs=stable_runs(times,valid.tolist())
            if runs:
                a,b=runs[-1];pick=max(a,b-round(.35/max(.001,float(np.median(np.diff(times))))))
                p.update(stable_interval_seconds=[times[a],times[b]],held_timestamp=times[pick],held_frame_index=pick,
                         reference_rmse=float(scores[pick,j,0]),reference_tile_rmse=float(scores[pick,j,1]))
    starts=[]
    for j,p in enumerate(pages):
        if p['status']!='passed':starts.append(None);continue
        if manual_plan:starts.append(manual_plan['pages'][j]['page_input_seconds']);continue
        if j==0:
            candidates=[e for e in events if e['start']<p['stable_interval_seconds'][0]]
            if show_key_seconds is not None:
                # Late reveals can be the last activity before the full reference
                # matches. Keep the first observed interval intersecting/after the
                # real F5 input, so earlier actor and bar motion is still scanned.
                # The interval may begin just before the wall-clock key because
                # media PTS and input-wall clocks have a small startup offset.
                after_key=[e for e in candidates if e['end']>=show_key_seconds]
                if after_key:
                    starts.append(after_key[0]['start'])
                    p['entry_window_basis']='first_observed_activity_intersecting_or_after_recorded_F5'
                else:
                    starts.append(None);p.update(status='pending',reason='No observed first-page entry activity after the actual show key')
            else:
                starts.append(candidates[-1]['start'] if candidates else max(0,p['stable_interval_seconds'][0]-.3))
            continue
        prev=pages[j-1]
        if prev['status']!='passed':starts.append(None);continue
        candidates=[e for e in events if e['end']>=prev['stable_interval_seconds'][1]-.15 and e['start']<p['stable_interval_seconds'][0]]
        starts.append(candidates[0]['start'] if candidates else None)
        if not candidates:p.update(status='pending',reason='The arriving page matched, but transition onset could not be observed')
    return pages,starts,activity,events


def color_palette(obj,background):
    colors=[]
    def collect(o):
        for key in ['fill','stroke']:
            c=o.get(key)
            if isinstance(c,str) and len(c)==6 and c!='none':
                rgb=list(bytes.fromhex(c));chroma=max(rgb)-min(rgb)
                if chroma>=50 and max(abs(a-b) for a,b in zip(rgb,background))>=45:colors.append(rgb)
        for child in o.get('objects',[]):collect(child)
    collect(obj)
    if not colors:return []
    # Gradient endpoint colors may never occur as solid pixels. Keep all saturated
    # source colors and let actual endpoint contours establish visibility.
    return [list(c) for c in sorted(set(map(tuple,colors)))]


def morph_candidates(doc):
    result=[];uncovered=[];w,h=doc['canvas']['width'],doc['canvas']['height']
    for i in range(1,len(doc['slides'])):
        prev,slide=doc['slides'][i-1:i+1]
        if slide['transition']['kind']!='morph':continue
        old={o['id']:o for o in prev['objects']}
        changed=False
        for o in slide['objects']:
            a=old.get(o['id'])
            if not a or max(abs(x-y) for x,y in zip(a['box'],o['box']))<3:continue
            changed=True
            reason=None
            if o['kind'] not in {'rect','ellipse','group'} or a['kind']!=o['kind']:reason='Text/complex geometry Morph requires separate template tracking'
            elif o['rotation'] or a['rotation'] or o['opacity']!=1 or a['opacity']!=1:reason='Rotated/translucent Morph is outside contour tracking'
            palette=color_palette(o,list(bytes.fromhex(slide['background'])))
            if not palette:reason=reason or 'No isolated saturated source contour; requires visual review'
            if reason:uncovered.append({'slide':i+1,'object':o['id'],'status':'pending','reason':reason});continue
            b0,b1=a['box'],o['box'];pad=12
            roi=[max(0,math.floor(min(b0[0],b1[0])-pad)),max(0,math.floor(min(b0[1],b1[1])-pad)),
                 min(w,math.ceil(max(b0[0]+b0[2],b1[0]+b1[2])+pad)),min(h,math.ceil(max(b0[1]+b0[3],b1[1]+b1[3])+pad))]
            exclusions=[];decoration_exclusions=[]
            for s in [prev,slide]:
                for other in s['objects']:
                    if other['id']!=o['id'] and other['kind']=='text':exclusions.append(other['box'])
                    if other['id']!=o['id'] and other.get('role')=='decoration':
                        colors=[list(bytes.fromhex(other[k])) for k in ['fill','stroke'] if other.get(k) and other[k]!='none']
                        if colors and all(max(c)-min(c)<50 for c in colors):
                            x,y,ww,hh=other['box'];pad=max(2,other.get('stroke_width',0));decoration_exclusions.append([x-pad,y-pad,ww+2*pad,hh+2*pad])
            result.append({'slide':i+1,'object':o['id'],'kind':o['kind'],'roi':roi,'palette':palette,'background':list(bytes.fromhex(slide['background'])),
                           'excluded_text_boxes':exclusions,'excluded_decoration_boxes':decoration_exclusions,'source_boxes':[b0,b1]})
        if not changed:uncovered.append({'slide':i+1,'status':'pending','reason':'No geometrically changed shared Morph object; visual review required'})
    return result,uncovered


def contour(frame,candidate,endpoint_box=None,seed=None):
    pixels=frame.copy();x0,y0,x1,y1=candidate['roi']
    mask=np.zeros(pixels.shape[:2],dtype=bool)
    values=pixels.astype(np.float32);background=np.array(candidate.get('background',[244,242,234]),dtype=np.float32)
    delta=values-background
    for color in candidate['palette']:
        color=np.array(color,dtype=np.float32);vector=color-background;length=float(np.sum(vector*vector))
        if length<1:continue
        fraction=np.sum(delta*vector,axis=2)/length
        residual=np.max(np.abs(delta-fraction[:,:,None]*vector),axis=2)
        # Include light gradient/antialiased contour shades on the source-color to
        # actual background ray, without absorbing neutral arrows or dark labels.
        contrast=np.max(np.abs(delta),axis=2)
        residual_limit=22 if candidate.get('kind')=='group' else np.minimum(22,contrast*.14)
        mask |= (fraction>=.18)&(fraction<=1.15)&(residual<=residual_limit)&(contrast>38)
    if endpoint_box is not None:
        x,y,w,h=endpoint_box;allowed=np.zeros_like(mask)
        a=max(0,math.floor(x-x0-4));b=max(0,math.floor(y-y0-4));c=min(x1-x0,math.ceil(x+w-x0+4));d=min(y1-y0,math.ceil(y+h-y0+4))
        allowed[b:d,a:c]=True;mask &= allowed
    for x,y,w,h in [*candidate['excluded_text_boxes'],*candidate.get('excluded_decoration_boxes',[])]:
        a=max(0,math.floor(x-x0));b=max(0,math.floor(y-y0));c=min(x1-x0,math.ceil(x+w-x0));d=min(y1-y0,math.ceil(y+h-y0))
        if c>a and d>b:mask[b:d,a:c]=False
    yy,xx=np.nonzero(mask)
    if len(xx)<24:return None
    if seed is None and endpoint_box is not None:
        x,y,w,h=endpoint_box;seed=[x+w/2,y+h/2]
    if seed is not None and candidate.get('kind')!='group':
        # A one-pixel diagonal line is disconnected under 4-neighbour flood fill.
        # Connect only for component labelling, then measure ORIGINAL mask pixels.
        remaining=np.array(Image.fromarray(mask.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(3)))>0
        best=None;best_score=-1
        source=candidate.get('source_boxes',[])
        scale=max(12,min(max(b[2:]) for b in source)/2) if source else 20
        for _ in range(32):
            ry,rx=np.nonzero(remaining)
            if not len(rx):break
            k=int(np.argmin((rx-(seed[0]-x0))**2+(ry-(seed[1]-y0))**2))
            component=Image.fromarray(remaining.astype(np.uint8)*255).copy()
            ImageDraw.floodfill(component,(int(rx[k]),int(ry[k])),128,thresh=0)
            connected=np.array(component)==128;remaining &= ~connected
            cy,cx=np.nonzero(mask&connected)
            if len(cx)<24:continue
            bounds=[int(cx.min()+x0),int(cy.min()+y0),int(cx.max()+x0+1),int(cy.max()+y0+1)]
            if source and any(bounds[j+2]-bounds[j]<min(b[j+2] for b in source)*.3 for j in [0,1]):continue
            distance=math.hypot((bounds[0]+bounds[2])/2-seed[0],(bounds[1]+bounds[3])/2-seed[1])
            score=len(cx)/(1+(distance/scale)**2)
            if score>best_score:best_score=score;best=(cy,cx)
            if source and distance<=scale and all(bounds[j+2]-bounds[j]>=min(b[j+2] for b in source)*.6 for j in [0,1]):break
        if best is None:return None
        yy,xx=best
    return [int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0+1),int(yy.max()+y0+1)]


def analyse_morph(records,first_box,last_box,minimum_poses=10):
    """Contour states and arrival plateau are observed, never interpolated from source timing."""
    result={'status':'pending','issues':[],'distinct_intermediate_poses':0,'settled_seconds':None}
    if not first_box or not last_box:return {**result,'reason':'Endpoint contours unavailable'}
    def near(a,b):return max(abs(x-y) for x,y in zip(a,b))<=4
    visible=[r for r in records if r.get('box')]
    intermediate=[r for r in visible if not near(r['box'],first_box) and not near(r['box'],last_box)]
    distinct=len(set(tuple(r['box']) for r in intermediate));result['distinct_intermediate_poses']=distinct
    widths=[b[2]-b[0] for b in [first_box,last_box]];heights=[b[3]-b[1] for b in [first_box,last_box]]
    invalid=[r for r in intermediate if r['box'][2]-r['box'][0]>max(widths)+10 or r['box'][3]-r['box'][1]>max(heights)+10]
    if invalid:result['issues'].append({'code':'morph-double-image','timestamp':invalid[0]['timestamp'],'severity':'failed','message':'Contour spans both endpoints or exceeds endpoint size envelope; inspect dissolve/double image'})
    if distinct<minimum_poses:
        result['reason']='Insufficient measured intermediate poses; native Morph cannot be certified'
        if invalid:result['status']='failed'
        return result
    dt=float(np.median(np.diff([r['timestamp'] for r in records])))
    valid=[r.get('box') is not None and near(r['box'],last_box) for r in records]
    runs=stable_runs([r['timestamp'] for r in records],valid,minimum=.12)
    if not runs:result['reason']='No observed arrival plateau; local drift phase remains unsegmented';return result
    settle=records[runs[0][0]]['timestamp'];moving=[r for r in visible if r['timestamp']<=settle]
    boxes=np.array([r['box'] for r in moving],dtype=float)
    centers=(boxes[:,:2]+boxes[:,2:])/2
    extent=float(np.linalg.norm((np.array(last_box[:2])+last_box[2:])/2-(np.array(first_box[:2])+first_box[2:])/2))
    step=float(np.max(np.abs(np.diff(centers,axis=0)))) if len(centers)>1 else 0
    gap=max((b['timestamp']-a['timestamp'] for a,b in zip(moving,moving[1:])),default=0)
    threshold=max(24,extent*.1)
    if step>threshold:result['issues'].append({'code':'morph-step','severity':'pending','message':'Large observed Morph center step','step_px':step,'threshold_px':threshold})
    if gap>max(.1,dt*4):result['issues'].append({'code':'capture-gap','severity':'pending','message':'Capture/visibility gap during Morph','seconds':gap})
    result.update(settled_seconds=settle,max_center_step_px=step,center_distance_px=extent,max_capture_gap_seconds=gap,
                  first_box=first_box,last_box=last_box,observed_transition_seconds=[moving[0]['timestamp'],settle])
    result['status']='failed' if any(i['severity']=='failed' for i in result['issues']) else 'pending' if result['issues'] else 'passed'
    return result
