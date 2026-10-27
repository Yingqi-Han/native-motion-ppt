import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {Base,Field,Speaker,useTime,clamp} from './Common';
export const QuestionScene:React.FC=()=>{const f=useCurrentFrame();const {fps}=useVideoConfig();const t=useTime(0);return <Base index={0} title={'声音走了，\n空气也走了吗？'}><Field time={t} opacity={interpolate(f,[.3*fps,1.3*fps],[0,1],clamp)}/><Speaker time={t}/></Base>};
