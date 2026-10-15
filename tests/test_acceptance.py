"""Acceptance must preserve failures, distinguish pending coverage and bind artifacts."""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from native_motion.acceptance import Ledger,playback_plan,write_report
from native_motion.model import normalize
from check_native_playback import compare_frame
from accept_project import execute,finalize_run
from verify_acceptance import verify


class AcceptanceTests(unittest.TestCase):
    def test_clicks_hold_and_next_page_do_not_collide(self):
        doc=normalize({"version":1,"slides":[{"duration":6000,"clicks":[750,2100],"objects":[
            {"id":"value","kind":"text","box":[100,100,800,100],"size":70,"text":"值",
             "animations":[{"kind":"enter","click":2,"duration":1200}]}]},
            {"duration":6000,"objects":[]}]})
        plan=playback_plan(doc)
        first=plan["pages"][0]
        self.assertGreater(first["held_probe_seconds"],first["click_at_seconds"][-1]+1.2)
        self.assertGreater(first["next_page_seconds"],first["held_probe_seconds"])
        self.assertEqual(plan["pages"][1]["page_input_seconds"],first["next_page_seconds"])
        self.assertEqual(plan["click_at"],sorted(plan["click_at"]))

    def test_failed_command_is_persisted_before_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ledger=Ledger(root,{"sha256":"test"})
            with self.assertRaises(RuntimeError):ledger.command("broken",[sys.executable,"-c","raise SystemExit(3)"])
            saved=json.loads((root/"acceptance.json").read_text())
            self.assertEqual(saved["stages"][0]["status"],"failed")
            self.assertEqual(saved["checks"][0]["status"],"failed")
            ledger.finish();self.assertEqual(ledger.data["acceptance_status"],"failed")

    def test_unavailable_target_cannot_become_overall_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(folder,{"sha256":"test"});ledger.check("design","设计","passed")
            ledger.check("target-player","WPS","pending",detail="WPS absent")
            ledger.finish();self.assertEqual(ledger.data["acceptance_status"],"pending")
            self.assertEqual(ledger.data["pipeline_status"],"completed")

    def test_optional_visual_review_does_not_certify_aesthetics(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(folder,{"sha256":"test"});ledger.check("native","原生","passed")
            ledger.check("visual-review","视觉","pending",required=False);ledger.finish()
            self.assertEqual(ledger.data["checks"][-1]["status"],"pending")

    def test_report_escapes_content_and_preserves_failed_state(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(folder,{"sha256":"test"});ledger.check("bad","<script>bad</script>","failed",detail="<img src=x>")
            ledger.finish();write_report(folder,ledger.data)
            text=(Path(folder)/"report.html").read_text()
            self.assertIn("&lt;script&gt;",text);self.assertNotIn("<script>bad</script>",text)
            self.assertIn("失败",text)

    def test_missing_local_graphics_do_not_hide_in_page_average(self):
        expected=Image.new("RGB",(1920,1080),"#f4f2ea");draw=ImageDraw.Draw(expected)
        draw.rectangle((930,420,1120,810),fill="#00766a")
        blank=Image.new("RGB",expected.size,"#f4f2ea")
        measured=compare_frame(blank,expected)
        self.assertGreater(measured["max_tile_rmse"],18)

    def test_small_antialiasing_shift_is_tolerated_by_descriptor(self):
        a=Image.new("RGB",(1920,1080),"#f4f2ea");b=a.copy()
        ImageDraw.Draw(a).rectangle((930,420,1120,810),fill="#00766a")
        ImageDraw.Draw(b).rectangle((932,422,1122,812),fill="#00766a")
        self.assertLess(compare_frame(a,b)["rmse"],8)

    def test_incomplete_stage_cannot_finish_as_passed(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(folder,{"sha256":"test"});ledger.data["stages"].append({"id":"capture","status":"running"})
            ledger.finish();self.assertEqual(ledger.data["acceptance_status"],"failed")

    def test_existing_run_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/"source.json";source.write_text('{"version":1}')
            old=root/"runs"/"existing";old.mkdir(parents=True);sentinel=old/"keep.txt";sentinel.write_text('user data')
            args=argparse.Namespace(spec=source,out=root/"runs",run_name="existing")
            with self.assertRaises(FileExistsError):execute(args)
            self.assertEqual(sentinel.read_text(),'user data')
            self.assertEqual(source.read_text(),'{"version":1}')

    def test_manifest_detects_changed_deliverable(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"file.txt").write_text('changed')
            (root/"manifest.json").write_text(json.dumps({"file.txt":{"bytes":3,"sha256":"old"}}))
            with self.assertRaisesRegex(ValueError,"Manifest mismatch"):verify(root)

    def test_visual_review_cannot_attach_to_replaced_movie(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);Ledger(root,{"sha256":"test"})
            (root/"player-recording.mp4").write_bytes(b"new recording")
            (root/"playback-evidence.json").write_text(json.dumps({"recording_sha256":"old"}))
            with self.assertRaisesRegex(ValueError,"replaced recording"):finalize_run(root,"reviewed")


if __name__=="__main__":unittest.main()
