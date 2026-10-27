"""Rendered SVG glyphs must not change with an embedding page's UI language."""
import base64
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from native_motion.fonts import resolve_font,bundle_fonts
from native_motion.model import normalize
from create_sound_ppt import generate


class SvgLocaleTests(unittest.TestCase):
    def test_chinese_math_frame_is_stable_in_english_and_chinese_hosts(self):
        browser=shutil.which('chromium') or shutil.which('google-chrome')
        font=resolve_font('Noto Sans CJK SC')
        if not browser or not shutil.which('node') or not font or not font['matched']:
            self.skipTest('Rendered regression needs Chromium, Node and full Noto CJK')
        try:
            from playwright.sync_api import sync_playwright
            from PIL import Image,ImageChops
        except ImportError:
            self.skipTest('Rendered regression needs the full analysis dependencies')
        story=json.loads((ROOT/'examples/science-video/sound-story.json').read_text())
        doc=normalize(generate(story)[0])
        program='import {renderFrame} from '+json.dumps((ROOT/'assets/timeline.mjs').as_uri())+';let s="";for await(const c of process.stdin)s+=c;process.stdout.write(renderFrame(JSON.parse(s),45600));'
        svg=subprocess.check_output(['node','--input-type=module','-e',program],input=json.dumps(doc),text=True)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);bundle_fonts(doc,folder);css=(folder/'fonts.css').read_text()
            for p in (folder/'fonts').iterdir():
                css=css.replace('./fonts/'+p.name,'data:font/otf;base64,'+base64.b64encode(p.read_bytes()).decode())
            images=[]
            with sync_playwright() as pw:
                b=pw.chromium.launch(executable_path=browser,headless=True)
                for language in ['en','zh-CN']:
                    page=b.new_page(viewport={'width':1920,'height':1080})
                    page.set_content(f'<html lang="{language}"><head><style>{css}html,body{{margin:0;font:14px system-ui}}svg{{display:block}}</style></head><body>{svg}</body></html>')
                    page.evaluate('async()=>{await Promise.all([document.fonts.load(\'400 40px "Noto Sans CJK SC"\'),document.fonts.load(\'700 40px "Noto Sans CJK SC"\')]);await document.fonts.ready}')
                    images.append(Image.open(io.BytesIO(page.screenshot())).convert('RGB'));page.close()
                b.close()
            self.assertIsNone(ImageChops.difference(*images).getbbox(),
                              'Host language changed authored Chinese/math glyphs')


if __name__=='__main__':unittest.main()
