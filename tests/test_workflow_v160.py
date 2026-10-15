"""Backend selection, phase evidence and immutable reruns. Synthetic unit fixtures are not playback evidence."""
import argparse,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from native_motion.players import recording_command,preflight,player_matches
from native_motion.acceptance import Ledger,sha,save
from native_motion.evidence import verify_reviews
from native_motion.phases import analyse_morph,classify_pages,morph_candidates,contour
from native_motion.desktop_workflow import execute_resume
from native_motion.model import normalize

class BackendTests(unittest.TestCase):
 def test_wps_target_dispatches_real_wps(self):
  cmd=recording_command('wps-desktop','x.pptx','capture',{'show_after':1,'seconds':9,'click_at':[4]},dict(width=1280,height=720,fps=30),'tools','wps','profile')
  self.assertEqual(cmd[0],'scripts/record_wps.py');self.assertIn('--wps-root',cmd);self.assertNotIn('scripts/record_desktop.py',cmd)
 def test_missing_wps_cannot_fall_back_to_impress(self):
  with self.assertRaisesRegex(ValueError,'WPS requires'):recording_command('wps-desktop','x','out',{'show_after':1,'seconds':9,'click_at':[]},dict(width=1280,height=720,fps=30))
  self.assertEqual(preflight('powerpoint-desktop')['status'],'pending')
 def test_relabelling_impress_does_not_certify_wps(self):
  self.assertFalse(player_matches('wps-desktop',{'player':'LibreOffice Impress','origin':'native_desktop_screen_capture','is_pptx_playback_recording':True}))

class PhaseTests(unittest.TestCase):
 def test_auto_identical_pages_remain_ambiguous(self):
  frame=np.full((180,320,3),230,dtype=np.uint8);times=[i/30 for i in range(90)]
  pages,_,_,_=classify_pages(times,[frame]*90,[frame,frame])
  self.assertTrue(all(p['status']=='pending' for p in pages))
 def test_full_page_matching_has_no_folio_dependency(self):
  a=np.full((180,320,3),230,dtype=np.uint8);a[50:90,40:100]=[0,80,120]
  b=np.full((180,320,3),230,dtype=np.uint8);b[80:140,190:270]=[130,40,20]
  frames=[a.copy() for _ in range(60)]+[b.copy() for _ in range(90)];times=[i/30 for i in range(len(frames))]
  pages,starts,_,_=classify_pages(times,frames,[a,b]);self.assertEqual([p['status'] for p in pages],['passed','passed']);self.assertAlmostEqual(starts[1],59/30)
 def test_dissolve_contour_cannot_pass_morph(self):
  first=[20,50,50,80];last=[220,50,280,110]
  rows=[{'timestamp':i/30,'frame_index':i,'box':first if i<10 else [20,50,280,110] if i<40 else last} for i in range(60)]
  r=analyse_morph(rows,first,last);self.assertNotEqual(r['status'],'passed');self.assertTrue(any(i['code']=='morph-double-image' for i in r['issues']))
 def test_arrival_cutoff_is_observed_not_a_source_duration(self):
  first=[20,50,50,80];last=[220,50,280,110];rows=[]
  for i in range(100):
   t=i/30;q=min(1,max(0,(t-.5)/1.5));b=[round(20+200*q),50,round(50+230*q),round(80+30*q)]
   rows.append({'timestamp':t,'frame_index':i,'box':b})
  r=analyse_morph(rows,first,last);self.assertEqual(r['status'],'passed');self.assertGreater(r['distinct_intermediate_poses'],10);self.assertAlmostEqual(r['settled_seconds'],2,delta=.1)
 def test_shaded_color_mask_does_not_absorb_a_neutral_arrow(self):
  c={'roi':[0,0,100,60],'palette':[[0,118,106]],'background':[244,242,234],'excluded_text_boxes':[]}
  p=np.full((60,100,3),[244,242,234],dtype=np.uint8);p[20:40,10:30]=[110,174,162];p[25:35,70:85]=[183,198,193]
  box=contour(p,c);self.assertEqual(box,[10,20,30,40])
 def test_same_color_decoy_is_not_merged_into_observed_subject(self):
  c={'roi':[0,0,100,60],'palette':[[0,118,106]],'background':[244,242,234],'excluded_text_boxes':[]}
  p=np.full((60,100,3),[244,242,234],dtype=np.uint8);p[20:40,10:30]=[0,118,106];p[25:35,70:85]=[0,118,106]
  self.assertEqual(contour(p,c,seed=[20,30]),[10,20,30,40])
 def test_palette_includes_visible_stroke_when_gradient_endpoint_absent(self):
  doc=normalize({'version':1,'slides':[{'objects':[{'id':'probe','kind':'group','box':[10,10,40,40],'objects':[{'id':'line','kind':'rect','box':[0,0,40,40],'fill':'00766A'},{'id':'center','kind':'ellipse','box':[10,10,10,10],'fill':'BE5434'}]}]},
    {'transition':{'kind':'morph','duration':800},'objects':[{'id':'probe','kind':'group','box':[200,10,60,60],'objects':[{'id':'line','kind':'rect','box':[0,0,60,60],'fill':'00766A'},{'id':'center','kind':'ellipse','box':[10,10,10,10],'fill':'BE5434'}]}]}]})
  cs,uncovered=morph_candidates(doc);self.assertFalse(uncovered);c=cs[0];self.assertIn([0,118,106],c['palette'])
  x0,y0,x1,y1=c['roi'];p=np.full((y1-y0,x1-x0,3),240,dtype=np.uint8);p[20-y0:40-y0,20-x0:40-x0]=[0,118,106]
  self.assertIsNotNone(contour(p,c))

class ReviewTests(unittest.TestCase):
 def fixture(self,p):
  ledger=Ledger(p,{'sha256':'unit'});(p/'v.mp4').write_bytes(b'unit fixture, not video');(p/'frame.png').write_bytes(b'unit frame');(p/'scan.json').write_text('{}')
  ledger.data['recordings']={'manual':{'video':'v.mp4','recording_sha256':sha(p/'v.mp4')}};ledger.check('motion','Motion','pending','scan.json');return ledger
 def payload(self,l):return {'reviewer':'unit-test','recordings':{k:v['recording_sha256'] for k,v in l.data['recordings'].items()},'reviews':[{'check_id':'motion','status':'passed','note':'Specific inspected phase boundary','evidence':['frame.png']}]}
 def test_review_preserves_raw_pending_and_verifies_hashes(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);l=self.fixture(p);l.review(self.payload(l));l.finish();c=l.data['checks'][0]
   self.assertEqual(c['automatic_status'],'pending');self.assertEqual(c['reviewed_status'],'passed');self.assertEqual(c['status'],'passed');verify_reviews(p,l.data)
   (p/'frame.png').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'evidence changed'):verify_reviews(p,l.data)
 def test_review_cannot_override_failed_measurement(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);l=self.fixture(p);l.check('motion','Motion','failed','scan.json')
   with self.assertRaisesRegex(ValueError,'Fix and retest'):l.review(self.payload(l))
 def test_stale_recording_review_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);l=self.fixture(p);payload=self.payload(l);(p/'v.mp4').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'replaced recording'):l.review(payload)
 def test_visual_pending_does_not_hide_technical_auto_pass(self):
  with tempfile.TemporaryDirectory() as tmp:
   l=Ledger(tmp,{});l.check('technical','Technical','passed');l.check('visual-review','Visual','pending');l.finish()
   self.assertEqual(l.data['automatic_acceptance_status'],'passed');self.assertEqual(l.data['acceptance_status'],'pending')

class RerunTests(unittest.TestCase):
 def test_check_only_copies_approved_dependencies_into_new_run(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);parent=base/'old';parent.mkdir();source=parent/'project.json';source.write_text(json.dumps({'version':1,'slides':[{'objects':[]}]}))
   (parent/'deck.pptx').write_bytes(b'unit');(parent/'manifest.json').write_text(json.dumps({n:{'sha256':sha(parent/n),'bytes':(parent/n).stat().st_size} for n in ['project.json','deck.pptx']}))
   save(parent/'acceptance.json',{'format_version':2,'source':{'snapshot':'project.json','sha256':sha(source)},'checks':[],'requested_target_player':'wps-desktop'})
   original=sha(parent/'acceptance.json');args=argparse.Namespace(resume=parent,mode='check',target_player=None,spec=None,out=base,run_name='new')
   with patch('verify_acceptance.verify'),patch('native_motion.desktop_workflow.run_desktop') as flow,patch('accept_project.finalize_run'):
    root,d=execute_resume(args)
   self.assertEqual(sha(parent/'acceptance.json'),original);self.assertEqual(root,base/'new');self.assertEqual(d['stages'],[])
   self.assertEqual(flow.call_args.args[-1],'check');self.assertEqual(sha(root/'deck.pptx'),sha(parent/'deck.pptx'))
 def test_changed_source_cannot_reuse_an_old_ppt(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);parent=p/'old';parent.mkdir();save(parent/'project.json',{'version':1,'slides':[{'objects':[]}]});save(parent/'manifest.json',{})
   save(parent/'acceptance.json',{'format_version':2,'source':{'snapshot':'project.json','sha256':sha(parent/'project.json')},'checks':[],'requested_target_player':'wps-desktop'})
   changed=p/'changed.json';changed.write_text('{}');args=argparse.Namespace(resume=parent,mode='record',target_player=None,spec=changed,out=p,run_name='new')
   with patch('verify_acceptance.verify'),self.assertRaisesRegex(ValueError,'Changed source'):execute_resume(args)
if __name__=='__main__':unittest.main()
