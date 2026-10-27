import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {Arrow,Base,Field,C,useTime,clamp} from './Common';
import story from './story.json';
export const ParcelScene:React.FC=()=>{
 const f=useCurrentFrame();const {fps}=useVideoConfig();const duration=story.scenes[1].duration_seconds;
 const visible=interpolate(f,[.8*fps,1.4*fps,(duration-1.3)*fps,(duration-.8)*fps],[0,1,1,0],clamp);
 return <Base index={1}><Field time={useTime(1)}/>
  <svg width={1920} height={1080} style={{position:'absolute',inset:0,opacity:visible}}>
   <path d="M 960 495 V 705" stroke={C.orange} strokeDasharray="6 8" opacity={.45}/>
   <path d="M 916 600 H 1004" stroke={C.orange} strokeWidth={3} opacity={.25}/>
   <text x={960} y={745} textAnchor="middle" fill={C.muted} fontSize={30} fontFamily="LabSans">平衡位置</text>
  </svg>
  <Arrow x={840} y={835} width={240} double color={C.orange} label="局部往复" opacity={visible}/>
 </Base>;
};
