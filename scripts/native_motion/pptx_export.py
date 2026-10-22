"""Native DrawingML geometry and PresentationML timing; no media embedding."""
import copy, math, os, tempfile, zipfile
from pathlib import Path
from lxml import etree
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml import parse_xml

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
P159 = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"
NS = {"p": P, "a": A, "mc": MC, "p159": P159, "p14": P14}
UNIT = 6350

def el(tag, **attrs):
    n = OxmlElement(tag)
    for k, v in attrs.items():
        n.set(k, str(v))
    return n

def place(slide, node):
    old = slide._element.find("p:extLst", NS)
    if old is None:
        slide._element.append(node)
    else:
        old.addprevious(node)

def remove_timing(slide):
    for n in slide._element.findall("p:timing", NS):
        slide._element.remove(n)

def transition(slide, spec, advance=None):
    for n in list(slide._element):
        if etree.QName(n).localname == "transition" or (n.tag == "{"+MC+"}AlternateContent" and n.find(".//p:transition", NS) is not None):
            slide._element.remove(n)
    def node(kind):
        tr = el("p:transition", spd="fast", advClick="1")
        tr.set("{"+P14+"}dur", str(round(spec["duration"])))
        if advance is not None:
            tr.set("advTm", str(round(advance)))
        if kind == "morph":
            tr.append(etree.Element("{"+P159+"}morph", option="byObject"))
        elif kind != "none":
            ch = el("p:"+kind)
            if kind in ("wipe", "push"):
                ch.set("dir", spec.get("direction", "l"))
            tr.append(ch)
        return tr
    if spec["kind"] == "morph":
        result = etree.Element("{"+MC+"}AlternateContent", nsmap={"mc": MC, "p159": P159})
        choice = etree.SubElement(result, "{"+MC+"}Choice", Requires="p159")
        choice.append(node("morph"))
        fallback = etree.SubElement(result, "{"+MC+"}Fallback")
        fallback.append(node("fade"))
    else:
        result = node(spec["kind"])
    timing = slide._element.find("p:timing", NS)
    if timing is not None:
        timing.addprevious(result)
    else:
        place(slide, result)

def alpha(color, value):
    if value != 1:
        color.append(el("a:alpha", val=round(value*100000)))

def paint(shape, o):
    shape.line.fill.background()
    if o["fill"] == "none":
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(o["fill"])
        alpha(shape._element.find(".//a:solidFill/a:srgbClr", NS), o["opacity"])
    if o.get("stroke"):
        shape.line.color.rgb = RGBColor.from_string(o["stroke"])
        shape.line.width = Pt(o.get("stroke_width", 2)/2)
        alpha(shape._element.find(".//a:ln/a:solidFill/a:srgbClr", NS), o["opacity"])
    if o.get("gradient"):
        pr = shape._element.find("p:spPr", NS)
        for child in list(pr):
            if etree.QName(child).localname in ("solidFill", "noFill", "gradFill"):
                pr.remove(child)
        g = o["gradient"]
        grad = el("a:gradFill", rotWithShape=1)
        stops = el("a:gsLst")
        for pos, key in ((0, "from"), (100000, "to")):
            stop = el("a:gs", pos=pos)
            clr = el("a:srgbClr", val=g[key])
            alpha(clr, o["opacity"])
            stop.append(clr); stops.append(stop)
        grad.append(stops)
        grad.append(el("a:lin", ang=round(g["angle"]%360*60000), scaled=1))
        ln = pr.find("a:ln", NS)
        if ln is None: pr.append(grad)
        else: ln.addprevious(grad)
    for ref in shape._element.xpath(".//a:effectRef"):
        ref.set("idx", "0")

def add_object(slide, o):
    x,y,w,h = o["box"]
    box = [round(v*UNIT) for v in (x,y,w,h)]
    kind = o["kind"]
    if kind == "group":
        children = [add_object(slide, c) for c in o["objects"]]
        shape = slide.shapes.add_group_shape(children)
        xf = shape._element.find("p:grpSpPr/a:xfrm", NS)
        for tag, keys, vals in (("off", ("x","y"), (x,y)), ("ext", ("cx","cy"), (w,h)),
                               ("chOff", ("x","y"), (0,0)), ("chExt", ("cx","cy"), (w,h))):
            node=xf.find("a:"+tag, NS)
            for k,v in zip(keys,vals): node.set(k,str(round(v*UNIT)))
    elif kind == "text":
        shape = slide.shapes.add_textbox(*box)
        tf=shape.text_frame;tf.clear()
        tf.word_wrap=False
        tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
        tf.vertical_anchor=MSO_ANCHOR.TOP
        for li,line in enumerate(o["text"].split("\n")):
            p=tf.paragraphs[0] if li==0 else tf.add_paragraph()
            p.alignment={"left":PP_ALIGN.LEFT,"center":PP_ALIGN.CENTER,"right":PP_ALIGN.RIGHT}[o["align"]]
            p.space_before=p.space_after=Pt(0)
            p.line_spacing=Pt(o["size"]/2*o["line_height"])
            r=p.add_run();r.text=line;r.font.name=o["font"];r.font.size=Pt(o["size"]/2)
            r.font.bold=o["bold"];r.font.color.rgb=RGBColor.from_string(o["fill"])
            rp=r._r.get_or_add_rPr();rp.set("spc",str(round(o["spacing"]*50)))
            for tag in ("a:ea","a:cs"):
                rp.append(el(tag,typeface=o["font"]))
            alpha(rp.find("a:solidFill/a:srgbClr", NS),o["opacity"])
    elif kind == "polygon":
        pts=[(x+p[0],y+p[1]) for p in o["points"]]
        b=slide.shapes.build_freeform(*pts[0],scale=UNIT)
        b.add_line_segments(pts[1:],close=True)
        shape=b.convert_to_shape()
        # Force the coordinate frame to the declared box. Points are local.
        path=shape._element.find("p:spPr/a:custGeom/a:pathLst/a:path", NS)
        path.set("w",str(round(w*1000)));path.set("h",str(round(h*1000)))
        for cmd,pt in zip(path.findall("a:moveTo/a:pt",NS)+path.findall("a:lnTo/a:pt",NS),o["points"]):
            cmd.set("x",str(round(pt[0]*1000)));cmd.set("y",str(round(pt[1]*1000)))
        shape.left,shape.top,shape.width,shape.height=box
        paint(shape,o)
    elif kind == "line":
        shape=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,box[0],box[1],box[0]+box[2],box[1]+box[3])
        shape.line.color.rgb=RGBColor.from_string(o.get("stroke",o["fill"]))
        shape.line.width=Pt(o.get("stroke_width",2)/2)
        alpha(shape._element.find(".//a:ln/a:solidFill/a:srgbClr",NS),o["opacity"])
    elif kind == "path":
        shape=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,*box)
        pr=shape._element.find("p:spPr",NS)
        old=pr.find("a:prstGeom",NS);pr.remove(old)
        geom=el("a:custGeom")
        for name in ("avLst","gdLst","ahLst","cxnLst"):geom.append(el("a:"+name))
        geom.append(el("a:rect",l=0,t=0,r="r",b="b"))
        paths=el("a:pathLst");path=el("a:path",w=round(w*1000),h=round(h*1000))
        for command in o["commands"]:
            tag={"M":"moveTo","L":"lnTo","C":"cubicBezTo","Q":"quadBezTo","Z":"close"}[command["op"]]
            node=el("a:"+tag)
            for px,py in command["points"]:node.append(el("a:pt",x=round(px*1000),y=round(py*1000)))
            path.append(node)
        paths.append(path);geom.append(paths);pr.insert(1,geom);paint(shape,o)
    else:
        typ=MSO_SHAPE.OVAL if kind=="ellipse" else MSO_SHAPE.ROUNDED_RECTANGLE if o.get("radius",0) else MSO_SHAPE.RECTANGLE
        shape=slide.shapes.add_shape(typ,*box)
        if o.get("radius",0):shape.adjustments[0]=min(.5,o["radius"]/min(w,h))
        paint(shape,o)
    shape.name="!!"+o["id"]
    shape.rotation=o["rotation"]
    return shape

def reassign_ids(slide):
    for i,n in enumerate(slide._element.findall(".//p:cNvPr",NS),1):
        n.set("id",str(i))

class Animator:
    def __init__(self, slide, replace=True):
        if replace: remove_timing(slide)
        self.slide=slide;self.counter=3;self.groups={}
        self.timing=el("p:timing");tn=el("p:tnLst");self.timing.append(tn)
        par=el("p:par");tn.append(par)
        root=el("p:cTn",id=1,dur="indefinite",restart="never",nodeType="tmRoot");par.append(root)
        child=el("p:childTnLst");root.append(child)
        seq=el("p:seq",concurrent=1,nextAc="seek");child.append(seq)
        main=el("p:cTn",id=2,dur="indefinite",nodeType="mainSeq");seq.append(main)
        self.main_children=el("p:childTnLst");main.append(self.main_children)
        for tag,evt in (("p:prevCondLst","onPrev"),("p:nextCondLst","onNext")):
            lst=el(tag);c=el("p:cond",evt=evt,delay=0)
            target=el("p:tgtEl");target.append(el("p:sldTgt"));c.append(target);lst.append(c);seq.append(lst)
        self.builds=el("p:bldLst")
        self.timing.append(self.builds)
        place(slide,self.timing)
    def ident(self):
        i=self.counter;self.counter+=1;return i
    def group(self, click):
        if click not in self.groups:
            outer=el("p:par");ctn=el("p:cTn",id=self.ident(),fill="hold")
            conds=el("p:stCondLst");conds.append(el("p:cond",delay="indefinite" if click else 0))
            ctn.append(conds);outer.append(ctn)
            children=el("p:childTnLst");ctn.append(children)
            inner=el("p:par");children.append(inner)
            inner_time=el("p:cTn",id=self.ident(),fill="hold")
            sc=el("p:stCondLst");sc.append(el("p:cond",delay=0));inner_time.append(sc);inner.append(inner_time)
            effects=el("p:childTnLst");inner_time.append(effects)
            self.main_children.append(outer);self.groups[click]=effects
        return self.groups[click]
    def behavior(self,sid,duration,e,attrs=(),letters=False):
        b=el("p:cBhvr")
        t=el("p:cTn",id=self.ident(),dur=round(duration),fill="hold")
        if duration>1:
            t.set("accel",str(round(e["accel"]*100000)));t.set("decel",str(round(e["decel"]*100000)))
        b.append(t)
        tgt=el("p:tgtEl");sp=el("p:spTgt",spid=sid);tgt.append(sp);b.append(tgt)
        if letters:
            tx=el("p:txEl");tx.append(el("p:pRg",st=0,end=0));sp.append(tx)
        if attrs:
            names=el("p:attrNameLst")
            for a in attrs: n=el("p:attrName");n.text=a;names.append(n)
            b.append(names)
        return b
    def add(self,shape,e,canvas):
        click=e["click"];grp=self.group(click);sid=shape.shape_id
        kind=e["kind"];letters=e["by_letter"]
        wipe=e.get("effect")=="wipe"
        preset=22 if wipe else {"enter":10,"exit":10,"rotate":8,"scale":6,"move":0}[kind]
        subtype={"up":4,"down":1,"left":2,"right":8}[e["direction"]] if wipe else 0
        outer=el("p:par");ctn=el("p:cTn",id=self.ident(),presetID=preset,
              presetClass={"enter":"entr","exit":"exit","move":"path","rotate":"emph","scale":"emph"}[kind],
              presetSubtype=subtype,fill="hold",nodeType="clickEffect" if click and len(grp)==0 else "withEffect")
        outer.append(ctn)
        if e["loop"]:
            ctn.set("repeatCount","indefinite")
            if e["auto_reverse"]:ctn.set("autoRev","1")
        sc=el("p:stCondLst");sc.append(el("p:cond",delay=round(e["at"])));ctn.append(sc)
        if letters:
            ctn.set("grpId",str(sid));itr=el("p:iterate",type="lt")
            itr.append(el("p:tmAbs",val=round(e["letter_delay"])));ctn.append(itr)
            if not any(b.get("spid")==str(sid) for b in self.builds):
                self.builds.append(el("p:bldP",spid=sid,grpId=sid))
        body=el("p:childTnLst");ctn.append(body)
        if kind in ("enter","exit"):
            if kind=="enter":
                st=el("p:set");st.append(self.behavior(sid,1,e,("style.visibility",),letters))
                to=el("p:to");to.append(el("p:strVal",val="visible"));st.append(to);body.append(st)
            # Office's filter parameter names the opposite side of the visual reveal.
            # From-bottom native preset 22/4 exports as wipe(down), not wipe(up).
            filter_direction={"up":"down","down":"up","left":"right","right":"left"}
            filter_name=f"wipe({filter_direction[e['direction']]})" if wipe else "fade"
            fade=el("p:animEffect",transition="in" if kind=="enter" else "out",filter=filter_name)
            fade.append(self.behavior(sid,e["duration"],e,letters=letters));body.append(fade)
        if kind in ("enter","exit","move"):
            start=e.get("from",[0,60] if kind=="enter" else [0,0])
            end=e.get("to",[0,0])
            pts=e.get("path",[start,end])
            if any(v for p in pts for v in p):
                norm=[[p[0]/canvas["width"],p[1]/canvas["height"]] for p in pts]
                path="M "+f"{norm[0][0]:.9f} {norm[0][1]:.9f} "
                if len(norm)==2:
                    path+="L "+" ".join(f"{p[0]:.9f} {p[1]:.9f}" for p in norm[1:])
                else:
                    for offset in range(1,len(norm),3):
                        path+="C "+" ".join(f"{p[0]:.9f} {p[1]:.9f}" for p in norm[offset:offset+3])+" "
                path+=" E"
                m=el("p:animMotion",origin="layout",path=path,pathEditMode="relative",rAng=0)
                m.append(self.behavior(sid,e["duration"],e,("ppt_x","ppt_y"),letters));body.append(m)
        if kind=="rotate":
            rot=el("p:animRot",by=round(e.get("degrees",4)*60000))
            rot.append(self.behavior(sid,e["duration"],e,("r",)));body.append(rot)
        if kind=="scale":
            scale=el("p:animScale",zoomContents=1);scale.append(self.behavior(sid,e["duration"],e,("ppt_w","ppt_h")))
            start=e.get("from",[1,1]);end=e.get("to",[1.08,1.08])
            scale.append(el("p:from",x=round(start[0]*100000),y=round(start[1]*100000)))
            scale.append(el("p:to",x=round(end[0]*100000),y=round(end[1]*100000)));body.append(scale)
        grp.append(outer)
    def finish(self):
        if not len(self.builds):self.timing.remove(self.builds)
        if not self.groups:self.slide._element.remove(self.timing)

def build(doc, destination, auto=False):
    p=Presentation();p.slide_width=round(doc["canvas"]["width"]*UNIT);p.slide_height=round(doc["canvas"]["height"]*UNIT)
    p.core_properties.title=doc["title"];p.core_properties.author="Native Motion Studio"
    mapping=[]
    for si, spec in enumerate(doc["slides"]):
        s=p.slides.add_slide(p.slide_layouts[6]);s.background.fill.solid()
        s.background.fill.fore_color.rgb=RGBColor.from_string(spec["background"])
        pairs=[(o,add_object(s,o)) for o in spec["objects"]]
        reassign_ids(s)
        animator=Animator(s)
        for click in range(len(spec["clicks"])+1):
            for o,shape in pairs:
                for e in o["animations"]:
                    if e["click"]==click:
                        emitted=copy.deepcopy(e)
                        if auto and emitted["click"]:
                            emitted["at"]+=spec["clicks"][emitted["click"]-1]
                            emitted["click"]=0
                        animator.add(shape,emitted,doc["canvas"])
        animator.finish()
        transition(s,spec["transition"],spec["duration"] if auto and si<len(doc["slides"])-1 else None)
        s.notes_slide.notes_text_frame.text=spec["notes"]
        mapping.append({o["id"]:sh.shape_id for o,sh in pairs})
    Path(destination).parent.mkdir(parents=True,exist_ok=True);p.save(destination)
    return mapping

def inventory(source):
    from .existing import inspect_existing
    return inspect_existing(source)

def enhance(source,destination,clicks=2,replace=False,plan=None):
    """Preserve art and unrelated package parts; skip animated slides by default."""
    from .existing import inspect_existing,validate_plan,verify_changes
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise ValueError('Choose a new output; existing files were preserved')
    original=inventory(source);p=Presentation(source);counts=[];modified={}
    if clicks<1:raise ValueError("clicks must be >= 1")
    plans=validate_plan(plan,original) if plan is not None else {}
    settings=(plan or {}).get('animation',{})
    for si,s in enumerate(p.slides,1):
        if s._element.find("p:timing",NS) is not None and not replace:
            counts.append({"skipped":"existing animation"});continue
        if plan is not None:
            if si not in plans:
                counts.append({"skipped":"not in plan"});continue
            if not plans[si]:
                counts.append({'added':0,'click_groups':0});continue
            targets={sh.shape_id:sh for sh in s.shapes};used=set();a=Animator(s)
            for ci,group in enumerate(plans[si],1):
                if not group:raise ValueError("Plan groups must be nonempty")
                for j,sid in enumerate(group):
                    if sid not in targets or sid in used:raise ValueError("Plan target is missing or repeated")
                    used.add(sid)
                    e={"kind":"enter","at":j*settings.get('stagger_ms',100),"duration":settings.get('duration_ms',450),"click":ci,"loop":False,
                       "auto_reverse":True,"by_letter":False,"letter_delay":35,"accel":.1,"decel":.65,
                       "from":[0,0] if plan.get('format_version',1)>=2 else [0,18]}
                    a.add(targets[sid],e,{"width":p.slide_width/UNIT,"height":p.slide_height/UNIT})
            a.finish();modified[str(s.part.partname).lstrip('/')]=copy.deepcopy(s._element.find('p:timing',NS))
            counts.append({"added":len(used),"click_groups":len(plans[si])});continue
        content=[sh for sh in s.shapes if getattr(sh,"has_text_frame",False) and sh.text.strip()]
        if not content:counts.append({"added":0});continue
        # The largest text near the top is the heading; keep it visible.
        heading=max(content,key=lambda sh:sum((r.font.size or 0) for p in sh.text_frame.paragraphs for r in p.runs))
        body=sorted([sh for sh in content if sh!=heading],key=lambda sh:(sh.top,sh.left))
        a=Animator(s);block=max(1,math.ceil(len(body)/max(1,clicks)))
        for i,sh in enumerate(body):
            e={"kind":"enter","at":(i%block)*100,"duration":450,"click":1+i//block,"loop":False,
               "auto_reverse":True,"by_letter":False,"letter_delay":35,"accel":.1,"decel":.65,"from":[0,18]}
            a.add(sh,e,{"width":p.slide_width/UNIT,"height":p.slide_height/UNIT})
        a.finish();counts.append({"added":len(body),"click_groups":math.ceil(len(body)/block)})
        if body:modified[str(s.part.partname).lstrip('/')]=copy.deepcopy(s._element.find('p:timing',NS))
    # Copy every unrelated part directly from the original ZIP. Re-saving an
    # arbitrary presentation through python-pptx may rewrite/drop unknown parts.
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.nmp-enhance-',suffix='.pptx',dir=destination.parent);os.close(fd);stage=Path(name)
    try:
        with zipfile.ZipFile(source) as before,zipfile.ZipFile(stage,'w') as after:
            if any(n.startswith('_xmlsignatures/') for n in before.namelist()):raise ValueError('Signed PPTX cannot be edited while preserving its signature')
            after.comment=before.comment
            for item in before.infolist():
                data=before.read(item.filename)
                if item.filename in modified:
                    root=etree.fromstring(data);old=root.find('p:timing',NS);node=modified[item.filename]
                    if old is not None:
                        if node is not None:node.tail=old.tail;old.addprevious(node)
                        root.remove(old)
                    elif node is not None:
                        ext=root.find('p:extLst',NS)
                        if ext is None:root.append(node)
                        else:ext.addprevious(node)
                    data=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
                after.writestr(copy.copy(item),data)
        verify_changes(source,stage,set(modified))
        if inventory(source)['source_pptx_sha256']!=original['source_pptx_sha256']:raise ValueError('Source PPTX changed during enhancement')
        os.link(stage,destination)
    finally:stage.unlink(missing_ok=True)
    return counts

