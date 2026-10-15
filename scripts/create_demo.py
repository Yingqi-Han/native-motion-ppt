"""Generate the original six-scene reference document; seeded, no stock assets."""
import json,math,random
from pathlib import Path
from native_motion.recipes import settled_drift
ROOT=Path(__file__).resolve().parents[1]
INK="090B12";PAPER="F1F0EB";BLUE="4148FF";MUTED="9296A6"
def text(ident,content,box,size,color,latin=False,**extra):
 return {"id":ident,"kind":"text","text":content,"box":box,"size":size,"fill":color,
         "font":"Space Grotesk SemiBold" if latin else "Noto Sans CJK SC","role":"title" if size>=90 else "caption",**extra}
def enter(at=100,duration=650,dy=55,**extra):return {"kind":"enter","at":at,"duration":duration,"from":[0,dy],**extra}
def rect(ident,box,color,**extra):return {"id":ident,"kind":"rect","box":box,"fill":color,**extra}
def sphere(ident,box):
 # Visible hemisphere with procedural metallic lighting and editable faces.
 n,m=30,80;pts=[];faces=[]
 for j in range(n+1):
  th=j/n*math.pi
  for k in range(m):
   ph=k/m*2*math.pi
   px=math.sin(th)*math.cos(ph);py=math.cos(th);pz=math.sin(th)*math.sin(ph)
   # Slight irregular silhouette avoids a stock sphere look.
   warp=1+.035*math.sin(ph*3+py*2)*math.sin(th)
   pts.append((px*warp,py*warp,pz*warp))
 for j in range(n):
  for k in range(m):
   ids=[j*m+k,j*m+(k+1)%m,(j+1)*m+(k+1)%m,(j+1)*m+k]
   p=[pts[a] for a in ids];z=sum(v[2] for v in p)/4
   if z<0:continue
   face=[]
   for x,y,zv in p:
    scale=1/(1-zv*.09);face.append([box[2]/2+x*box[2]*.46*scale,box[3]/2-y*box[3]*.46*scale])
   colors=[]
   for vx,vy,vz in p:
    length=math.sqrt(vx*vx+vy*vy+vz*vz);nx,ny,nz=vx/length,vy/length,vz/length
    rx,ry,rz=2*nz*nx,2*nz*ny,2*nz*nz-1;edge=(1-max(0,nz))**3.2
    broad=math.exp(-min(100,abs((rx+.32)/.44)**6+abs((ry-.46)/.18)**6))
    stripe=math.exp(-min(100,abs((rx-.43)/.05)**6+abs(ry/.85)**6))
    fill=max(0,-rx*.65-ry*.12+rz)**3
    rgb=[.115+.32*fill+.13*edge+2.9*broad+2.3*stripe,
         .135+.40*fill+.25*edge+2.9*broad+2.3*stripe,
         .18+.66*fill+.62*edge+2.9*broad+2.3*stripe]
    colors.append([max(0,min(255,round((v/(1+v*.7))**.78*255))) for v in rgb])
   luminance=[sum(c[i]*[.22,.7,.08][i] for i in range(3)) for c in colors]
   lo=min(range(4),key=lambda i:luminance[i]);hi=max(range(4),key=lambda i:luminance[i])
   hexcol=lambda c:"".join(f"{v:02X}" for v in c)
   angle=math.degrees(math.atan2(face[hi][1]-face[lo][1],face[hi][0]-face[lo][0]))
   minx,miny=min(pt[0] for pt in face),min(pt[1] for pt in face)
   fw,fh=max(pt[0] for pt in face)-minx,max(pt[1] for pt in face)-miny
   if fw<.001 or fh<.001:continue
   local=[[pt[0]-minx,pt[1]-miny] for pt in face]
   faces.append((z,{"id":f"{ident}-face-{j}-{k}","kind":"polygon","box":[minx,miny,fw,fh],"points":local,"fill":hexcol(colors[lo]),"gradient":{"from":hexcol(colors[lo]),"to":hexcol(colors[hi]),"angle":angle}}))
 faces.sort(key=lambda t:t[0])
 return {"id":ident,"kind":"group","box":box,"role":"visual","objects":[o for _,o in faces]}
def chrome_orb(box,duration=1800,at=0):
 o=sphere("sculpture",box)
 # A small, continuous elliptical drift, then a settled pose for native Morph.
 # Avoid rotating a baked reflection like a flat sticker.
 return settled_drift(o,duration,at)
def ring(ident,box,thickness,color):
 w,h=box[2:];t=thickness;r=min(w,h)*.13;k=.55228475
 outer=f"M {r} 0 L {w-r} 0 C {w-r+k*r} 0 {w} {r-k*r} {w} {r} L {w} {h-r} C {w} {h-r+k*r} {w-r+k*r} {h} {w-r} {h} L {r} {h} C {r-k*r} {h} 0 {h-r+k*r} 0 {h-r} L 0 {r} C 0 {r-k*r} {r-k*r} 0 {r} 0 Z"
 iw,ih=w-2*t,h-2*t;ir=max(1,r-t)
 inner=f"M {t+ir} {t} C {t+ir-k*ir} {t} {t} {t+ir-k*ir} {t} {t+ir} L {t} {t+ih-ir} C {t} {t+ih-ir+k*ir} {t+ir-k*ir} {t+ih} {t+ir} {t+ih} L {t+iw-ir} {t+ih} C {t+iw-ir+k*ir} {t+ih} {t+iw} {t+ih-ir+k*ir} {t+iw} {t+ih-ir} L {t+iw} {t+ir} C {t+iw} {t+ir-k*ir} {t+iw-ir+k*ir} {t} {t+iw-ir} {t} Z"
 return {"id":ident,"kind":"path","box":box,"d":outer+" "+inner,"rotation":-8,"fill":color,"role":"visual"}
def scene(i,label,light=False,transition="fade"):
 return {"id":f"scene-{i}","label":label,"duration":2500,"background":PAPER if light else INK,
 "transition":{"kind":transition,"duration":480 if transition=="morph" else 320},
 "objects":[text("brand","NATIVE / MOTION",[108,70,960,50],27,INK if light else PAPER,True,spacing=2.8,role="label"),
 text(f"folio-{i}",f"{i:02} / 06",[1585,78,226,44],23,"626775" if light else MUTED,True,align="right",role="label")]}
def main():
 slides=[]
 s=scene(1,"开场");s["objects"]+=[chrome_orb([1090,225,660,660]),
 text("opening","信息\n开始流动。",[108,318,1120,370],134,PAPER,font="Noto Serif CJK SC",bold=True,animations=[enter(120)]),
 text("opening-note","让重点出现，让变化可见。",[115,847,1400,80],36,MUTED,animations=[enter(500,dy=20)])]
 s["duration"]=2200
 s["notes"]="原生面片组合构成三维视觉；标题入场，雕塑轻缓浮动。所有元素可编辑。";slides.append(s)
 s=scene(2,"重点",True,"morph")
 s["duration"]=2800
 s["transition"]["duration"]=760;s["clicks"]=[650]
 s["objects"]+=[chrome_orb([1225,267,470,470],1420,100),
 text("step1","01",[109,225,680,220],166,BLUE,True,animations=[enter(60,dy=38)]),
 text("focus-title","先看见重点。",[109,490,1080,172],101,INK,bold=True,animations=[enter(200,dy=38)]),
 text("focus-note","分组出现，让观众按你的顺序理解。",[114,792,1480,90],39,INK,animations=[enter(0,450,dy=18,click=1)])]
 s["notes"]="雕塑沿连续曲线轻缓漂移，回到静止位置后以760毫秒Morph移到右侧。说明文字等待一次点击；预览在转场后650毫秒模拟点击。";slides.append(s)
 s=scene(3,"路径",True);s["objects"]+=[
 text("step2","02",[109,225,650,210],166,BLUE,True,animations=[enter(60,dy=38)]),
 text("path-title","再跟上变化。",[109,490,1080,176],101,INK,bold=True,animations=[enter(160,dy=32,by_letter=True,letter_delay=55)]),
 text("path-note","位置、比例、方向，都能在 PPT 里修改。",[114,792,1550,90],39,INK,animations=[enter(550,dy=18)])]
 s["objects"].append({"id":"trajectory","kind":"path","box":[1170,250,570,450],"d":"M 20 310 C 120 70 200 390 310 230 C 400 100 470 110 550 40","fill":"none","stroke":"A6ABC9","stroke_width":3,"role":"visual","animations":[enter(0,550,dy=15)]})
 for i,(x,y,size) in enumerate([(1158,528,64),(1429,429,102),(1635,205,170)]):
  o={"id":f"node-{i}","kind":"ellipse","box":[x,y,size,size],"fill":BLUE,
     "animations":[enter(90+i*130,620,dy=80),{"kind":"scale","at":900,"duration":1400+i*110,"from":[1,1],"to":[1.07,1.07],"loop":True}]}
  s["objects"].append(o)
 s["notes"]="原生逐字出现；三个圆点分步到位后轻缓缩放。";slides.append(s)
 s=scene(4,"聚合",False,"push")
 s["objects"]+=[text("gather-title","散开，\n再聚拢。",[108,317,960,360],134,PAPER,bold=True,animations=[enter(120)]),
 text("gather-note","每个点，都有自己的路径。",[114,847,1480,80],36,MUTED,animations=[enter(470,dy=20)])]
 rng=random.Random(4107)
 for i in range(240):
  while True:
   x=rng.uniform(-1,1);y=rng.uniform(-1,1)
   # Letter A formed from two legs and a horizontal crossbar.
   leg=abs(abs(x)-.4*(y+1))<.095
   cross=abs(y-.25)<.085 and abs(x)<.6
   if leg or cross:break
  tx=1460+x*240;ty=530+y*290;r=rng.uniform(2.2,4.2)
  sx=rng.uniform(1020,1820)-tx;sy=rng.uniform(190,870)-ty
  s["objects"].append({"id":f"particle-{i}","kind":"ellipse","box":[tx-r,ty-r,r*2,r*2],"fill":"D0DAFF" if i%4 else "FFFFFF",
  "animations":[{"kind":"enter","at":rng.randrange(25,220),"duration":rng.randrange(720,1060),
    "path":[[sx,sy],[sx*.67,sy*.72-35],[sx*.14,-26],[0,0]],"from":[sx,sy]}]})
 s["notes"]="240个可编辑原生圆点，各自沿曲线路径聚合。";slides.append(s)
 s=scene(5,"空间",True);s["objects"]+=[
 text("depth-title","空间，\n从层次开始。",[108,320,1090,355],110,INK,font="Noto Serif CJK SC",bold=True,animations=[enter(110)]),
 text("depth-note","前后景错开运动，画面就有了纵深。",[114,847,1560,85],36,INK,animations=[enter(460,dy=20)])]
 for j in range(8):
  w=170+j*72;h=w*.73
  ident="actor-frame" if j==0 else f"depth-{j}"
  o=ring(ident,[1440-w/2,520-h/2,w,h],4+j*.65,"A1A6FF" if j%2 else BLUE)
  o["animations"]=[{"kind":"scale","at":120+j*35,"duration":1700+j*70,"from":[1,1],"to":[1.09,1.09],"loop":True}]
  s["objects"].append(o)
 s["notes"]="八层原生组合框以不同的时间和比例缩放，形成镜头向前的错觉。";slides.append(s)
 s=scene(6,"交付",False,"morph");o=ring("actor-frame",[815,165,290,212],11,BLUE)
 o["animations"]=[{"kind":"rotate","at":1000,"duration":2100,"degrees":3,"loop":True}]
 s["objects"]+=[o,text("wordmark","MOTION",[104,472,1712,310],238,PAPER,True,spacing=13,align="center",animations=[enter(140,650,dy=70,by_letter=True)]),
 text("closing","同一份设计。两种交付。",[106,834,1708,98],53,PAPER,align="center",animations=[enter(540,550,dy=22)]),
 text("closing-note","EDITABLE BY DESIGN",[106,978,1708,45],24,MUTED,True,spacing=4,align="center",animations=[enter(600,450,dy=10)])]
 s["notes"]="与上一页的actor-frame进行Morph对应。PPT输出原生动画，Remotion读取同一份对象和时间数据。";slides.append(s)
 doc={"version":1,"title":"Native Motion / 原生动态演示","canvas":{"width":1920,"height":1080,"fps":60},
      "theme":{"font":"Noto Sans CJK SC","latin_font":"Space Grotesk SemiBold","background":INK,"foreground":PAPER,"accent":BLUE},"slides":slides}
 (ROOT/"examples").mkdir(exist_ok=True);(ROOT/"examples/demo.json").write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
 print(ROOT/"examples/demo.json")
if __name__=="__main__":main()

