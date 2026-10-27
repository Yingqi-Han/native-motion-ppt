/** Shared deterministic preview timeline. No CSS animation or media. */
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"}[c]));
const clamp=x=>Math.max(0,Math.min(1,x));
const mix=(a,b,p)=>a+(b-a)*p;
const rgb=(a,b,p)=>[0,2,4].map(i=>Math.round(mix(parseInt(a.slice(i,i+2),16),parseInt(b.slice(i,i+2),16),p)).toString(16).padStart(2,"0")).join("");
export function ease(t,a=.1,d=.65){
 t=clamp(t);const v=1/(1-(a+d)/2);
 if(a&&t<a)return v*t*t/(2*a);
 if(d&&t>1-d)return 1-v*(1-t)*(1-t)/(2*d);
 return v*(t-a/2);
}
export function effectProgress(e,t,s,letter=0){
 const start=(e.click?s.clicks[e.click-1]:0)+e.at+letter*e.letter_delay;
 let p=(t-start)/e.duration;
 if(e.loop&&p>0){p=e.auto_reverse?p%2:p%1;if(e.auto_reverse&&p>1)p=2-p;}
 return ease(p,e.accel,e.decel);
}
function pathPoint(e,p){
 const points=e.path||[e.from||(e.kind==="enter"?[0,60]:[0,0]),e.to||[0,0]];
 if(points.length===2)return points[0].map((v,i)=>mix(v,points[1][i],p));
 const count=(points.length-1)/3,segment=Math.min(count-1,Math.floor(p*count));
 const u=p*count-segment,q=1-u,offset=segment*3;
 return [0,1].map(i=>q*q*q*points[offset][i]+3*q*q*u*points[offset+1][i]+3*q*u*u*points[offset+2][i]+u*u*u*points[offset+3][i]);
}
export function sampleState(o,t,s,letter=null){
 const st={x:0,y:0,rotation:o.rotation,scaleX:1,scaleY:1,opacity:o.opacity};
 const effects=o.animations.filter(e=>letter===null?!e.by_letter:e.by_letter);
 const startsAt=e=>(e.click?s.clicks[e.click-1]:0)+e.at+(letter??0)*e.letter_delay;
 const fades=effects.filter(e=>e.kind==="enter"||e.kind==="exit").sort((a,b)=>startsAt(a)-startsAt(b));
 if(fades[0]?.kind==="enter"&&t<startsAt(fades[0]))st.opacity=0;
 for(const e of [...effects].sort((a,b)=>startsAt(a)-startsAt(b))){
  const p=effectProgress(e,t,s,letter??0);
  const starts=(e.click?s.clicks[e.click-1]:0)+e.at+(letter??0)*e.letter_delay;
  if((e.kind==="enter"||e.kind==="exit")&&t>=starts){
   const alpha=e.effect==="wipe"?(e.kind==="enter"?1:p<1?1:0):(e.kind==="enter"?p:1-p);
   st.opacity=o.opacity*alpha;
  }
  if(["enter","exit","move"].includes(e.kind)&&t>=starts){
   const pt=pathPoint(e,p);st.x+=pt[0];st.y+=pt[1];
  }
  if(e.kind==="rotate")st.rotation+=(e.degrees??4)*p;
  if(e.kind==="scale"&&t>=starts){
   const a=e.from||[1,1],b=e.to||[1.08,1.08];st.scaleX*=mix(a[0],b[0],p);st.scaleY*=mix(a[1],b[1],p);
  }
 }
 return st;
}
export function wipeRect(o,t,s){
 const start=e=>(e.click?s.clicks[e.click-1]:0)+e.at;
 const e=o.animations.filter(e=>["enter","exit"].includes(e.kind)&&t>=start(e)).sort((a,b)=>start(a)-start(b)).at(-1);
 if(e?.effect!=="wipe")return null;
 let p=effectProgress(e,t,s),direction=e.direction||"up";
 if(e.kind==="exit"){
  p=1-p;direction=({up:"down",down:"up",left:"right",right:"left"})[direction];
 }
 const [, ,w,h]=o.box;
 return ({up:[0,h*(1-p),w,h*p],down:[0,0,w,h*p],left:[w*(1-p),0,w*p,h],right:[0,0,w*p,h]})[direction];
}
function morphObject(a,b,p){
 if(!a||a.kind!==b.kind)return b;
 const n={...b,box:b.box.map((v,i)=>mix(a.box[i],v,p)),rotation:mix(a.rotation,b.rotation,p)};
 if(b.fill!=="none"&&a.fill!=="none")n.fill=rgb(a.fill,b.fill,p);
 if(b.points&&a.points&&b.points.length===a.points.length)n.points=b.points.map((pt,i)=>pt.map((v,j)=>mix(a.points[i][j],v,p)));
 if(b.kind==="group"){
  const old=new Map(a.objects.map(o=>[o.id,o]));n.objects=b.objects.map(o=>morphObject(old.get(o.id),o,p));
 }
 if(b.kind==="text"){n.size=mix(a.size,b.size,p);n.spacing=mix(a.spacing,b.spacing,p);}
 if(b.kind==="text")n.advances=b.advances.map(v=>v*n.size/b.size);
 if(b.commands&&a.commands&&b.commands.length===a.commands.length&&b.commands.every((c,i)=>c.op===a.commands[i].op)){
  n.commands=b.commands.map((c,i)=>({...c,points:c.points.map((pt,j)=>pt.map((v,k)=>mix(a.commands[i].points[j][k],v,p)))}));
  n.d=n.commands.map(c=>c.op+" "+c.points.flat().join(" ")).join(" ");
 }
 if(b.gradient&&a.gradient)n.gradient={...b.gradient,from:rgb(a.gradient.from,b.gradient.from,p),to:rgb(a.gradient.to,b.gradient.to,p),angle:mix(a.gradient.angle,b.gradient.angle,p)};
 return n;
}
function objectSVG(o,t,s,prefix,state=null,clipOverride=undefined){
 const [x,y,w,h]=o.box,st=state||sampleState(o,t,s),cx=x+w/2,cy=y+h/2;
 const transform=`translate(${st.x} ${st.y}) translate(${cx} ${cy}) rotate(${st.rotation}) scale(${st.scaleX} ${st.scaleY}) translate(${-cx} ${-cy})`;
 const gid="g_"+[prefix,o.id].map(p=>Array.from(p).map(c=>c.codePointAt(0).toString(16)).join("_")).join("__");
 let fill=o.fill==="none"?"none":"#"+o.fill,defs="";
 if(o.gradient){
  const ang=o.gradient.angle*Math.PI/180,dx=Math.cos(ang)/2,dy=Math.sin(ang)/2;
  defs=`<defs><linearGradient id="${gid}" x1="${.5-dx}" y1="${.5-dy}" x2="${.5+dx}" y2="${.5+dy}"><stop stop-color="#${o.gradient.from}"/><stop offset="1" stop-color="#${o.gradient.to}"/></linearGradient></defs>`;
  fill=`url(#${gid})`;
 }
 const clip=clipOverride===undefined?wipeRect(o,t,s):clipOverride;
 const clipId=gid+"_wipe";
 if(clip)defs+=`<defs><clipPath id="${clipId}" clipPathUnits="userSpaceOnUse"><rect data-wipe-clip="${esc(o.id)}" x="${clip[0]}" y="${clip[1]}" width="${clip[2]}" height="${clip[3]}"/></clipPath></defs>`;
 const attrs=`fill="${fill}" stroke="${o.stroke?"#"+o.stroke:"none"}" stroke-width="${o.stroke_width??2}"`;
 let body="";
 if(o.kind==="group")body=o.objects.map(c=>objectSVG(c,0,{clicks:[]},prefix+o.id)).join("");
 if(o.kind==="rect")body=`<rect width="${w}" height="${h}" rx="${Math.min(o.radius??0,w/2,h/2)}" ${attrs}/>`;
 if(o.kind==="line")body=`<line x1="0" y1="0" x2="${w}" y2="${h}" stroke="#${o.stroke||o.fill}" stroke-width="${o.stroke_width??2}"/>`;
 if(o.kind==="ellipse")body=`<ellipse cx="${w/2}" cy="${h/2}" rx="${w/2}" ry="${h/2}" ${attrs}/>`;
 if(o.kind==="polygon")body=`<polygon points="${o.points.map(p=>p.join(",")).join(" ")}" ${attrs}/>`;
 if(o.kind==="path")body=`<path d="${esc(o.d)}" ${attrs}/>`;
 if(o.kind==="text"){
  const textAttrs=`font-family="${esc(o.font)}" font-size="${o.size}" font-weight="${o.bold?700:400}" fill="${fill}" letter-spacing="${o.spacing}"`;
  if(o.animations.some(e=>e.by_letter)){
   const width=o.advances.reduce((a,b)=>a+b,0)+o.spacing*(o.text.length-1);
   let cursor=o.align==="center"?(w-width)/2:o.align==="right"?w-width:0;
   body=Array.from(o.text).map((ch,i)=>{
    const cst=sampleState(o,t,s,i);
    const node=`<text data-letter="${i}" x="${cursor+cst.x}" y="${o.size*.99+cst.y}" opacity="${cst.opacity/o.opacity||0}" ${textAttrs}>${esc(ch)}</text>`;
    cursor+=o.advances[i]+o.spacing;return node;
   }).join("");
  }else{
   body=o.text.split("\n").map((line,i)=>`<text x="${o.align==="center"?w/2:o.align==="right"?w:0}" y="${o.size*.99+i*o.size*o.line_height}" text-anchor="${o.align==="center"?"middle":o.align==="right"?"end":"start"}" ${textAttrs}>${esc(line)}</text>`).join("");
  }
 }
 return `<g data-object="${esc(o.id)}" opacity="${st.opacity}" transform="${transform}">${defs}<g transform="translate(${x} ${y})"><g${clip?` clip-path="url(#${clipId})"`:""}>${body}</g></g></g>`;
}
export function sceneSVG(doc,index,time,transition=true){
 const s=doc.slides[index],prev=doc.slides[index-1],tr=s.transition;
 const p=index&&transition&&tr.duration?ease(time/tr.duration):1;
 const local=Math.max(0,time-(index&&transition?tr.duration:0));
 const previousTime=prev?prev.duration-(index>1?prev.transition.duration:0):0;
 let bg=s.background,body="",objects=s.objects;
 if(prev&&p<1&&tr.kind==="morph"){
  bg=rgb(prev.background,s.background,p);
  const old=new Map(prev.objects.map(o=>[o.id,o])),newIds=new Set(objects.map(o=>o.id));
  body+=`<g opacity="${1-p}">${prev.objects.filter(o=>!newIds.has(o.id)).map(o=>objectSVG(o,previousTime,prev,"old")).join("")}</g>`;
  for(const target of objects){
   const source=old.get(target.id),matched=source?.kind===target.kind;
   const o=matched?morphObject(source,target,p):target;
   let state=null,clip=undefined;
   if(matched){
    const a=sampleState(source,previousTime,prev),b=sampleState(target,0,s);
    state=Object.fromEntries(Object.keys(a).map(k=>[k,mix(a[k],b[k],p)]));
    const ac=wipeRect(source,previousTime,prev),bc=wipeRect(target,0,s);
    if(ac||bc){
     const normalized=(c,obj)=>(c||[0,0,obj.box[2],obj.box[3]]).map((v,i)=>v/obj.box[2+i%2]);
     const from=normalized(ac,source),to=normalized(bc,target);
     clip=from.map((v,i)=>mix(v,to[i],p)*o.box[2+i%2]);
    }
   }
   body+=`<g opacity="${matched?1:p}">${objectSVG(o,local,s,"new",state,clip)}</g>`;
  }
 }else if(prev&&p<1&&tr.kind!=="none"){
  const oldBody=prev.objects.map(o=>objectSVG(o,previousTime,prev,"old")).join("");
  const newBody=objects.map(o=>objectSVG(o,local,s,"new")).join("");
  const oldScene=`<rect width="${doc.canvas.width}" height="${doc.canvas.height}" fill="#${prev.background}"/>${oldBody}`;
  const newScene=`<rect width="${doc.canvas.width}" height="${doc.canvas.height}" fill="#${s.background}"/>${newBody}`;
  if(tr.kind==="push"){
   const [dx,dy]=({l:[-doc.canvas.width,0],r:[doc.canvas.width,0],u:[0,-doc.canvas.height],d:[0,doc.canvas.height]})[tr.direction];
   body=`<g transform="translate(${dx*p} ${dy*p})">${oldScene}</g><g transform="translate(${dx*(p-1)} ${dy*(p-1)})">${newScene}</g>`;
  }else if(tr.kind==="wipe"){
   const w=doc.canvas.width,h=doc.canvas.height;
   const box=({l:[w*(1-p),0,w*p,h],r:[0,0,w*p,h],u:[0,h*(1-p),w,h*p],d:[0,0,w,h*p]})[tr.direction];
   body=oldScene+`<defs><clipPath id="wipe"><rect x="${box[0]}" y="${box[1]}" width="${box[2]}" height="${box[3]}"/></clipPath></defs><g clip-path="url(#wipe)">${newScene}</g>`;
  }else body=`<g opacity="${1-p}">${oldScene}</g><g opacity="${p}">${newScene}</g>`;
 }else body=objects.map(o=>objectSVG(o,local,s,"new")).join("");
 // Keep glyph selection consistent with preview.html when embedded in a host
 // whose document language differs (for example Remotion's English shell).
 return `<svg xmlns="http://www.w3.org/2000/svg" lang="zh-CN" xml:lang="zh-CN" viewBox="0 0 ${doc.canvas.width} ${doc.canvas.height}" width="${doc.canvas.width}" height="${doc.canvas.height}"><rect width="100%" height="100%" fill="#${bg}"/>${body}</svg>`;
}
export function locate(doc,time){
 let offset=0;
 for(let i=0;i<doc.slides.length;i++){
  if(time<offset+doc.slides[i].duration||i===doc.slides.length-1)return [i,time-offset];
  offset+=doc.slides[i].duration;
 }
}
export function renderFrame(doc,time){const [i,t]=locate(doc,time);return sceneSVG(doc,i,t);}

