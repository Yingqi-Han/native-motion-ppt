"""Synthetic binding tests; dummy movie bytes and fixtures are never playback evidence."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from native_motion.diagnostics import collect_diagnostics, write_diagnostics, verify_diagnostics, sha


class DiagnosticTests(unittest.TestCase):
    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value),encoding='utf-8')

    def fixture(self,root):
        (root/'video.mp4').write_bytes(b'synthetic binding fixture; not playable')
        (root/'deck.pptx').write_bytes(b'synthetic PPT binding fixture')
        (root/'project.json').write_text('{}')
        video=sha(root/'video.mp4');pptx=sha(root/'deck.pptx')
        self.write(root/'proof.json',{'origin':'native_desktop_screen_capture','is_pptx_playback_recording':True,
                   'player':'synthetic-test-player','recording_sha256':video,'source_pptx_sha256':pptx,'opened_copy_sha256':pptx,'actions':[{'key':'F5','at_wall_seconds':1}]})
        base={'origin':'measurement_of_actual_desktop_recording','recording_sha256':video,'source_pptx_sha256':pptx,'source_json_sha256':sha(root/'project.json')}
        phase=root/'qa/manual/phases/phase-audit.json'
        self.write(phase,{**base,'format_version':2,'status':'passed','playback_evidence_sha256':sha(root/'proof.json'),'actual_show_key_seconds':1,
                         'pages':[{'slide':1,'status':'passed','stable_interval_seconds':[3,5]}],'morphs':[],'uncovered_morphs':[]})
        self.write(root/'qa/manual/motion/native-motion-playback-audit.json',{**base,'status':'failed','phase_evidence_sha256':sha(phase),'pages':[],
            'objects':[{'slide':1,'object':'actor','status':'failed','issues':[{'code':'position-jump','severity':'failed','timestamp':2.,'frame_index':60,'message':'jump','suggestion':'repair then record'}]}],
            'uncovered_objects':[{'slide':1,'object':'rotating','status':'pending','reason_code':'unsupported-transform','reason':'Need angle tracking'}]})
        self.write(root/'acceptance.json',{'format_version':2,'acceptance_status':'failed','automatic_acceptance_status':'failed',
            'recordings':{'manual':{'video':'video.mp4','pptx':'deck.pptx','evidence':'proof.json','player':'synthetic-test-player','recording_sha256':video,'source_pptx_sha256':pptx}},
            'checks':[{'id':'native-phases-manual','status':'passed','label':'Phases'}, {'id':'native-motion-manual','status':'failed','label':'Motion'}]})

    def test_raw_states_are_preserved_and_unsupported_has_no_invented_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);old=(root/'acceptance.json').read_bytes()
            report=collect_diagnostics(root)
            self.assertEqual(report['acceptance_status'],'failed');self.assertEqual(report['diagnostic_integrity'],'passed')
            issue=next(f for f in report['findings'] if f['code']=='position-jump')
            self.assertEqual((issue['timestamp'],issue['frame_index']),(2.,60))
            unknown=next(f for f in report['findings'] if f['code']=='unsupported-transform')
            self.assertIsNone(unknown['timestamp']);self.assertEqual(unknown['location_basis'],'page_context_only')
            self.assertEqual(unknown['category'],'unsupported')
            self.assertEqual((root/'acceptance.json').read_bytes(),old)
            write_diagnostics(root,root/'derived',report);verify_diagnostics(root,root/'derived/diagnostics.json')
            page=(root/'derived/diagnostics.html').read_text()
            self.assertIn('非异常时刻',page);self.assertIn('原始帧 60',page)

    def test_replaced_video_does_not_receive_bound_time_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);(root/'video.mp4').write_bytes(b'changed')
            report=collect_diagnostics(root)
            self.assertEqual(report['diagnostic_integrity'],'failed');self.assertEqual(report['videos'],{})
            self.assertFalse(any(f['timestamp'] is not None for f in report['findings']))

    def test_changed_dependency_invalidates_old_explanation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);write_diagnostics(root,root/'derived',collect_diagnostics(root))
            (root/'proof.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Diagnostic source changed'):verify_diagnostics(root,root/'derived/diagnostics.json')

    def test_contradictory_formal_state_is_reported_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);data=json.loads((root/'acceptance.json').read_text());data['checks'][1]['status']='pending'
            self.write(root/'acceptance.json',data);report=collect_diagnostics(root)
            self.assertEqual(report['diagnostic_integrity'],'failed')
            self.assertTrue(any('disagree' in f['message'] for f in report['findings']))
            self.assertEqual(json.loads((root/'acceptance.json').read_text())['checks'][1]['status'],'pending')

    def test_evidence_paths_cannot_escape_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);data=json.loads((root/'acceptance.json').read_text());data['recordings']['manual']['evidence']='../private.json'
            self.write(root/'acceptance.json',data);report=collect_diagnostics(root)
            self.assertEqual(report['diagnostic_integrity'],'failed');self.assertEqual(report['videos'],{})


if __name__=='__main__':unittest.main()
