import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {Base,C,ease,clamp,Arrow,useCueStart} from './Common';
export const WavelengthScene:React.FC=()=>{
 const f=useCurrentFrame();const {fps}=useVideoConfig();const formula=useCueStart(5,1);const numbers=useCueStart(5,2);
 return <Base index={5}>
  <div style={{position:'absolute',left:130,top:340,fontSize:46,color:C.muted}}>20°C 空气 · v ≈ 343 m/s</div>
  <div style={{position:'absolute',left:130,top:480,fontSize:84,fontFamily:'LabDisplay',color:C.cyan,opacity:interpolate(f,[formula*fps,(formula+.45)*fps],[0,1],clamp)}}>λ = v / f</div>
  <div style={{position:'absolute',left:130,top:610,fontSize:70,fontFamily:'LabDisplay',opacity:interpolate(f,[numbers*fps,(numbers+.5)*fps],[0,1],clamp)}}>343 / 440</div>
  <div style={{position:'absolute',left:900,top:450,fontSize:180,fontWeight:700,color:C.orange,opacity:interpolate(f,[(numbers+1.6)*fps,(numbers+2.2)*fps],[0,1],{...clamp,easing:ease}),scale:interpolate(f,[(numbers+1.6)*fps,(numbers+2.2)*fps],[.94,1],{...clamp,easing:ease})}}>0.78<span style={{fontSize:80}}> 米</span></div>
  <svg width={1920} height={1080} style={{position:'absolute',inset:0,opacity:interpolate(f,[(numbers+2.2)*fps,(numbers+2.7)*fps],[0,1],clamp)}}>{[900,1640].map(x=><g key={x}><rect x={x-17} y={700} width={34} height={140} fill={C.cyan} opacity={.17}/><text x={x} y={880} textAnchor="middle" fontSize={28} fill={C.cyan} fontFamily="LabSans">压缩区</text></g>)}</svg>
  <Arrow x={900} y={780} width={740} double color={C.cyan} label="相邻压缩区之间，一个波长" opacity={interpolate(f,[(numbers+2.2)*fps,(numbers+2.7)*fps],[0,1],clamp)}/>
 </Base>;
};
