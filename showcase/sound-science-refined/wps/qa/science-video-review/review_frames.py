"""Supplementary actual-capture samples; does not replace generic phase results."""
from pathlib import Path
import hashlib,json,subprocess
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def frame(video,t):
 raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
 return Image.fromarray(np.frombuffer(raw,dtype=np.uint8).reshape(1080,1920,3))

def sheet(video,stamps,name,crop=None,cols=4):
 thumbs=[]
 for i,t in enumerate(stamps):
  im=frame(video,t)
  if crop:im=im.crop(crop)
  im.thumbnail((480,270));tile=Image.new('RGB',(480,300),'#0b1930');tile.paste(im,((480-im.width)//2,0));ImageDraw.Draw(tile).text((8,278),f'actual WPS frame @ {t:.3f} s',fill='white');thumbs.append(tile)
 canvas=Image.new('RGB',(480*cols,300*((len(thumbs)+cols-1)//cols)),'#0b1930')
 for i,tile in enumerate(thumbs):canvas.paste(tile,((i%cols)*480,(i//cols)*300))
 path=OUT/name;canvas.save(path);return str(path.relative_to(ROOT))
result={'origin':'supplementary_measurement_of_actual_WPS_recordings','scope':'Authored sound deck only. Actual timestamps chosen to inspect content, native marker cycle and transition intermediates. This does not clear generic phase/Morph pending results.','recordings':{},'contacts':{}}
for mode,filename,page_times,start in [
 ('manual','player-recording.mp4',[8,20,31,41,52,62,73,81],13.5),
 ('automatic','player-recording-auto.mp4',[8,18,28,38,46,55,63,71],11.7)]:
 v=ROOT/filename;result['recordings'][mode]=sha(v)
 result['contacts'][mode+'-pages']=sheet(v,page_times,mode+'-all-eight.jpg')
 # Decode at original 30fps. Orange marker/halo are isolated here; labels and
 # the low-opacity mean line are outside this color mask. No rendered model used.
 raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(start),'-i',str(v),'-t','3.2','-vf','crop=320:180:800:500:exact=1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
 a=np.frombuffer(raw,dtype=np.uint8).reshape(-1,180,320,3);obs=[]
 for n,f in enumerate(a):
  mask=(f[:,:,0]>205)&(f[:,:,1]>100)&(f[:,:,1]<215)&(f[:,:,2]<145)
  yy,xx=np.where(mask)
  if len(xx)<300:raise ValueError('Isolated orange marker absent')
  obs.append({'seconds':round(start+n/30,6),'x':float(xx.mean()+800+.5),'y':float(yy.mean()+500+.5),'orange_pixels':len(xx)})
 span=max(o['x'] for o in obs)-min(o['x'] for o in obs);vertical=max(o['y'] for o in obs)-min(o['y'] for o in obs)
 result[mode+'-marker']={'status':'passed' if span>75 and vertical<2 else 'failed','horizontal_span_px':span,'vertical_span_px':vertical,'samples':obs,'scope':'Measures local horizontal motion only; does not certify every grouped parcel or transition.'}
 result['contacts'][mode+'-cycle']=sheet(v,[start+q for q in [0,.4,.8,1.2,1.6,2,2.6,3.2]],mode+'-cycle.jpg',crop=(760,450,1160,750))
 if mode=='manual':
  result['contacts']['manual-transitions']=sheet(v,[11.55,12,12.5,13.25,22.35,22.8,23.2,23.8,32.6,33,33.5,34],mode+'-transitions.jpg')
  result['contacts']['manual-reveals']=sheet(v,[25.8,27.5,58,60.4],mode+'-reveals.jpg')
 else:
  result['contacts']['automatic-transitions']=sheet(v,[9.9,10.3,10.9,11.6,19.6,20.1,20.7,21.4,29.5,30,30.4,31],mode+'-transitions.jpg')
  result['contacts']['automatic-reveals']=sheet(v,[22.5,25,50,53.5],mode+'-reveals.jpg')
(OUT/'actual-capture-supplement.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:{a:b for a,b in v.items() if a!='samples'} if isinstance(v,dict) else v for k,v in result.items()},indent=2))
