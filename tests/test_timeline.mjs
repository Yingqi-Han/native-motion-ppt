import test from "node:test";
import assert from "node:assert/strict";
import {sampleState,sceneSVG,effectProgress,wipeRect} from "../assets/timeline.mjs";
const effect=(kind,at,duration=100)=>({kind,at,duration,click:0,loop:false,auto_reverse:true,by_letter:false,letter_delay:35,accel:0,decel:0,from:[0,0],to:[0,0]});
const object=(id="subject")=>({id,kind:"rect",box:[0,0,100,100],fill:"4148FF",opacity:1,rotation:0,animations:[]});
test("a future re-entrance does not hide an already visible object",()=>{
 const o=object();o.animations=[effect("enter",0),effect("exit",1000),effect("enter",2000)];
 assert.equal(sampleState(o,500,{clicks:[]}).opacity,1);
 assert.equal(sampleState(o,1500,{clicks:[]}).opacity,0);
 assert.equal(sampleState(o,2050,{clicks:[]}).opacity,.5);
});
test("a delayed scale leaves the initial size intact",()=>{
 const o=object();o.animations=[{...effect("scale",1000),from:[2,2],to:[3,3]}];
 assert.equal(sampleState(o,500,{clicks:[]}).scaleX,1);
});
test("distinct dotted and underscored IDs have distinct gradient IDs",()=>{
 const a=object("a.b"),b=object("a_b");
 for(const o of [a,b])o.gradient={from:"000000",to:"FFFFFF",angle:45};
 const d={canvas:{width:1920,height:1080},slides:[{background:"090B12",duration:3000,transition:{kind:"none",duration:0},clicks:[],objects:[a,b]}]};
 const svg=sceneSVG(d,0,1000),ids=Array.from(svg.matchAll(/linearGradient id="([^"]+)"/g),m=>m[1]);
 assert.equal(new Set(ids).size,2);
});

test("chained cubic motion follows every arc and remains tangent-continuous",()=>{
 const o=object(),k=.5522847498307936;
 o.animations=[{...effect("move",0,4000),path:[[0,0],[k,0],[1,-1+k],[1,-1],[1,-1-k],[k,-2],[0,-2],[-k,-2],[-1,-1-k],[-1,-1],[-1,-1+k],[-k,0],[0,0]]}];
 const state=t=>sampleState(o,t,{clicks:[]});
 for(const [t,expected] of [[0,[0,0]],[1000,[1,-1]],[2000,[0,-2]],[3000,[-1,-1]],[4000,[0,0]]]){
  const s=state(t);assert.ok(Math.hypot(s.x-expected[0],s.y-expected[1])<1e-9);
 }
 for(const t of [1000,2000,3000]){
  const a=state(t-.01),b=state(t),c=state(t+.01);
  assert.ok(Math.hypot((b.x-a.x)-(c.x-b.x),(b.y-a.y)-(c.y-b.y))<1e-8);
 }
});

test("closed cubic cycles have no position or velocity jump at their seam",()=>{
 const o=object(),k=.5522847498307936;
 o.animations=[{...effect("move",0,4000),loop:true,auto_reverse:false,path:[[0,0],[k,0],[1,-1+k],[1,-1],[1,-1-k],[k,-2],[0,-2],[-k,-2],[-1,-1-k],[-1,-1],[-1,-1+k],[-k,0],[0,0]]}];
 const a=sampleState(o,3999,{clicks:[]}),b=sampleState(o,4000,{clicks:[]}),c=sampleState(o,4001,{clicks:[]});
 assert.ok(Math.hypot(b.x,b.y)<1e-12);
 assert.ok(Math.hypot((b.x-a.x)-(c.x-b.x),(b.y-a.y)-(c.y-b.y))<1e-5);
});

test("Morph starts from the outgoing animated pose including its correct local clock",()=>{
 const o=object(),next=object();o.animations=[{...effect("move",0,1000),to:[100,40]},{...effect("rotate",0,1000),degrees:20}];
 const slide=(objects,duration=1000)=>({background:"090B12",duration,transition:{kind:"morph",duration:400},clicks:[],objects});
 const d={canvas:{width:1920,height:1080},slides:[slide([]),slide([o]),slide([next])]};
 // The middle slide spent 400ms in its incoming transition: outgoing local time is 600ms.
 const before=sceneSVG(d,1,1000),after=sceneSVG(d,2,0);
 const transform=svg=>svg.match(/data-object="subject"[^>]*transform="([^"]+)"/)[1];
 assert.equal(transform(after),transform(before));
 assert.match(transform(after),/translate\(60 24\)/);
 assert.match(transform(after),/rotate\(12\)/);
});

test("Morph hands off to incoming animation without a jump",()=>{
 const a=object(),b=object();a.animations=[{...effect("scale",0,100),from:[1,1],to:[2,2]}];
 b.animations=[{...effect("move",0,500),to:[10,0]}];
 const d={canvas:{width:1920,height:1080},slides:[{background:"090B12",duration:1000,transition:{kind:"none",duration:0},clicks:[],objects:[a]},{background:"090B12",duration:1000,transition:{kind:"morph",duration:400},clicks:[],objects:[b]}]};
 const transform=svg=>svg.match(/data-object="subject"[^>]*transform="([^"]+)"/)[1];
 assert.equal(transform(sceneSVG(d,1,400)),transform(sceneSVG(d,1,0,false)));
 const near=transform(sceneSVG(d,1,399.999));
 assert.ok(Number(near.match(/scale\(([^ ]+)/)[1])-1<1e-8);
});

test("paired native scale and translation keep a bar on its data baseline",()=>{
 const o=object();o.box=[200,300,100,400];
 o.animations=[{...effect("enter",100,950),from:[0,188],accel:.1,decel:.65},
               {...effect("scale",100,950),from:[1,.06],to:[1,1],accel:.1,decel:.65}];
 for(const t of [100,101,180,360,600,900,1050,1400]){
  const st=sampleState(o,t,{clicks:[]});
  const bottom=o.box[1]+o.box[3]/2+o.box[3]/2*st.scaleY+st.y;
  assert.ok(Math.abs(bottom-700)<1e-9,`baseline moved at ${t}`);
 }
});

test("bottom wipe never transforms the bar and clips only inside its fixed geometry",()=>{
 const o=object();o.box=[200,300,100,400];
 o.animations=[{...effect("enter",100,1000),effect:"wipe",direction:"up"}];
 for(const t of [0,100,101,250,600,999,1100,1600]){
  const st=sampleState(o,t,{clicks:[]});
  assert.equal(st.y,0);assert.equal(st.x,0);assert.equal(st.scaleX,1);assert.equal(st.scaleY,1);
  const clip=wipeRect(o,t,{clicks:[]});
  if(clip){assert.ok(Math.abs(clip[1]+clip[3]-400)<1e-9);assert.ok(clip[3]>=0&&clip[3]<=400);}
 }
 assert.equal(sampleState(o,99,{clicks:[]}).opacity,0);
 assert.deepEqual(wipeRect(o,600,{clicks:[]}),[0,200,100,200]);
});

test("directional wipe rectangles stay within the source bounds",()=>{
 const o=object();o.box=[20,30,160,90];
 for(const direction of ["up","down","left","right"]){
  o.animations=[{...effect("enter",0,1000),effect:"wipe",direction}];
  const c=wipeRect(o,500,{clicks:[]});
  assert.ok(c[0]>=0&&c[1]>=0&&c[0]+c[2]<=160&&c[1]+c[3]<=90);
 }
});

test("a wipe exit leaves the correct remainder and finishes hidden",()=>{
 const o=object();o.animations=[{...effect("exit",0,1000),effect:"wipe",direction:"up"}];
 assert.deepEqual(wipeRect(o,500,{clicks:[]}),[0,0,100,50]);
 assert.equal(sampleState(o,1000,{clicks:[]}).opacity,0);
});

