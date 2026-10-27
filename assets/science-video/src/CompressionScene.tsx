import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {Base,Field,Arrow,useTime,C,sceneTimes,clamp} from './Common';
export const CompressionScene:React.FC=()=>{
 const f=useCurrentFrame();const {fps}=useVideoConfig();const t=useTime(2);
 const start=sceneTimes[2];const phase=(start/3)%1;
 const first=340+480*(phase+.5);const x=first+160*(t-start);
 const opacity=interpolate(f,[0,.5*fps,6.5*fps,7*fps],[0,1,1,0],clamp);
 return <Base index={2}><Field time={t} showBands/>
  <svg width={1920} height={1080} style={{position:'absolute',inset:0,opacity}}>
   <defs><linearGradient id="follow-pressure"><stop stopColor={C.cyan} stopOpacity="0"/><stop offset=".5" stopColor={C.cyan} stopOpacity=".28"/><stop offset="1" stopColor={C.cyan} stopOpacity="0"/></linearGradient></defs>
   <rect x={x-58} y={385} width={116} height={355} fill="url(#follow-pressure)"/>
   <path d={`M ${x} 380 l -12 -20 h 24 Z`} fill={C.cyan}/>
   <text x={Math.min(1580,x)} y={335} textAnchor="middle" fill={C.cyan} fontSize={32} fontFamily="LabSans">跟踪压缩区 →</text>
  </svg>
  <Arrow x={420} y={835} width={1100} label="疏密变化向右传播" opacity={interpolate(f,[.5*fps,1.2*fps],[0,1],clamp)}/>
 </Base>;
};
