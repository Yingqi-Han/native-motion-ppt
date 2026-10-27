import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {Base,Field,Arrow,useTime,C,clamp,useCueStart} from './Common';
export const ParallelScene:React.FC=()=>{
 const f=useCurrentFrame();const {fps}=useVideoConfig();const answer=useCueStart(3,1);
 return <Base index={3}><Field time={useTime(3)} unmarkedOpacity={interpolate(f,[0,.7*fps],[.88,.45],clamp)}/>
  <Arrow x={700} y={360} width={360} double color={C.orange} label="空气振动" opacity={interpolate(f,[.3*fps,1*fps],[0,1],clamp)}/>
  <Arrow x={440} y={815} width={1060} label="声波传播" opacity={interpolate(f,[1.3*fps,2*fps],[0,1],clamp)}/>
  <div style={{position:'absolute',left:1320,top:430,width:350,padding:'22px 24px',background:C.bg,border:`1px solid ${C.line}`,borderRadius:18,textAlign:'center',fontSize:96,color:C.paper,fontWeight:700,opacity:interpolate(f,[answer*fps,(answer+.5)*fps],[0,1],clamp)}}>纵波<div style={{fontSize:32,color:C.cyan,marginTop:8}}>振动 ∥ 传播</div></div>
 </Base>;
};
