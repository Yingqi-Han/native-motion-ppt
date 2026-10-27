import React from 'react';
import {AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/fonts';
import {Audio} from '@remotion/media';
import type {Caption} from '@remotion/captions';
import story from './story.json';
import captions from './captions.json';
import {cameraAt,compressionCenters,displacement} from './physics';

loadFont({family:'LabSans',url:staticFile('NotoSansSC-Regular.woff'),weight:'400'});
loadFont({family:'LabSans',url:staticFile('NotoSansSC-Bold.woff'),weight:'700'});
loadFont({family:'LabDisplay',url:staticFile('SpaceGrotesk-SemiBold.ttf'),weight:'600'});
export const C={bg:'#0B1930',paper:'#F5F2E8',muted:'#A7B6C8',cyan:'#6CE2D0',orange:'#FFAC4B',line:'#29415C'};
export const ease=Easing.bezier(.16,1,.3,1);
export const clamp={extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};
export const sceneTimes=story.scenes.map((_,i)=>story.scenes.slice(0,i).reduce((n,s)=>n+s.duration_seconds,0));
export const useTime=(index:number) => useCurrentFrame()/useVideoConfig().fps+sceneTimes[index];
export const useCueStart=(index:number,cue:number) => ((captions as Record<string,Caption[]>)[story.scenes[index].id]?.[cue]?.startMs??600)/1000;

export const Base:React.FC<{index:number;children:React.ReactNode;title?:string}> = ({index,children,title}) => {
 const frame=useCurrentFrame();const {fps}=useVideoConfig();const s=story.scenes[index];
 const rows=(captions as Record<string,Caption[]>)[s.id]??[];
 const caption=rows.find(c=>c.startMs<=frame/fps*1000&&c.endMs>frame/fps*1000)?.text??'';
 const globalSeconds=sceneTimes[index]+frame/fps;
 const totalSeconds=story.scenes.reduce((n,s)=>n+s.duration_seconds,0);
 return <AbsoluteFill style={{background:C.bg,color:C.paper,fontFamily:'LabSans',overflow:'hidden'}}>
  <div style={{position:'absolute',inset:0,opacity:.09,backgroundImage:'radial-gradient(#496380 1px,transparent 1px)',backgroundSize:'38px 38px'}}/>
  <div style={{position:'absolute',left:120,top:65,fontFamily:'LabDisplay',fontSize:25,letterSpacing:4,color:C.cyan}}>SOUND / 看见声音</div>
  <div style={{position:'absolute',right:120,top:65,fontFamily:'LabDisplay',fontSize:25,color:C.muted}}>{String(index+1).padStart(2,'0')} / 08</div>
  {title!==''&&<div data-main-title style={{position:'absolute',left:120,top:170,right:120,fontSize:80,fontWeight:700,lineHeight:1.18,whiteSpace:'pre-line',zIndex:3,opacity:interpolate(frame,[0,.6*fps],[0,1],{...clamp,easing:ease}),translate:`0px ${interpolate(frame,[0,.7*fps],[24,0],{...clamp,easing:ease})}px`}}>{title??s.title}</div>}
  {children}
  <div style={{position:'absolute',left:0,right:0,bottom:0,height:170,background:`linear-gradient(transparent,${C.bg} 32%)`,pointerEvents:'none'}}/>
  <div data-caption style={{position:'absolute',left:150,right:150,top:930,minHeight:65,fontSize:42,textAlign:'center',lineHeight:1.35,whiteSpace:'pre-line',color:C.paper}}>{caption}</div>
  <div style={{position:'absolute',left:120,bottom:24,fontSize:20,color:C.muted}}>平均运动示意 · 位移与时间已放大 · 未画热运动</div>
  <div style={{position:'absolute',right:120,bottom:24,fontFamily:'LabDisplay',fontSize:20,color:C.muted}}>声波实验室</div>
  <div data-film-progress style={{position:'absolute',bottom:0,left:0,height:4,background:C.cyan,width:1920*globalSeconds/totalSeconds}}/>
  {index<7&&<Audio name={`${s.id}中文解说`} src={staticFile(`audio/${s.id}.wav`)} from={.6*fps} premountFor={fps} volume={.92}/>}
 </AbsoluteFill>;
};

export const Field:React.FC<{time:number;showBands?:boolean;opacity?:number;transform?:string;tagOnly?:boolean;unmarkedOpacity?:number}>=({time,showBands=false,opacity=1,transform,unmarkedOpacity}) => {
 const m=story.model;
 const tagX=m.origin_x+m.tagged_column*m.parcel_spacing_px;
 const tagY=m.origin_y+m.tagged_row*m.row_spacing_px;
 const camera=cameraAt(time,sceneTimes[1],sceneTimes[2]);
 return <svg data-field width={1920} height={1080} style={{position:'absolute',inset:0,opacity}}>
  <defs><clipPath id="field-clip"><rect x={150} y={355} width={1620} height={530}/></clipPath>
   <linearGradient id="pressure-glow"><stop stopColor={C.cyan} stopOpacity={0}/><stop offset=".5" stopColor={C.cyan} stopOpacity={.15}/><stop offset="1" stopColor={C.cyan} stopOpacity={0}/></linearGradient></defs>
  <g clipPath="url(#field-clip)"><g transform={transform??`translate(${camera.tx},${camera.ty}) scale(${camera.scale})`}>
   {showBands&&compressionCenters(time).map((x,i)=><g key={i}><rect x={x-64} y={375} width={128} height={380} fill="url(#pressure-glow)"/><path d={`M ${x} 366 l -10 -18 h 20 Z`} fill={C.cyan}/></g>)}
   {Array.from({length:m.rows},(_,row)=>Array.from({length:m.columns},(_,col)=>{
    const x0=m.origin_x+col*m.parcel_spacing_px;const y=m.origin_y+row*m.row_spacing_px;
    const tagged=row===m.tagged_row&&col===m.tagged_column;
    return <circle data-parcel={`${row}-${col}`} data-tagged-parcel={tagged||undefined} key={`${row}-${col}`} cx={x0+displacement(x0,time)} cy={y} r={tagged?11:6.8} fill={tagged?C.orange:C.paper} opacity={tagged?.88:unmarkedOpacity??(.88-.64*camera.focus)}/>;
   }))}
   <line x1={tagX} y1={tagY-48} x2={tagX} y2={tagY+48} stroke={C.orange} strokeDasharray="5 8" opacity={.7}/>
   <circle cx={tagX+displacement(tagX,time)} cy={tagY} r={20} fill="none" stroke={C.orange} strokeWidth={2.2}/>
  </g></g>
 </svg>;
};

export const Arrow:React.FC<{x:number;y:number;width:number;color?:string;double?:boolean;label?:string;opacity?:number}>=({x,y,width,color=C.cyan,double=false,label,opacity=1}) => <svg width={1920} height={1080} style={{position:'absolute',inset:0,opacity}}>
 <path d={`M ${x} ${y} H ${x+width}`} fill="none" stroke={color} strokeWidth={4}/>
 <path d={`M ${x+width-17} ${y-10} L ${x+width} ${y} L ${x+width-17} ${y+10}`} fill="none" stroke={color} strokeWidth={4}/>
 {double&&<path d={`M ${x+17} ${y-10} L ${x} ${y} L ${x+17} ${y+10}`} fill="none" stroke={color} strokeWidth={4}/>}
 {label&&<text x={x+width/2} y={y-30} textAnchor="middle" fill={color} fontSize={40} fontFamily="LabSans">{label}</text>}
</svg>;

export const Speaker:React.FC<{time:number}>=({time})=><svg width={1920} height={1080} style={{position:'absolute',inset:0}}><g transform={`translate(${Math.sin(time*Math.PI*2/3)*9},0)`}><path d="M 130 505 H 186 L 251 452 V 648 L 186 595 H 130 Z" fill={C.cyan}/><path d="M 279 486 Q 330 550 279 614" fill="none" stroke={C.cyan} strokeWidth={5} opacity={.65}/></g></svg>;
