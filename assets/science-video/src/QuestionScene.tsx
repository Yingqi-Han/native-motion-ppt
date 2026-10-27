import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {Base,Field,Speaker,useTime,clamp,useCueStart} from './Common';
import story from './story.json';
export const QuestionScene:React.FC=()=>{
 const f=useCurrentFrame();const {fps}=useVideoConfig();const t=useTime(0);const end=story.scenes[0].duration_seconds;const cue=useCueStart(0,1);
 return <Base index={0} title={'声音走了，\n空气也走了吗？'}>
  <Field time={t} opacity={interpolate(f,[.3*fps,1.3*fps],[0,1],clamp)}/>
  <div style={{opacity:interpolate(f,[0,.5*fps,(end-.7)*fps,(end-.15)*fps],[0,1,1,0],clamp)}}><Speaker time={t}/></div>
  <div style={{position:'absolute',left:700,top:780,fontSize:36,color:'#FFAC4B',opacity:interpolate(f,[cue*fps,(cue+.4)*fps,(end-.7)*fps,(end-.2)*fps],[0,1,1,0],clamp)}}>只跟踪这个橙色标记。</div>
 </Base>;
};
