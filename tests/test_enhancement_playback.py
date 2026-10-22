"""Synthetic reveal controls constrain the checker; these images are not WPS frames."""
import sys
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from check_enhancement_playback import measure_reveal,normalize_reference,compare_region


class RevealTests(unittest.TestCase):
    def images(self):
        blank=Image.new('RGB',(500,280),'#F4F2EA');reference=blank.copy()
        ImageDraw.Draw(reference).rectangle((70,70,420,220),fill='#00766A')
        return blank,reference

    def test_hidden_to_complete_content_passes(self):
        blank,reference=self.images()
        self.assertEqual(measure_reveal(blank,reference,reference)['status'],'passed')

    def test_content_visible_before_click_cannot_certify_a_reveal(self):
        _,reference=self.images()
        self.assertEqual(measure_reveal(reference,reference,reference)['status'],'failed')

    def test_missing_or_wrong_post_click_content_fails(self):
        blank,reference=self.images();wrong=Image.new('RGB',reference.size,'#4460DA')
        self.assertEqual(measure_reveal(blank,blank,reference)['status'],'failed')
        self.assertEqual(measure_reveal(blank,wrong,reference)['status'],'failed')

    def test_only_one_pixel_pdf_rounding_is_normalized(self):
        normalized,basis=normalize_reference(Image.new('RGB',(1600,901)),(1600,900))
        self.assertEqual(normalized.size,(1600,900));self.assertIn('rounding',basis)
        with self.assertRaises(ValueError):normalize_reference(Image.new('RGB',(1600,920)),(1600,900))

    def test_thin_context_keeps_aspect_but_missing_content_is_detected(self):
        blank=Image.new('RGB',(1000,70),'#F4F2EA');reference=blank.copy();shifted=blank.copy()
        ImageDraw.Draw(reference).rectangle((60,20,900,40),fill='#173330')
        ImageDraw.Draw(shifted).rectangle((60,21,900,41),fill='#173330')
        self.assertLess(compare_region(shifted,reference)['rmse'],8)
        missing=compare_region(blank,reference)
        self.assertTrue(missing['rmse']>8 or missing['max_tile_rmse']>18)


if __name__=='__main__':unittest.main()
