import React from 'react';
import {useCurrentFrame,useVideoConfig,staticFile} from 'remotion';
import {Audio} from '@remotion/media';
import {Base,C} from './Common';
import {displacement} from './physics';
export const FrequencyScene:React.FC=()=>{const f=useCurrentFrame();const {fps}=useVideoConfig();const t=Math.min(f/fps,4);return <Base index={4}><svg width={1920} height={1080} style={{position:'absolute',inset:0}}>
 {[{freq:220,lambda:640,period:4,origin:180,y:465,physical:'1.56 m'},{freq:440,lambda:320,period:2,origin:340,y:715,physical:'0.78 m'}].map((r,i)=><g key={r.freq}>
  <text x={120} y={r.y+15} fontSize={58} fontFamily="LabDisplay" fill={(i===0&&f>=8*fps&&f<9*fps)||(i===1&&f>=10*fps&&f<11*fps)?C.orange:C.cyan}>{r.freq} Hz</text>
  {Array.from({length:26},(_,j)=>{const x=350+j*51;return <g key={j}>{[-18,18].map(dy=><circle key={dy} cx={x+displacement(x,t,25,r.lambda,r.period,r.origin)} cy={r.y+dy} r={7} fill={C.paper}/>)}</g>;})}
  {f>4.2*fps&&<g><path d={`M 500 ${r.y+65} v 14 h ${r.lambda} v -14`} fill="none" stroke={C.orange} strokeWidth={3}/><text x={500+r.lambda/2} y={r.y+125} textAnchor="middle" fontSize={36} fill={C.orange} fontFamily="LabSans">λ ≈ {r.physical}</text></g>}
 </g>)}
 </svg>{f>4.2*fps&&<div style={{position:'absolute',right:160,top:340,color:C.orange,fontSize:30}}>定格测量波长</div>}<Audio name="220Hz原创纯音" src={staticFile('audio/tone-220.wav')} from={8*fps} premountFor={fps}/><Audio name="440Hz原创纯音" src={staticFile('audio/tone-440.wav')} from={10*fps} premountFor={fps}/></Base>};
