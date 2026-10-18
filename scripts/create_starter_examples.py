#!/usr/bin/env python3
"""Rebuild editable, explicitly simulated product and progress starter projects."""
import json
from pathlib import Path

from native_motion.figures import Palette, bar_chart, label, segment
from native_motion.recipes import fade_in, settled_drift

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, PAPER, GRID = '142B31', '526763', 'F4F2EA', 'CCD8D1'


def text(ident, content, box, size=30, role='body', color=INK, **extra):
    return label(ident, content, box, size, color, role=role, **extra)


def heading(ident, content, box, size=66):
    return fade_in(text(ident, content, box, size, 'title', font='Noto Serif CJK SC'), at=100, duration=520, dy=14)


def chrome(prefix, number, section):
    return [text(prefix + '-section', section, [108, 62, 900, 40], 22, 'label', font='Space Grotesk SemiBold'),
            text(prefix + '-page', f'{number:02} / 03', [1335, 62, 160, 40], 22, 'label', MUTED, align='right', font='Space Grotesk SemiBold'),
            segment(prefix + '-rule', [108, 116], [1492, 116], GRID, 1.3),
            text(prefix + '-disclaimer', '模拟数据与流程示意，仅用于演示；请替换为核实后的内容。', [108, 844, 1380, 36], 21, 'caption', MUTED)]


def slide(ident, objects, number, section, morph=False, click=False):
    return {'id': ident, 'duration': 6800 if morph else 6000, 'clicks': [1000] if click else [],
            'background': PAPER, 'transition': {'kind': 'morph' if morph else 'fade', 'duration': 1800 if morph else 350},
            'objects': chrome(ident, number, section) + objects}


def flow(prefix):
    result = []
    for i, title in enumerate(['源内容', '动作编排', '原生输出']):
        x = 120 + i * 520
        result.append(text(f'{prefix}-step-{i}', title, [x, 420, 360, 65], 37, 'body', INK, align='center'))
        if i < 2:
            result.append(segment(f'{prefix}-link-{i}', [x + 300, 610], [x + 540, 610], GRID, 3))
    return result


def product():
    palette = Palette(paper=PAPER, ink=INK, muted=MUTED, accent='00766A', secondary='B35735')
    chart = bar_chart('revision', ['拆散重做', '保留对象'], [72, 36], [1000, 350, 450, 300], [0, 100], '示例耗时', palette=palette)
    token = {'id': 'product-token', 'kind': 'rect', 'box': [150, 620, 220, 150], 'radius': 18, 'fill': '4460DA', 'role': 'visual'}
    first = [heading('product-heading-a', '内容的变化，\n在同一页看清。', [108, 184, 770, 195]),
             text('product-purpose', '用原生对象组织信息，\n让每次修改都能继续编辑。', [112, 420, 720, 105], 30),
             settled_drift(token, duration=2000, rx=8, ry=7),
             text('product-token-caption', '一个可编辑主体', [120, 790, 440, 44], 25, 'caption', MUTED), *chart.objects]
    second_token = {**token, 'box': [1190, 520, 270, 180], 'radius': 20}
    second = [heading('product-heading-b', '同一份内容，\n延续同一个主体。', [108, 180, 1350, 195]), *flow('product-flow'),
              settled_drift(second_token, at=350, duration=2000, rx=8, ry=7),
              text('product-flow-note', '位置与尺度跨页衔接，动作结束后留出阅读时间。', [112, 755, 1380, 55], 28)]
    third = [heading('product-heading-c', '交付之后，仍能继续修改。', [108, 184, 1370, 110], 64),
             text('product-three-note', '让内容、动作和检查记录一起留下。', [112, 315, 1360, 58], 30, color=MUTED)]
    for i, (name, description) in enumerate([
        ('保留原生对象', '文字、图形与动画\n可以分别编辑。'),
        ('按讲解展开', '用少量语义点击\n组织信息顺序。'),
        ('按版本复核', '源稿、PPT 与录像\n各自绑定校验值。'),
    ]):
        x = 108 + i * 475
        third += [fade_in({'id': f'product-card-{i}', 'kind': 'rect', 'box': [x, 442, 435, 320], 'radius': 12, 'fill': 'FFFFFF', 'role': 'decoration'}, click=1, at=i*130),
                  fade_in(text(f'product-feature-{i}', name, [x+28, 488, 375, 65], 38, 'body'), click=1, at=i*130),
                  fade_in(text(f'product-detail-{i}', description, [x+28, 590, 375, 115], 30, color=MUTED), click=1, at=i*130+100)]
    return {'version': 1, 'title': '产品介绍 · 原生演示示例', 'canvas': {'width': 1600, 'height': 900, 'fps': 30},
            'theme': {'font': 'Noto Sans CJK SC', 'latin_font': 'Space Grotesk SemiBold', 'background': PAPER, 'foreground': INK, 'accent': '4460DA'},
            'slides': [slide('product-compare', first, 1, 'PRODUCT / EDITABLE PRESENTATION', click=True),
                       slide('product-connect', second, 2, 'PRODUCT / SAME OBJECT', morph=True),
                       slide('product-deliver', third, 3, 'PRODUCT / HANDOFF', click=True)]}


def progress():
    palette = Palette(paper=PAPER, ink=INK, muted=MUTED, accent='00766A', secondary='A8512E')
    chart = bar_chart('milestone', ['设计', '联调', '验收'], [85, 60, 35], [910, 350, 540, 300], [0, 100], '完成度（%）', palette=palette)
    token = {'id': 'delivery-marker', 'kind': 'ellipse', 'box': [170, 620, 140, 140], 'fill': 'B76A24', 'role': 'visual'}
    first = [heading('progress-heading-a', '阶段进展，\n用同一尺度比较。', [108, 184, 650, 195]),
             text('progress-purpose', '先看已完成的工作，\n再看需要推进的环节。', [112, 420, 670, 105], 30),
             settled_drift(token, duration=2000, rx=7, ry=8),
             text('progress-marker-caption', '同一项交付', [120, 784, 430, 45], 25, 'caption', MUTED), *chart.objects]
    second_token = {**token, 'box': [1240, 530, 180, 180]}
    second = [heading('progress-heading-b', '让交付沿着\n同一条路径前进。', [108, 180, 1350, 195])]
    for i, title in enumerate(['设计确认', '接口联调', '验收发布']):
        x = 120 + i*520
        second.append(text(f'progress-stage-{i}', title, [x, 420, 360, 65], 37, 'body', align='center'))
        if i < 2:
            second.append(segment(f'progress-link-{i}', [x+300, 620], [x+540, 620], GRID, 3))
    second += [settled_drift(second_token, at=350, duration=2000, rx=7, ry=8),
               text('progress-flow-note', '每一步都有明确输入、负责人和可核对的结束状态。', [112, 755, 1380, 55], 28)]
    third = [heading('progress-heading-c', '下一步，把依赖说清楚。', [108, 184, 1380, 110], 64),
             text('progress-next-subtitle', '围绕实际阻碍分配行动，避免只列完成百分比。', [112, 315, 1380, 55], 30, color=MUTED)]
    for i, (topic, owner, action) in enumerate([
        ('范围收敛', '产品', '确认边界与验收标准'),
        ('联调窗口', '研发', '锁定接口及可用时间'),
        ('发布依赖', '测试', '核对版本与回归记录'),
    ]):
        y = 435+i*118
        third += [segment(f'progress-row-line-{i}', [108, y+94], [1492, y+94], GRID, 1.5),
                  fade_in(text(f'progress-topic-{i}', topic, [120, y+18, 350, 62], 35, 'body'), click=1, at=i*150),
                  fade_in(text(f'progress-owner-{i}', owner, [590, y+18, 230, 62], 33, 'body', MUTED), click=1, at=i*150),
                  fade_in(text(f'progress-action-{i}', action, [930, y+18, 550, 62], 33, 'body'), click=1, at=i*150)]
    return {'version': 1, 'title': '项目进展 · 交付流程示例', 'canvas': {'width': 1600, 'height': 900, 'fps': 30},
            'theme': {'font': 'Noto Sans CJK SC', 'latin_font': 'Space Grotesk SemiBold', 'background': PAPER, 'foreground': INK, 'accent': 'B76A24'},
            'slides': [slide('progress-overview', first, 1, 'PROJECT / STATUS', click=True),
                       slide('progress-flow', second, 2, 'PROJECT / DELIVERY', morph=True),
                       slide('progress-actions', third, 3, 'PROJECT / NEXT ACTIONS', click=True)]}


if __name__ == '__main__':
    for name, doc in [('product-intro.json', product()), ('project-update.json', progress())]:
        path = ROOT / 'examples' / name
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(path)
