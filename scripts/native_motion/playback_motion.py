"""Measurements from captured pixels and PTS; never evaluate the source animation."""
import math
import numpy as np
from PIL import Image,ImageDraw


def intervals(times, active, gap=.22, minimum=.025):
    """Group observed changes, retaining renderer holds rather than filling them."""
    picked=[i for i,value in enumerate(active) if value]
    groups=[]
    for index in picked:
        if not groups or times[index]-times[groups[-1][-1]]>gap:groups.append([index])
        else:groups[-1].append(index)
    return [{"start":times[max(0,g[0]-1)],"end":times[g[-1]],"first_frame":max(0,g[0]-1),
             "last_frame":g[-1],"changed_frames":len(g)} for g in groups
            if times[g[-1]]-times[max(0,g[0]-1)]>=minimum]


def thumbnail_score(actual, reference):
    delta=actual.astype(np.float32)-reference.astype(np.float32)
    square=delta*delta
    h,w=actual.shape[:2]
    tiles=square.reshape(5,h//5,8,w//8,3).mean(axis=(1,3,4))
    return float(np.sqrt(square.mean())),float(np.sqrt(tiles.max()))


def stable_runs(times, valid, minimum=.45):
    runs=[];start=None
    for i,ok in enumerate([*valid,False]):
        if ok and start is None:start=i
        if not ok and start is not None:
            if times[i-1]-times[start]>=minimum:runs.append((start,i-1))
            start=None
    return runs


def foreground_box(frame,background,threshold=38,seed=None,trim_border=0):
    mask=np.max(np.abs(frame.astype(np.int16)-np.array(background,dtype=np.int16)),axis=2)>threshold
    if trim_border:
        mask[:trim_border]=False;mask[-trim_border:]=False
        mask[:,:trim_border]=False;mask[:,-trim_border:]=False
    ys,xs=np.nonzero(mask)
    if len(xs)<16:return None
    if seed is not None:
        nearest=int(np.argmin((xs-seed[0])**2+(ys-seed[1])**2))
        component=Image.fromarray(mask.astype(np.uint8)*255).copy()
        ImageDraw.floodfill(component,(int(xs[nearest]),int(ys[nearest])),128,thresh=0)
        ys,xs=np.nonzero(np.array(component)==128)
        if len(xs)<16:return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],int(len(xs))


def colored_box(frame,color,tolerance=34):
    mask=np.max(np.abs(frame.astype(np.int16)-np.array(color,dtype=np.int16)),axis=2)<=tolerance
    ys,xs=np.nonzero(mask)
    if len(xs)<8:return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],int(len(xs))


def analyse_trace(records,kind="actor",intent="free",max_step=24,noise=.8,pause=.30):
    """Conservative flags. Direction reversals are expected on curved/closed paths."""
    visible=[r for r in records if r.get("box") is not None]
    result={"visible_frames":len(visible),"status":"pending","issues":[],"observed_intervals":[],"kinematics":[]}
    if len(visible)<6:
        result.update(reason="可靠可见帧不足，不能判断运动",reason_code='visibility-insufficient');return result
    times=np.array([r["timestamp"] for r in visible],dtype=float)
    if np.any(np.diff(times)<=0):raise ValueError("Actual timestamps must strictly increase")
    boxes=np.array([r["box"] for r in visible],dtype=float)
    values=np.column_stack(((boxes[:,0]+boxes[:,2])/2,(boxes[:,1]+boxes[:,3])/2,
                            boxes[:,2]-boxes[:,0],boxes[:,3]-boxes[:,1]))
    if kind=="bar":values=np.column_stack((boxes[:,1],boxes[:,3],values[:,2],values[:,3]))
    steps=np.max(np.abs(np.diff(values,axis=0)),axis=1)
    primary=values[:,:1] if kind=="bar" else values[:,:2]
    moved=np.zeros(len(values),dtype=bool);last_pose=primary[0]
    for index,value in enumerate(primary[1:],1):
        if np.max(np.abs(value-last_pose))>noise:moved[index]=True;last_pose=value
    events=intervals(times.tolist(),moved.tolist(),minimum=0)
    result.update(observed_intervals=events,distinct_poses=len(set(map(tuple,values))),
                  max_step_px=float(steps.max()),position_extent_px=np.ptp(values,axis=0).tolist())
    if not events or np.ptp(primary,axis=0).max()<3:
        result.update(reason="录像中没有足够的可测位移；静止画面不能证明动画通过",reason_code='motion-not-observed');return result
    begin,end=events[0]["first_frame"],events[-1]["last_frame"]
    duration=times[end]-times[begin]
    result.update(observed_start=float(times[begin]),observed_end=float(times[end]),observed_duration=float(duration))
    issues=[]
    def issue(code,index,message,suggestion,severity="failed",**extra):
        issues.append({"code":code,"timestamp":float(times[index]),"frame_index":visible[index]["frame_index"],
                       "severity":severity,"message":message,"suggestion":suggestion,**extra})
    gaps=np.diff(times)
    typical=float(np.median(gaps));result["max_capture_gap_seconds"]=float(gaps[begin:end].max())
    if result["max_capture_gap_seconds"]>max(.10,typical*4):
        index=begin+int(np.argmax(gaps[begin:end]))+1
        issue("capture-gap",index,"动作中有采集或可见性缺口，速度结论需复查","先检查录屏负载或遮挡，再重新采集",severity="pending")
    if kind=="bar":
        bottom_error=np.max(np.abs(boxes[:,3]-np.median(boxes[-min(20,len(boxes)):,3])))
        running=np.minimum.accumulate(boxes[:,1]);reversal=boxes[:,1]-running
        result.update(max_bottom_deviation_px=float(bottom_error),max_rebound_px=float(reversal.max()))
        if bottom_error>1:issue("baseline-drift",int(np.argmax(np.abs(boxes[:,3]-np.median(boxes[-20:,3])))),
                               "柱底在展开时偏离到位基线","保留最终几何，改用单一原生擦除；取消中心缩放与补偿位移",deviation_px=float(bottom_error))
        if reversal.max()>1:issue("rebound",int(np.argmax(reversal)),"柱顶出现反向回弹","检查原生擦除方向、缓动及并行动作",deviation_px=float(reversal.max()))
    else:
        if steps.max()>max_step:
            index=int(np.argmax(steps))+1
            severity="pending" if gaps[index-1]>max(.10,typical*4) else "failed"
            issue("position-jump",index,"主体在两个实际采集帧之间跳动过大","延长动作或拆分位移；检查路径衔接与重复入场",severity=severity,step_px=float(steps.max()),threshold_px=max_step)
        size_step=np.max(np.abs(np.diff(values[:,2:],axis=0)))
        result["max_size_step_px"]=float(size_step)
        if size_step>max_step:issue("size-jump",int(np.argmax(np.max(np.abs(np.diff(values[:,2:],axis=0)),axis=1)))+1,
                                    "可见主体尺寸突然改变","检查缩放锚点、遮挡及跨页对象身份",severity="pending",step_px=float(size_step))
        if intent=="linear":
            direction=values[end,:2]-values[begin,:2];length=np.linalg.norm(direction)
            if length>4:
                progress=(values[:,:2]-values[begin,:2])@(direction/length)
                rebound=np.maximum.accumulate(progress)-progress
                result["max_rebound_px"]=float(rebound.max())
                if rebound.max()>2:issue("rebound",int(np.argmax(rebound)),"预定单向移动出现回退","核对并行动作的进度与路径起点",deviation_px=float(rebound.max()))
    # Local least-squares slope over actual PTS, robust to duplicated capture frames.
    dimensions=[0] if kind=="bar" else [0,1]
    slopes=[]
    for index,t in enumerate(times):
        sel=np.abs(times-t)<=.08
        tt=times[sel]-t;vv=values[sel][:,dimensions]
        centered=tt-tt.mean();denom=float(np.sum(centered*centered))
        slope=np.sum(centered[:,None]*(vv-vv.mean(axis=0)),axis=0)/denom if denom>0 else np.zeros(len(dimensions))
        slopes.append(slope)
    slopes=np.array(slopes);speed=np.linalg.norm(slopes,axis=1)
    acceleration=np.linalg.norm(np.gradient(slopes,times,axis=0),axis=1)
    peak=int(np.argmax(speed[begin:end+1]))+begin
    result.update(peak_speed_px_s=float(speed[peak]),peak_acceleration_px_s2=float(acceleration[begin:end+1].max()),peak_frame_index=visible[peak]["frame_index"])
    moving_speed=speed[begin:end+1];positive=moving_speed[moving_speed>2]
    if kind=="actor" and len(positive)>6 and speed[peak]>max(120,float(np.median(positive))*4) and 4<=steps.max()<=max_step:
        issue("speed-burst",peak,"局部速度明显高于其余动作，需回看是否突然加速","检查动作时长与缓动衔接；按设计意图决定是否修正",severity="pending",peak_speed_px_s=float(speed[peak]))
    for index,r in enumerate(visible):
        result["kinematics"].append({"timestamp":float(times[index]),"frame_index":r["frame_index"],
             "x":float(values[index,0]),"y":float(values[index,1]),"width":float(values[index,2]),"height":float(values[index,3]),
             "speed_px_s":float(speed[index]),"acceleration_px_s2":float(acceleration[index])})
    # Interior stalls need visible motion both before and after; easing tails are excluded.
    changed=np.flatnonzero(moved)
    holds=[]
    for a,b in zip(changed,changed[1:]):
        if times[b-1]-times[a]<pause:continue
        left=np.flatnonzero((times>=times[a]-.25)&(times<=times[a]))
        right=np.flatnonzero((times>=times[b-1])&(times<=times[b-1]+.25))
        if not len(left) or not len(right):continue
        before=float(np.max(np.abs(primary[a]-primary[left[0]])));after=float(np.max(np.abs(primary[right[-1]]-primary[b-1])))
        if before>=2 and after>=2:
            holds.append({"start":float(times[a]),"end":float(times[b-1]),"duration":float(times[b-1]-times[a])})
    result["interior_holds"]=holds
    if holds:
        index=int(np.searchsorted(times,holds[0]["start"]))
        issue("interior-hold",index,"动作中途停住后继续移动","对照声明的分步停顿；若非设计停顿，检查播放器重绘与并行动作",severity="pending",duration_seconds=holds[0]["duration"])
    result["issues"]=issues
    for event in events:
        first,last=event["first_frame"],event["last_frame"]
        event.update(first_visible_index=first,last_visible_index=last,
                     first_frame=visible[first]["frame_index"],last_frame=visible[last]["frame_index"])
    result["status"]="failed" if any(x["severity"]=="failed" for x in issues) else "pending" if issues else "passed"
    result["reason"]="按实际像素与时间戳检查跳变、回弹、停顿；速度与加速度为局部拟合值，不是审美评分"
    return result
