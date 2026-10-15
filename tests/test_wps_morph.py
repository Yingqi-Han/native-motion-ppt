"""Synthetic unit fixtures test false-positive rejection; these are NEVER WPS playback evidence."""
import argparse,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from check_native_morph import check
from native_motion.acceptance import sha
from native_motion.model import normalize
from native_motion.pptx_export import build

class MorphEvidenceTests(unittest.TestCase):
 def fixture(self,root,motion=False):
  spec={'version':1,'canvas':{'width':320,'height':180,'fps':20},'slides':[
   {'id':f's{i}','duration':4000,'transition':{'kind':'morph' if i else 'none','duration':1600 if i else 0},
    'objects':[{'id':'probe','kind':'rect','box':box,'fill':'00766A',
     **({'animations':[{'kind':'move','duration':500,'to':[3,0]}]} if motion else {})}]}
   for i,box in enumerate([[20,75,30,30],[220,55,60,60]])]}
  deck=root/'unit.pptx';build(normalize(spec),deck);video=root/'unit.bin';video.write_bytes(b'unit fixture only, not a video')
  ev=root/'unit-evidence.json';ev.write_text(json.dumps({'origin':'native_desktop_screen_capture','is_pptx_playback_recording':True,
   'player':'SYNTHETIC UNIT FIXTURE','source_pptx_sha256':sha(deck),'recording_sha256':sha(video)}))
  return argparse.Namespace(pptx=deck,video=video,evidence=ev,start=0,end=3.95,out=root/'unit-report.json')
 def pixels(self,fade):
  # Crop used by checker: [5,40,296,131]. Internal mocked arrays are not encoded/exported.
  for i in range(80):
   t=i/20;progress=min(1,max(0,(t-1)/1.6));bg=np.full((180,320,3),244,dtype=np.uint8);color=np.array([0,118,106])
   if fade:
    bg[75:105,20:50]=(244*progress+color*(1-progress)).astype(np.uint8)
    bg[55:115,220:280]=(244*(1-progress)+color*progress).astype(np.uint8)
   else:
    x=round(20+200*progress);y=round(75-20*progress);size=round(30+30*progress);bg[y:y+size,x:x+size]=color
   yield i,t,bg[40:131,5:296]
 def run_fixture(self,fade):
  with tempfile.TemporaryDirectory() as tmp:
   args=self.fixture(Path(tmp));meta={'streams':[{'width':320,'height':180}]};times=[i/20 for i in range(80)]
   with patch('check_native_morph.probe',return_value=(meta,times)),patch('check_native_morph.decode',return_value=self.pixels(fade)):
    return check(args)
 def test_solid_interpolation_has_many_intermediate_poses(self):
  self.assertEqual(self.run_fixture(False)['status'],'passed')
 def test_dissolve_cannot_pass_as_native_morph(self):
  r=self.run_fixture(True);self.assertEqual(r['status'],'failed');self.assertLess(r['solid_intermediate_distinct_poses'],10)
 def test_object_motion_is_rejected_even_if_transition_has_morph_tag(self):
  with tempfile.TemporaryDirectory() as tmp:
   args=self.fixture(Path(tmp),motion=True)
   with self.assertRaisesRegex(ValueError,'no object animations'):check(args)
 def test_stale_capture_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   args=self.fixture(Path(tmp));args.video.write_bytes(b'replaced')
   with self.assertRaisesRegex(ValueError,'checksum mismatch'):check(args)
if __name__=='__main__':unittest.main()
