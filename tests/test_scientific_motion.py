"""Scientific semantics: truthful scales, computed statistics and native baseline anchoring."""
import copy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from native_motion.figures import bar_chart, dot_plot, line_chart, sample_network
from native_motion.recipes import anchored_grow, settled_drift, wipe_in
from native_motion.model import normalize
from native_motion.pptx_export import build
from native_motion.qa import audit,import_check
from pptx import Presentation


class ScientificMotionTests(unittest.TestCase):
    def test_bar_domain_cannot_hide_the_zero_baseline(self):
        with self.assertRaises(ValueError):bar_chart("bars",["A"],[52],[920,385,800,425],[40,60],"s")

    def test_out_of_domain_data_are_rejected_instead_of_clipped(self):
        with self.assertRaises(ValueError):line_chart("line",[0,1],[2,5],[920,385,800,425],[0,4],"a.u.")

    def test_line_times_must_be_increasing(self):
        with self.assertRaises(ValueError):line_chart("line",[0,1,1],[2,3,2],[920,385,800,425],[0,4],"a.u.")

    def test_zero_bar_has_no_fabricated_positive_height(self):
        f=bar_chart("bars",["A"],[0],[920,385,800,425],[0,60],"s")
        o=next(o for o in f.objects if o["id"]=="bars-bar-0")
        self.assertEqual(o["kind"],"path");self.assertEqual(f.metadata["values"],[0])
        self.assertTrue(o["d"].endswith("112.0 0"))

    def test_statistics_are_computed_from_observations(self):
        f=dot_plot("dot",{"A":[1,2,3,4]},[920,385,800,425],[0,5],"a.u.")
        stat=f.metadata["statistics"][0]
        self.assertEqual((stat["median"],stat["q1"],stat["q3"]),(2.5,1.75,3.25))

    def test_drift_does_not_mutate_its_source_and_returns_to_layout(self):
        o=sample_network("subject",[100,100,200,200]);before=copy.deepcopy(o)
        animated=settled_drift(o)
        self.assertEqual(o,before)
        self.assertEqual(animated["animations"][0]["path"][0],animated["animations"][0]["path"][-1])
        self.assertFalse(animated["animations"][0].get("loop",False))

    def test_conflicting_authored_animation_is_preserved(self):
        o={"id":"bar","kind":"rect","box":[100,100,80,200],"animations":[{"kind":"rotate","degrees":10}]}
        with self.assertRaises(ValueError):anchored_grow(o)
        self.assertEqual(o["animations"][0]["degrees"],10)

    def test_default_bar_exports_a_single_wipe_without_native_transforms(self):
        figure=bar_chart("bar",["A","B"],[10,20],[920,385,800,425],[0,60],"s")
        d=normalize({"version":1,"slides":[{"duration":6000,"clicks":[750],"objects":figure.objects}]})
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"bars.pptx";build(d,path)
            result=audit(path);self.assertEqual(result["issues"],[]);self.assertEqual(result["media_parts"],0)
            root=Presentation(path).slides[0]._element
            self.assertEqual(root.xpath('.//p:animScale'),[])
            self.assertEqual(root.xpath('.//p:animMotion'),[])
            wipes=root.xpath('.//p:animEffect[@filter="wipe(down)"]')
            self.assertEqual(len(wipes),2)
            self.assertEqual(len(root.xpath('.//p:cTn[@presetID="22"][@presetSubtype="4"]')),2)

    @unittest.skipUnless(shutil.which("soffice"),"Office importer is required")
    def test_bottom_wipe_imports_with_the_correct_direction(self):
        figure=bar_chart("bar",["A"],[20],[920,385,800,425],[0,60],"s")
        d=normalize({"version":1,"slides":[{"duration":6000,"clicks":[750],"objects":figure.objects}]})
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"wipe.pptx";build(d,p)
            imported=import_check(p,Path(t)/"imported")
            wipe=[f for f in imported["transition_filters"] if f.get("type")=="barWipe"]
            self.assertEqual(len(wipe),1)
            self.assertEqual(wipe[0]["subtype"],"topToBottom")
            self.assertEqual(wipe[0]["direction"],"reverse")

    def test_wipe_rejects_a_compensation_motion(self):
        o=wipe_in({"id":"bar","kind":"rect","box":[100,100,100,200]})
        o["animations"][0]["from"]=[0,20]
        with self.assertRaises(ValueError):normalize({"version":1,"slides":[{"objects":[o]}]})


if __name__=="__main__":unittest.main()
