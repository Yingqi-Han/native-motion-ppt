import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {Base,Field,Arrow,C,useTime,clamp} from './Common';
export const RecapScene:React.FC=()=>{
 const f=useCurrentFrame();const {fps}=useVideoConfig();
 return <Base index={6}><Field time={useTime(6)} showBands/>
  <Arrow x={750} y={355} width={260} double color={C.orange} label="空气：局部往复"/>
  <Arrow x={450} y={840} width={1050} label="声波：向外传递能量" opacity={interpolate(f,[.5*fps,1.2*fps],[0,1],clamp)}/>
 </Base>;
};
