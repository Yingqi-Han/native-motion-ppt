"""Native playback measurement must not accept design-video or stale-recording evidence."""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from check_desktop_bars import check


class DesktopEvidenceTests(unittest.TestCase):
    def test_code_preview_is_not_accepted_as_player_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);evidence=root/"evidence.json"
            evidence.write_text(json.dumps({"origin":"code_generated_design_preview","is_pptx_playback_recording":False}))
            args=argparse.Namespace(video=root/"design.mp4",pptx=root/"deck.pptx",out=root/"qa",
                                    evidence=evidence,start=1,end=5,hold=4,tolerance=1,prefix="bar-")
            with self.assertRaisesRegex(ValueError,"design previews are not accepted"):
                check(args)

    def test_a_replaced_recording_cannot_reuse_old_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);video=root/"player.mp4";video.write_bytes(b"different recording")
            evidence=root/"evidence.json"
            evidence.write_text(json.dumps({"origin":"native_desktop_screen_capture","is_pptx_playback_recording":True,
                                           "recording_sha256":"old-video-sha","source_pptx_sha256":"old-deck-sha"}))
            args=argparse.Namespace(video=video,pptx=root/"deck.pptx",out=root/"qa",
                                    evidence=evidence,start=1,end=5,hold=4,tolerance=1,prefix="bar-")
            with self.assertRaisesRegex(ValueError,"differs from its evidence"):
                check(args)


if __name__=="__main__":unittest.main()
