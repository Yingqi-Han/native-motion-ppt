"""Failure detection from measured traces, not assertions about source easing code."""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from native_motion.playback_motion import analyse_trace,intervals,stable_runs,foreground_box
from check_native_motion import check


def trace(xs,dt=1/60,ys=None):
    return [{"frame_index":i,"timestamp":i*dt,"box":[x,(ys[i] if ys else 50),x+30,(ys[i] if ys else 50)+30]} for i,x in enumerate(xs)]


class NativeMotionTests(unittest.TestCase):
    def test_static_pose_cannot_pass_motion(self):
        self.assertEqual(analyse_trace(trace([50]*120))["status"],"pending")

    def test_large_actual_frame_jump_is_located(self):
        result=analyse_trace(trace([50]*40+[150]*60),intent="linear")
        issue=next(i for i in result["issues"] if i["code"]=="position-jump")
        self.assertEqual(result["status"],"failed");self.assertEqual(issue["frame_index"],40)
        self.assertAlmostEqual(issue["timestamp"],40/60)

    def test_closed_curve_turn_is_allowed(self):
        t=np.linspace(0,2*np.pi,120)
        result=analyse_trace(trace((50+8*np.sin(t)).tolist(),ys=(50+8*np.cos(t)).tolist()),intent="closed")
        self.assertEqual(result["status"],"passed")

    def test_capture_gap_does_not_certify_a_player_jump(self):
        rows=trace([50]*40+[150]*60)
        for i in range(40,len(rows)):rows[i]["timestamp"]+=.4
        result=analyse_trace(rows,intent="linear")
        self.assertEqual(result["status"],"pending")
        self.assertIn("capture-gap",[i["code"] for i in result["issues"]])

    def test_mid_action_hold_is_not_hidden_by_smoothing(self):
        rows=trace(list(range(50,90))+[90]*40+list(range(91,132)))
        result=analyse_trace(rows,intent="linear")
        self.assertEqual(result["status"],"pending");self.assertTrue(result["interior_holds"])

    def test_unequal_pts_define_speed(self):
        rows=trace(list(range(120)))
        for i,r in enumerate(rows):r["timestamp"]=i/30
        result=analyse_trace(rows,intent="linear")
        self.assertAlmostEqual(result["peak_speed_px_s"],30,places=5)

    def test_event_frames_retain_original_capture_indices(self):
        rows=trace(list(range(80)))
        for r in rows:r["frame_index"]+=1000
        result=analyse_trace(rows,intent="linear")
        self.assertGreaterEqual(result["observed_intervals"][0]["first_frame"],1000)

    def test_nearby_label_does_not_become_actor(self):
        frame=np.full((120,120,3),240,dtype=np.uint8)
        frame[4:10,4:110]=0;frame[50:80,50:80]=[0,100,90]
        bbox,area=foreground_box(frame,[240,240,240],seed=[65,65])
        self.assertEqual(bbox,[50,50,80,80]);self.assertEqual(area,900)

    def test_local_speed_burst_requires_review(self):
        xs=list(range(50))+list(range(69,130))
        result=analyse_trace(trace(xs),intent="linear")
        self.assertIn("speed-burst",[i["code"] for i in result["issues"]])

    def test_linear_rebound_is_detected(self):
        result=analyse_trace(trace(list(range(60))+list(range(60,40,-1))+list(range(41,100))),intent="linear")
        self.assertIn("rebound",[i["code"] for i in result["issues"]])

    def test_bar_baseline_and_rebound(self):
        rows=[]
        tops=[100-i for i in range(50)]+[60,65,70]+[50]*30
        for i,top in enumerate(tops):rows.append({"timestamp":i/60,"frame_index":i,"box":[50,top,80,160+(4 if i==20 else 0)]})
        result=analyse_trace(rows,kind="bar")
        self.assertEqual(result["status"],"failed")
        self.assertEqual({i["code"] for i in result["issues"]},{"baseline-drift","rebound"})

    def test_settled_bar_edge_quantization_is_not_a_stall(self):
        tops=list(range(100,50,-1))+[50]*100
        rows=[{"timestamp":i/60,"frame_index":i,"box":[50,top,80+(2 if i>100 else 0),160]} for i,top in enumerate(tops)]
        result=analyse_trace(rows,kind="bar")
        self.assertEqual(result["status"],"passed");self.assertAlmostEqual(result["observed_end"],50/60)

    def test_nonmonotonic_pts_rejected(self):
        rows=trace(list(range(60)));rows[30]["timestamp"]=rows[29]["timestamp"]
        with self.assertRaises(ValueError):analyse_trace(rows)

    def test_short_stop_not_reported_as_reading_hold(self):
        rows=trace(list(range(50))+[50]*3+list(range(51,100)))
        self.assertEqual(analyse_trace(rows,intent="linear")["status"],"passed")

    def test_stability_observed_without_fixed_probe(self):
        times=[i*.1 for i in range(40)];runs=stable_runs(times,[False]*12+[True]*28)
        self.assertEqual(runs,[(12,39)])
        self.assertEqual(intervals(times,[False]*5+[True]*10+[False]*25)[0]["start"],.4)

    def test_design_video_rejected_before_any_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence=Path(folder)/"evidence.json";evidence.write_text(json.dumps({"origin":"code_generated_design_preview"}))
            with self.assertRaisesRegex(ValueError,"actual desktop"):
                check(argparse.Namespace(video="missing",pptx="missing",out=folder,evidence=evidence))


if __name__=="__main__":unittest.main()
