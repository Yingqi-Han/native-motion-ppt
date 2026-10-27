import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {Arrow,Base,Field,C,ease,useTime,clamp} from './Common';
export const ParcelScene:React.FC=()=>{const f=useCurrentFrame();const {fps}=useVideoConfig();const s=interpolate(f,[0,1.1*fps],[1,1.85],{...clamp,easing:ease});return <Base index={1}><Field time={useTime(1)} tagOnly transform={`translate(960,600) scale(${s}) translate(-880,-530)`}/><Arrow x={840} y={795} width={240} double color={C.orange} label="局部往复" opacity={interpolate(f,[fps,1.7*fps],[0,1],clamp)}/></Base>};
