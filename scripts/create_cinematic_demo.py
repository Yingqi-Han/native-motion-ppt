#!/usr/bin/env python3
"""Create a three-scene original motion study with explicitly simulated data.

Six editable blades become six data bars through native Morph. A separate chart
uses bottom-up wipes, so chart geometry never moves below the zero baseline.
"""
import argparse
import json
import math
from pathlib import Path

from native_motion.recipes import fade_in, wipe_in

ROOT = Path(__file__).resolve().parents[1]
PAPER, INK, MUTED, GRID = 'F4EFE6', '26231F', '6E645B', 'DAD0C4'
CORAL, PALE = 'F1714D', 'FBC5A2'
SANS, LATIN = 'Noto Sans CJK SC', 'Space Grotesk SemiBold'
VALUES = [28, 39, 47, 61, 74, 88]
COLORS = [('C2583E', 'F5A87F'), ('B64932', 'ED865D'),
          ('DF6C45', 'FFD0A0'), ('C85033', 'F79268'),
          ('EB8054', 'FFD4AA'), ('B44730', 'EF8B60')]


def text(ident, content, box, size=30, color=INK, role='body', **extra):
    obj = dict(id=ident, kind='text', text=content, box=box, size=size,
               fill=color, font=SANS, role=role)
    obj.update(extra)
    return obj


def shape(ident, box, color, **extra):
    return dict(id=ident, kind='rect', box=box, fill=color, **extra)


def line(ident, x1, y1, x2, y2, color=GRID, width=1):
    return dict(id=ident, kind='path', box=[x1, y1, max(.01, x2-x1), max(.01, y2-y1)],
                d=f'M 0 0 L {x2-x1} {y2-y1}', fill='none', stroke=color,
                stroke_width=width, role='decoration')


def chrome(index, light=True):
    ink, muted = (INK, MUTED) if light else (PAPER, 'BCAF9F')
    return [text('brand', 'NATIVE / MOTION STUDY', [96, 58, 900, 36], 20,
                 ink, 'label', font=LATIN),
            text(f'folio-{index}', f'0{index} / 03', [1340, 58, 164, 36], 20,
                 ink, 'label', align='right'),
            text(f'note-{index}', '原创动效样片 · 图表为模拟数据',
                 [96, 834, 1100, 36], 20, muted, 'caption')]


def blade(index, box, rotation=0):
    low, high = COLORS[index]
    return shape(f'blade-{index}', box, low, radius=24, rotation=rotation,
                 gradient={'from': low, 'to': high, 'angle': 0}, role='visual')


def create():
    first = chrome(1)
    first += [dict(id='orbit', kind='ellipse', box=[775, 150, 730, 585],
                   fill='none', stroke=GRID, stroke_width=1.2, role='decoration'),
              fade_in(text('opening-kicker', '01 / 先把目光聚拢', [100, 177, 630, 48],
                           26, MUTED, 'label'), at=100, duration=450, dy=14),
              fade_in(text('opening-title', '让信息，\n精彩地转身。', [96, 252, 690, 270],
                           88, INK, 'title', bold=True), at=160, duration=850, dy=42),
              fade_in(text('opening-caption', '让动作接续内容，\n让变化值得被看见。', [102, 607, 630, 100],
                           30, MUTED), at=1100, duration=520, dy=18)]
    for i, angle in enumerate([-50, -30, -10, 10, 30, 50]):
        rad = math.radians(angle)
        cx, cy = 1160 + math.sin(rad)*205, 660-math.cos(rad)*205
        obj = blade(i, [cx-46, cy-205, 92, 410], angle)
        # Every blade arrives at its exact static pose before the Morph.
        obj['animations'] = [dict(kind='enter', at=80+i*85,
                                  duration=1050+i*45, click=0,
                                  **{'from': [150*math.sin(rad), 110],
                                     'accel': .08, 'decel': .72})]
        first.append(obj)
    first += [fade_in(dict(id='hinge', kind='ellipse', box=[1136, 636, 48, 48],
                           fill=INK, role='visual'), at=1350, duration=300),
              fade_in(text('hero-tag', '六个原生形状 / 下一页继续', [935, 750, 580, 40],
                           23, MUTED, 'caption'), at=1600, duration=400)]

    second = chrome(2)
    second += [text('morph-kicker', '02 / 再让形状给出证据', [100, 177, 600, 48],
                    26, MUTED, 'label'),
               text('morph-title', '同一组形状，\n换一个视角。', [96, 252, 620, 270],
                    82, INK, 'title', bold=True),
               text('morph-caption', '扇形转为数据柱。\n位置、比例与方向跨页接续。',
                    [102, 607, 600, 100], 28, MUTED)]
    for val in [0, 50, 100]:
        y = 680-4.8*val
        second += [line(f'grid-{val}', 790, y, 1500, y, GRID, 1.2),
                   text(f'tick-{val}', str(val), [735, y-18, 44, 38], 20, MUTED,
                        'label', align='right')]
    for i, val in enumerate(VALUES):
        x, h = 815+i*112, val*4.8
        second.append(blade(i, [x, 680-h, 72, h]))
        second += [fade_in(text(f'value-{i}', str(val), [x-10, 680-h-50, 92, 44],
                                30, INK, 'label', align='center'),
                           at=350+i*70, duration=360),
                   fade_in(text(f'category-{i}', f'0{i+1}', [x-10, 706, 92, 42],
                                22, MUTED, 'label', align='center'), at=450, duration=360)]
    second += [text('chart-unit', '模拟指标 / 0—100', [790, 135, 700, 44],
                    22, MUTED, 'caption', align='right')]

    third = chrome(3, False)
    third += [fade_in(text('evidence-kicker', '03 / 把差距展开给我看', [100, 177, 650, 48],
                           26, PALE, 'label'), at=100, duration=400, dy=12),
              fade_in(text('evidence-title', '每一步，\n都更接近重点。', [96, 252, 690, 270],
                           82, PAPER, 'title', bold=True), at=180, duration=700, dy=30),
              fade_in(text('evidence-ratio', '3.7×', [96, 520, 650, 176],
                           150, PALE, 'data', bold=True), at=2900, duration=550, dy=16),
              fade_in(text('evidence-caption', '88 ÷ 24 ≈ 3.7，示意比值。',
                           [104, 727, 650, 52], 26, 'BCAF9F', 'caption'),
                      at=3200, duration=400)]
    for val in [0, 50, 100]:
        y = 680-4.8*val
        third += [line(f'evidence-grid-{val}', 850, y, 1500, y, '51473E', 1.2),
                  text(f'evidence-tick-{val}', str(val), [790, y-18, 48, 38],
                       20, 'BCAF9F', 'label', align='right')]
    for i, (name, val) in enumerate(zip(['起点', '中段', '目标'], [24, 56, 88])):
        x, h, at = 890+i*210, val*4.8, 500+i*600
        bar = shape(f'evidence-bar-{i}', [x, 680-h, 130, h], CORAL,
                    role='data', gradient={'from': CORAL, 'to': PALE, 'angle': 270})
        third += [wipe_in(bar, at=at, duration=1050, direction='up'),
                  text(f'evidence-label-{i}', name, [x-10, 709, 150, 48],
                       26, PAPER, 'label', align='center'),
                  fade_in(text(f'evidence-value-{i}', str(val), [x-10, 680-h-65, 150, 56],
                               40, PAPER, 'label', align='center'),
                          at=at+1050, duration=330)]

    return dict(version=1, title='转身 / 原生动态视觉样片',
                canvas=dict(width=1600, height=900, fps=30),
                theme=dict(font=SANS, latin_font=LATIN, background=PAPER,
                           foreground=INK, accent=CORAL),
                slides=[dict(id='focus', duration=5500, background=PAPER,
                             transition=dict(kind='none', duration=0), objects=first,
                             notes='原创图形：六片形状分步聚拢，停稳后再翻页。'),
                        dict(id='perspective', duration=6500, background=PAPER,
                             transition=dict(kind='morph', duration=1800), objects=second,
                             notes='同名原生矩形由扇形转为柱形。模拟数据28/39/47/61/74/88。'),
                        dict(id='evidence', duration=7500, background=INK,
                             transition=dict(kind='fade', duration=500), objects=third,
                             notes='模拟数据24/56/88。原生擦除从固定零基线上露出，不缩放柱形。')])


def create_focus_zoom():
    """Expand the same six values into a full-width chart with one focal value.

    This is a layout change through native Morph, not a 3D camera or new data.
    All six bar heights share one scale and one zero baseline on each page.
    """
    doc = create()
    focus = chrome(3)
    focus += [text('focus-kicker', '03 / 把比较展开，把重点留下',
                   [100, 113, 650, 44], 25, MUTED, 'label'),
              text('focus-title', '把目光，\n交给最重要的数。',
                   [96, 178, 640, 200], 70, INK, 'title', bold=True),
              text('focus-caption', '六项保持同一比例，重点留给 88。',
                   [100, 392, 650, 45], 25, MUTED),
              text('chart-unit', '模拟指标 / 0—100', [790, 135, 700, 44],
                   22, MUTED, 'caption', align='right')]
    for value in [0, 50, 100]:
        y = 740-5.2*value
        # Avoid the large 88 with geometry, rather than opaque label masks that
        # can arrive too early and cut into the moving bars during native Morph.
        focus += [line(f'grid-{value}', 96 if value == 0 else 810, y,
                       1200 if value == 100 else 1500, y,
                       GRID, 1.2),
                  text(f'focus-tick-{value}', str(value), [35, y-18, 45, 38],
                       20, MUTED, 'label', align='right')]
    for i, value in enumerate(VALUES):
        x, height = 96+i*230, value*5.2
        obj = blade(i, [x, 740-height, 150, height])
        obj['role'] = 'data'
        if i < len(VALUES)-1:
            obj.update(fill='A99B8B', gradient={'from': 'A99B8B', 'to': 'D8CCBD', 'angle': 0})
        focus.append(obj)
        box = [x-10, 740-height-50, 170, 44]
        if i == len(VALUES)-1:
            box = [x-15, 740-height-104, 180, 96]
        focus += [text(f'value-{i}', str(value), box,
                       76 if i == len(VALUES)-1 else 30,
                       INK, 'label', align='center', bold=i == len(VALUES)-1),
                  text(f'category-{i}', f'0{i+1}', [x-10, 770, 170, 42],
                       24, MUTED, 'label', align='center')]
    doc['title'] = '聚焦 / 连续原生 Morph 视觉样片'
    doc['slides'] = doc['slides'][:2]+[
        dict(id='full-frame-focus', duration=6500, background=PAPER,
             transition=dict(kind='morph', duration=1800), objects=focus,
             notes='与上一页相同的六项模拟数据和原生对象。全幅重排时所有柱共享零基线与相同尺度，突出第六项88。不是新增测量或真实三维镜头。')]
    return doc


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--focus-zoom', action='store_true', help='Use two consecutive Morph transitions and a full-width focal chart')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    path = args.out or ROOT/'examples'/('cinematic-focus-zoom.json' if args.focus_zoom else 'cinematic-focus.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(create_focus_zoom() if args.focus_zoom else create(),
                               ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(path)
