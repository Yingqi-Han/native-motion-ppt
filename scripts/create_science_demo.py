#!/usr/bin/env python3
"""Five original pages demonstrate data reveals and a controlled scientific process."""
import csv
import hashlib
import json
from pathlib import Path

from native_motion.figures import Palette, bar_chart, dot_plot, label, line_chart, process_flow, sample_network, segment
from native_motion.recipes import fade_in, settled_drift

ROOT = Path(__file__).resolve().parents[1]
P = Palette()


def title(index, text, box, size=96):
    return fade_in(label(f"science-title-{index}", text, box, size, P.ink,
                         "Noto Serif CJK SC", bold=True, role="title", line_height=1.18),
                   at=100, duration=700, dy=36)


def note(index, text, box=(114,730,690,120)):
    return fade_in(label(f"science-note-{index}", text, box, 34, P.muted, P.font,
                         role="body"), at=420, duration=500, dy=12)


def scene(index, name, duration=6000, clicks=None, morph=False):
    return {"id":f"science-{index}", "label":name, "duration":duration,
            "background":P.paper, "clicks":clicks or [],
            "transition":{"kind":"morph" if morph else "fade", "duration":1400 if morph else 360},
            "objects":[label("science-brand", "SCIENCE / MOTION", [108,70,800,45], 25, P.ink, P.numbers, spacing=2.3),
                       label(f"science-folio-{index}", f"{index:02} / 05", [1600,70,212,45], 25, P.muted, P.numbers, align="right"),
                       segment("science-rule", [108,142], [1812,142], P.grid, 1.5),
                       label("science-source", "模拟数据与流程示意，仅用于演示；不代表实验结果。", [112,1004,1500,44],
                             23, P.muted, P.font)]}


def main():
    data = list(csv.DictReader((ROOT/"examples/data/scientific-demo.csv").open(encoding="utf-8")))
    for row in data:
        row["x"], row["value"] = float(row["x"]), float(row["value"])
    slides, manifests = [], []
    box = [920,385,800,425]
    bars = [r for r in data if r["kind"] == "bar"]
    s = scene(1, "共同基线", clicks=[750])
    f = bar_chart("comparison", [r["series"] for r in bars], [r["value"] for r in bars], box,
                  [0,60], "完成时间（s）", palette=P)
    s["objects"] += [title(1, "把比较\n放在一起。", [108,316,710,300], 100),
                     note(1, "共用坐标和基线，\n差异才看得清。"), *f.objects]
    s["notes"] = "一次点击展开三根柱子及其数值。柱子的底部保持在同一基线上。数字来自scientific-demo.csv中的模拟数据。"
    slides.append(s);manifests.append({"slide":1, **f.metadata})

    response = [r for r in data if r["kind"] == "line" and r["series"] == "改变条件后"]
    reference = [r for r in data if r["kind"] == "line" and r["series"] == "参照"]
    s = scene(2, "时间顺序", duration=6500, clicks=[750])
    f = line_chart("response", [r["x"] for r in response], [r["value"] for r in response], box,
                   [0,3.2], "响应（a.u.）", reference=[r["value"] for r in reference], palette=P)
    f.metadata["data_series"]="改变条件后"
    s["objects"] += [title(2, "变化需要\n一段过程。", [108,316,710,300], 100),
                     note(2, "参照保持可见，\n再看变化怎样发生。"), *f.objects,
                     segment("legend-reference-line", [1280,281], [1330,281], P.muted, 3),
                     label("legend-reference", "参照", [1345,258,115,48], 28, P.muted, P.font),
                     segment("legend-response-line", [1500,281], [1550,281], P.accent, 5),
                     label("legend-response", "改变条件后", [1565,258,220,48], 28, P.accent, P.font),
                     label("response-time-unit", "时间（s）", [1490,898,285,48], 28, P.muted, P.font, align="right")]
    s["notes"] = "一次点击，曲线按观测时间逐段淡入，点位保持原始采样值。灰色参照曲线、坐标和刻度始终保持可见。"
    slides.append(s);manifests.append({"slide":2, **f.metadata})

    for i, active in [(3,0), (4,1)]:
        s = scene(i, "固定条件" if i == 3 else "改变因素", duration=5500, morph=i==4)
        f = process_flow("experiment", ["输入条件","受控变化","观察响应"], [120,438,1680,350], active, palette=P)
        pose = [272,506,256,256] if i == 3 else [790,464,340,340]
        subject = settled_drift(sample_network("sample-token", pose, changed=i==4, palette=P),
                                duration=1800, at=100, rx=7, ry=8)
        headline = "先固定条件。" if i == 3 else "再改变一个因素。"
        description = "保持输入一致，才能比较后面的变化。" if i == 3 else "只改变一个因素，再观察它带来的响应。"
        s["objects"] += [title(i, headline, [108,218,1640,170], 108), *f.objects, subject,
                         note(i, description, (114,876,1690,60)),
                         label(f"process-schematic-{i}", "网络结构为程序化示意，不对应真实分子。", [114,946,1500,44],
                               23, P.muted, P.font)]
        s["notes"] = "同一sample-token保持对象与子对象身份；曲线漂移结束后回到静态布局，再进行跨页Morph。示意网络不代表真实分子或实验模型。"
        slides.append(s);manifests.append({"slide":i, **f.metadata, "shared_actor":"sample-token", "actor_box":pose,
                                          "settle_ms":5500-(800 if i==4 else 360)-1900})

    s = scene(5, "分布与中位数", duration=6500, clicks=[750,2100])
    samples = {name:[r["value"] for r in data if r["kind"] == "dot" and r["series"] == name]
               for name in ["条件 A","条件 B"]}
    f = dot_plot("distribution", samples, box, [0,80], "观测值（a.u.）", palette=P)
    s["objects"] += [title(5, "把离散程度\n也交代清楚。", [108,316,710,300], 94),
                     note(5, "每个点是一条观测。\n中位数和分布一起看。"), *f.objects,
                     label("distribution-legend", "色块：四分位区间  ·  短线：中位数", [915,900,885,50],
                           28, P.muted, P.font)]
    s["notes"] = "第一次点击展开观测点，第二次点击展示四分位区间与中位数。中位数和四分位数由原始模拟观测计算；横向错开只用于分开点，不表示额外变量。"
    slides.append(s);manifests.append({"slide":5, **f.metadata})

    document = {"version":1, "title":"Science / Motion · 动态图表与科研流程", "canvas":{"width":1920,"height":1080,"fps":60},
                "theme":{"font":P.font,"latin_font":P.numbers,"background":P.paper,"foreground":P.ink,"accent":P.accent},
                "slides":slides}
    (ROOT/"examples/scientific.json").write_text(json.dumps(document,ensure_ascii=False,indent=2))
    (ROOT/"examples/data/scientific-manifest.json").write_text(json.dumps({"source":"scientific-demo.csv",
         "source_sha256":hashlib.sha256((ROOT/"examples/data/scientific-demo.csv").read_bytes()).hexdigest(),
         "data_status":"simulated demonstration data", "figures":manifests},ensure_ascii=False,indent=2))
    print(ROOT/"examples/scientific.json")


if __name__ == "__main__":
    main()
