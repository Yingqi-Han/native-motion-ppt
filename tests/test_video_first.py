"""Unit fixtures test binding/order only, never actual-video or WPS acceptance."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from native_motion.video_first import digest,seal,verify
from create_sound_ppt import create,closed_horizontal_cycle


class VideoFirstTests(unittest.TestCase):
    def fixture(self,folder,status='passed'):
        video=folder/'unit-fixture.mp4';video.write_bytes(b'unit binding fixture, not footage')
        story=folder/'story.json';story.write_bytes((ROOT/'examples/science-video/sound-story.json').read_bytes())
        quality=folder/'quality.json';quality.write_text(json.dumps({'origin':'rendered_science_video_qa',
            'status':status,'video_sha256':digest(video),'story_sha256':digest(story)}))
        return video,story,quality,folder/'VIDEO_LOCK.json'

    def test_no_ppt_is_created_without_a_finished_video_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);destination=folder/'ppt'
            with self.assertRaises(FileNotFoundError):create(folder/'missing.json',destination)
            self.assertFalse(destination.exists())

    def test_failed_video_checks_cannot_be_sealed(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.fixture(Path(temp),'failed')
            with self.assertRaisesRegex(ValueError,'Complete video checks'):seal(*args)
            self.assertFalse(args[-1].exists())

    def test_mutated_video_or_script_is_rejected_before_ppt_output(self):
        for kind in ['video','story','quality']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                folder=Path(temp);video,story,quality,lock=self.fixture(folder);seal(video,story,quality,lock)
                paths={'video':video,'story':story,'quality':quality};paths[kind].write_bytes(paths[kind].read_bytes()+b' ')
                with self.assertRaisesRegex(ValueError,'changed'):create(lock,folder/'ppt')
                self.assertFalse((folder/'ppt').exists())

    def test_bound_teaching_deck_and_mapping_preserve_the_video_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);video,story,quality,lock=self.fixture(folder);seal(video,story,quality,lock)
            result=create(lock,folder/'ppt')
            self.assertEqual(result['slides'],8)
            mapping=json.loads((folder/'ppt/video-to-ppt.json').read_text())
            self.assertEqual(mapping['video_sha256'],digest(video))
            self.assertEqual(mapping['mapping'][5]['video_start_seconds'],48)
            self.assertEqual(mapping['mapping'][5]['video_end_seconds'],62)
            with self.assertRaisesRegex(ValueError,'previous PPT'):create(lock,folder/'ppt')

    def test_finite_marker_cycle_returns_to_the_static_pose_before_morph(self):
        points=closed_horizontal_cycle()
        self.assertEqual(points[0],[0,0]);self.assertEqual(points[-1],[0,0])
        self.assertEqual(len(points),13)
        self.assertTrue(all(y==0 for x,y in points))

    def test_retimed_video_maps_new_scene_boundaries_and_sample_frames(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);video,story,quality,lock=self.fixture(folder)
            story.write_bytes((ROOT/'examples/science-video/sound-refined.json').read_bytes())
            d=json.loads(quality.read_text());d['story_sha256']=digest(story);quality.write_text(json.dumps(d))
            seal(video,story,quality,lock);create(lock,folder/'ppt')
            mapping=json.loads((folder/'ppt/video-to-ppt.json').read_text())['mapping']
            self.assertEqual(mapping[5]['video_start_seconds'],42)
            self.assertEqual(mapping[-1]['video_end_seconds'],66)
            self.assertEqual(mapping[2]['representative_frame'],570)


if __name__=='__main__':unittest.main()
