import React from 'react';
import {useCurrentFrame,useVideoConfig,staticFile,interpolate} from 'remotion';
import {Audio} from '@remotion/media';
import {Base,C,clamp} from './Common';
import {displacement} from './physics';
export const FrequencyScene:React.FC=()=>{
 const f=useCurrentFrame();const {fps}=useVideoConfig();const seconds=f/fps;const t=Math.min(seconds,4);
 const low=seconds>=8&&seconds<8.85;const high=seconds>=10&&seconds<10.85;
 return <Base index={4}><svg width={1920} height={1080} style={{position:'absolute',inset:0}}>
  {[{freq:220,lambda:640,period:4,origin:180,y:465,physical:'1.56 m',active:low},{freq:440,lambda:320,period:2,origin:340,y:715,physical:'0.78 m',active:high}].map(r=><g key={r.freq}>
   <text x={120} y={r.y+15} fontSize={58} fontFamily="LabDisplay" fill={r.active?C.orange:C.cyan}>{r.freq} Hz</text>
   {Array.from({length:26},(_,j)=>{const x=350+j*51;return <g key={j}>{[-18,18].map(dy=><circle key={dy} cx={x+displacement(x,t,25,r.lambda,r.period,r.origin)} cy={r.y+dy} r={7} fill={C.paper}/>)}</g>;})}
   {seconds>=4&&[500,500+r.lambda].map(x=><rect key={x} x={x-14} y={r.y-43} width={28} height={86} fill={C.cyan} opacity={.14}/>)}
   <g opacity={interpolate(f,[4*fps,4.5*fps],[0,1],clamp)}><path d={`M 500 ${r.y+65} v 14 h ${r.lambda} v -14`} fill="none" stroke={C.orange} strokeWidth={3}/><text x={500+r.lambda/2} y={r.y+125} textAnchor="middle" fontSize={36} fill={C.orange} fontFamily="LabSans">λ ≈ {r.physical}</text></g>
   {r.active&&<><path d={`M 120 ${r.y+44} H ${120+180*((seconds-(r.freq===220?8:10))/.85)}`} stroke={C.orange} strokeWidth={5}/><text x={120} y={r.y-67} fontSize={30} fill={C.orange} fontFamily="LabSans">正在播放 · {r.freq===220?'较低':'较高'}</text></>}
  </g>)}
 </svg>
 <div style={{position:'absolute',right:160,top:320,color:C.muted,fontSize:30}}>{seconds<4?'同介质 · 同温度 · 慢放演示':'定格测量波长'}</div>
 <div style={{position:'absolute',left:640,top:850,fontSize:36,color:low||high?C.orange:C.muted,opacity:interpolate(f,[7.1*fps,7.6*fps],[0,1],clamp)}}>{low?'听：220 Hz，音高较低':high?'听：440 Hz，音高较高':'请听两次，比较音高。'}</div>
 <Audio name="220Hz原创纯音" src={staticFile('audio/tone-220.wav')} from={8*fps} premountFor={fps}/>
 <Audio name="440Hz原创纯音" src={staticFile('audio/tone-440.wav')} from={10*fps} premountFor={fps}/>
 </Base>;
};
