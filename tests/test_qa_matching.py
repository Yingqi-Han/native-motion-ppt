"""Actual Office fixtures distinguish repeated axis labels from real text overflow."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from native_motion.model import normalize
from native_motion.pptx_export import build
from native_motion.qa import render


@unittest.skipUnless(shutil.which("soffice"),"LibreOffice is required for actual glyph matching")
class OfficeMatchingTests(unittest.TestCase):
    def test_repeated_zero_ticks_are_assigned_to_the_correct_axis_boxes(self):
        d={"version":1,"slides":[{"objects":[
            {"id":"y-zero","kind":"text","text":"0","box":[820,790,75,44],"size":27,"font":"Space Grotesk SemiBold","align":"right"},
            {"id":"x-zero","kind":"text","text":"0","box":[870,834,100,48],"size":28,"font":"Space Grotesk SemiBold","align":"center"}]}]}
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"axes.pptx";build(normalize(d),p)
            self.assertEqual(render(p,Path(t)/"qa")["text_outside_declared_box"],[])

    def test_actual_overflow_still_fails_the_box_check(self):
        d={"version":1,"slides":[{"objects":[
            {"id":"too-wide","kind":"text","text":"OVERFLOW","box":[100,100,70,130],"size":100,"font":"Space Grotesk SemiBold"}]}]}
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"overflow.pptx";build(normalize(d),p)
            self.assertTrue(render(p,Path(t)/"qa")["text_outside_declared_box"])


if __name__=="__main__":unittest.main()
