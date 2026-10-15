#!/usr/bin/env python3
"""Verify intentionally faulty and corrected real-playback regression evidence."""
import argparse
import json
from pathlib import Path

from native_motion.acceptance import sha,save


def verify(root):
    root=Path(root).resolve();cases=[]
    for name,expected in [("fault","failed"),("fixed","passed")]:
        case=root/name
        proof=json.loads((case/"playback-evidence.json").read_text())
        measured=json.loads((case/"qa/motion/native-motion-playback-audit.json").read_text())
        if proof.get("origin")!="native_desktop_screen_capture" or proof.get("is_pptx_playback_recording") is not True:
            raise ValueError("Regression requires real desktop recordings")
        for key,path in [("recording_sha256",case/"player-recording.mp4"),("source_pptx_sha256",case/"deck.pptx")]:
            if measured[key]!=sha(path) or proof[key]!=sha(path):raise ValueError("Stale regression evidence: "+name)
        if proof.get("opened_copy_sha256")!=proof["source_pptx_sha256"]:raise ValueError("Regression opened another PPTX")
        if measured["source_json_sha256"]!=sha(case/"project.json") or measured["planned_input_sha256"]!=sha(case/"playback-plan.json"):
            raise ValueError("Regression source or input plan changed")
        if measured["status"]!=expected:raise ValueError("Unexpected regression result: "+name)
        if name=="fault" and not any(e["code"]=="position-jump" for e in measured["errors"]):raise ValueError("Known jump was not detected")
        if name=="fixed" and (measured["errors"] or any(o["status"]!="passed" for o in measured["objects"])):
            raise ValueError("Corrected motion remains unresolved")
        cases.append({"case":name,"expected_measurement_state":expected,"actual_measurement_state":measured["status"],
                      "max_actor_step_px":max(o["max_step_px"] for o in measured["objects"]),
                      "recording_sha256":proof["recording_sha256"],"source_pptx_sha256":proof["source_pptx_sha256"],
                      "report":name+"/qa/motion/motion-report.html"})
    report={"status":"passed","cases":cases,"errors":[],"scope":"The fault case must be rejected and the corrected case must pass. These recordings do not certify the main project or another player."}
    save(root/"regression-check.json",report);return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("root")
    print(json.dumps(verify(parser.parse_args().root),indent=2))
