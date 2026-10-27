"""Measured speech segments must keep their real boundaries in captions."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from create_sound_video import captions

class SoundCaptionTests(unittest.TestCase):
 def fixture(self):
  story={'scenes':[{'id':'one','duration_seconds':8,'narration':'短句。更长的一句话。'},{'id':'credits','duration_seconds':4,'narration':''}]}
  audio={'clips':[{'scene':'one','duration_seconds':5,'cues':[{'text':'短句。','start_seconds':0,'end_seconds':2.7},{'text':'更长的一句话。','start_seconds':3,'end_seconds':5}]}]}
  return story,audio
 def test_measured_boundaries_override_character_proportions(self):
  story,audio=self.fixture();rows,cues=captions(story,audio)
  self.assertEqual([(r['startMs'],r['endMs']) for r in rows['one']],[(600,3300),(3600,5600)])
  self.assertEqual(cues[1],(3.6,5.6,'更长的一句话。'))
  self.assertEqual(rows['credits'],[])
 def test_overlapping_or_out_of_audio_range_is_rejected(self):
  for field,value in [('start_seconds',2.5),('end_seconds',5.1)]:
   story,audio=self.fixture();audio['clips'][0]['cues'][1][field]=value
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'boundaries'):captions(story,audio)
 def test_wrong_caption_words_are_rejected(self):
  story,audio=self.fixture();audio['clips'][0]['cues'][0]['text']='错误。'
  with self.assertRaisesRegex(ValueError,'match the narration'):captions(story,audio)
 def test_legacy_audio_still_has_documented_approximate_captions(self):
  story,audio=self.fixture();del audio['clips'][0]['cues']
  rows,_=captions(story,audio);self.assertEqual(rows['one'][0]['startMs'],600);self.assertEqual(rows['one'][-1]['endMs'],5600)

if __name__=='__main__':unittest.main()
