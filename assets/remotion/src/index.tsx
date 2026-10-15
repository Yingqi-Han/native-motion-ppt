import React,{useEffect,useState} from "react";
import {AbsoluteFill,Composition,Folder,registerRoot,useCurrentFrame,useVideoConfig,delayRender,continueRender,cancelRender,staticFile} from "remotion";
import {loadFont} from "@remotion/fonts";
import doc from "./document.json";
import fonts from "./fonts.json";
import {renderFrame,sceneSVG} from "./timeline.mjs";

const loaded=Promise.all(fonts.map(font=>loadFont({family:font.family,url:staticFile(font.file),weight:font.weight})));
type Props={document:typeof doc;scene?:number};
const Motion:React.FC<Props>=({document,scene})=>{
 const frame=useCurrentFrame(),{fps}=useVideoConfig();
 const [handle]=useState(()=>delayRender("Load project fonts"));
 useEffect(()=>{loaded.then(()=>continueRender(handle)).catch(cancelRender);},[handle]);
 const svg=scene===undefined?renderFrame(document,frame/fps*1000):sceneSVG(document,scene,frame/fps*1000,false);
 return <AbsoluteFill style={{background:"#090b12"}}><div style={{width:"100%",height:"100%"}} dangerouslySetInnerHTML={{__html:svg}}/></AbsoluteFill>;
};
// The JSON document intentionally owns all generated scene registrations.
const Root:React.FC=()=>(
 <>
 <Composition id="NativeMotion" component={Motion} width={1920} height={1080} fps={60} durationInFrames={900}
  defaultProps={{document:doc}}
  calculateMetadata={({props})=>({width:props.document.canvas.width,height:props.document.canvas.height,fps:props.document.canvas.fps,durationInFrames:Math.round(props.document.slides.reduce((n,s)=>n+s.duration,0)/1000*props.document.canvas.fps)})}/>
 <Folder name="Scenes">
 {doc.slides.map((s,i)=><Composition key={s.id} id={`Scene${String(i+1).padStart(2,"0")}`} component={Motion}
 width={doc.canvas.width} height={doc.canvas.height} fps={doc.canvas.fps} durationInFrames={Math.round(s.duration/1000*doc.canvas.fps)}
 defaultProps={{document:doc,scene:i}}/>)}
 </Folder>
 </>
);
registerRoot(Root);

