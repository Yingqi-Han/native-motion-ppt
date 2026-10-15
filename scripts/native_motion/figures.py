"""Data-driven scientific figures built from editable shapes, paths and text."""
import math
import re
import statistics
from dataclasses import dataclass, field

from .recipes import wipe_in, fade_in, reveal_sequence


@dataclass(frozen=True)
class Palette:
    ink: str = "142B31"
    muted: str = "536867"
    grid: str = "D2DCD6"
    accent: str = "00766A"
    secondary: str = "BE5434"
    pale: str = "D2E5DE"
    paper: str = "F4F2EA"
    font: str = "Noto Sans CJK SC"
    numbers: str = "Space Grotesk SemiBold"


@dataclass
class Figure:
    objects: list
    metadata: dict = field(default_factory=dict)


def _prefix(prefix):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,60}", prefix):
        raise ValueError("Figure prefix must be a valid, short native object ID")


def _numbers(values):
    result = list(values)
    if not result or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in result):
        raise ValueError("Figure data must be nonempty and finite")
    return result


def _domain(values, domain):
    low, high = _numbers(domain)
    if low >= high or any(v < low or v > high for v in values):
        raise ValueError("All data must fit the increasing declared domain; values are never clipped")
    return low, high


def _box(box):
    if len(box) != 4 or any(not math.isfinite(v) for v in box) or box[2] <= 0 or box[3] <= 0:
        raise ValueError("Figure box must have finite positive dimensions")
    return box


def label(ident, text, box, size=28, color="142B31", font="Noto Sans CJK SC", **extra):
    return {"id":ident, "kind":"text", "text":str(text), "box":list(box),
            "size":size, "fill":color, "font":font, "role":"label", **extra}


def segment(ident, a, b, color, width=2, **extra):
    x, y = min(a[0], b[0]), min(a[1], b[1])
    w, h = max(.001, abs(a[0]-b[0])), max(.001, abs(a[1]-b[1]))
    return {"id":ident, "kind":"path", "box":[x, y, w, h],
            "d":f"M {a[0]-x} {a[1]-y} L {b[0]-x} {b[1]-y}",
            "fill":"none", "stroke":color, "stroke_width":width,
            "role":"decoration", **extra}


def _axes(prefix, box, domain, unit, palette):
    x, y, w, h = _box(box)
    low, high = domain
    objects = []
    for i in range(5):
        value = low+(high-low)*i/4
        yy = y+h-i*h/4
        objects += [segment(f"{prefix}-grid-{i}", [x, yy], [x+w, yy], palette.grid, 1.5),
                    label(f"{prefix}-tick-{i}", f"{value:g}", [x-100, yy-20, 75, 44],
                          27, palette.muted, palette.numbers, align="right")]
    objects += [segment(f"{prefix}-baseline", [x, y+h], [x+w, y+h], palette.ink, 2),
                label(f"{prefix}-unit", unit, [x, y-125, min(300,w), 48], 29, palette.muted, palette.font)]
    return objects


def bar_chart(prefix, labels, values, box, domain, unit, *, click=1, palette=None):
    """Nonnegative bars share zero and an invariant baseline throughout their reveal."""
    _prefix(prefix)
    palette = palette or Palette()
    values = _numbers(values)
    low, high = _domain(values, domain)
    if low != 0 or any(v < 0 for v in values):
        raise ValueError("This positive-bar recipe requires a zero-based nonnegative domain")
    if len(labels) != len(values):
        raise ValueError("Bar labels and values must have equal lengths")
    x, y, w, h = _box(box)
    spacing = w/len(values)
    width = min(112, spacing*.42)
    objects = _axes(prefix, box, (low, high), unit, palette)
    bars = []
    for i, (name, value) in enumerate(zip(labels, values)):
        cx, height = x+spacing*(i+.5), h*value/high
        ident = f"{prefix}-bar-{i}"
        if height:
            bar = {"id":ident, "kind":"rect", "box":[cx-width/2, y+h-height, width, height],
                   "fill":palette.accent if i < len(values)-1 else palette.secondary, "role":"data"}
            objects.append(wipe_in(bar, at=i*120, click=click))
        else:
            bar = segment(ident, [cx-width/2, y+h], [cx+width/2, y+h], palette.accent, 2, role="data")
            objects.append(fade_in(bar, at=i*120, click=click))
        objects += [label(f"{prefix}-category-{i}", name, [cx-spacing*.45, y+h+26, spacing*.9, 55],
                          32, palette.ink, palette.font, align="center"),
                    fade_in(label(f"{prefix}-value-{i}", f"{value:g}", [cx-95, y+h-height-66, 190, 54],
                                  38, palette.ink, palette.numbers, align="center", role="data"),
                            at=1100+i*120, duration=320, click=click)]
        bars.append({"id":ident, "value":value, "baseline":y+h, "box":bar["box"]})
    return Figure(objects, {"kind":"positive-bar", "prefix":prefix, "box":list(box), "domain":[low, high], "unit":unit,
                            "values":values, "labels":list(labels), "bars":bars,
                            "axes_stay_static":True, "zero_is_a_native_line":True,
                            "reveal":"native wipe from bottom", "geometry_stays_static":True})


def line_chart(prefix, xs, values, box, domain, unit, *, reference=None, click=1, palette=None):
    """Reveal native segments in sample order; never interpolate fictitious observations."""
    _prefix(prefix)
    palette = palette or Palette()
    xs, values = _numbers(xs), _numbers(values)
    if len(xs) != len(values) or len(xs) < 2 or any(b <= a for a, b in zip(xs, xs[1:])):
        raise ValueError("Line samples need matching lengths and strictly increasing x values")
    if reference is not None:
        reference = _numbers(reference)
        if len(reference) != len(xs):
            raise ValueError("Reference and measured series must share x samples")
    low, high = _domain(values+(reference or []), domain)
    x, y, w, h = _box(box)
    def point(i, value):
        return [x+(xs[i]-xs[0])/(xs[-1]-xs[0])*w, y+h-(value-low)/(high-low)*h]
    objects = _axes(prefix, box, (low, high), unit, palette)
    for i, xx in enumerate(xs):
        px = point(i, low)[0]
        objects.append(label(f"{prefix}-x-{i}", f"{xx:g}", [px-50, y+h+24, 100, 48],
                             28, palette.muted, palette.numbers, align="center"))
    points = [point(i, v) for i, v in enumerate(values)]
    if reference is not None:
        for i in range(len(xs)-1):
            objects.append(segment(f"{prefix}-reference-{i}", point(i, reference[i]),
                                   point(i+1, reference[i+1]), palette.muted, 3))
    lines = [segment(f"{prefix}-segment-{i}", points[i], points[i+1], palette.accent, 5, role="data")
             for i in range(len(points)-1)]
    objects += reveal_sequence(lines, click=click, stagger=150, duration=280)
    for i, (px, py) in enumerate(points):
        node = {"id":f"{prefix}-point-{i}", "kind":"ellipse", "box":[px-7, py-7, 14, 14],
                "fill":palette.accent, "role":"data"}
        objects.append(fade_in(node, at=max(0, i-1)*150+180, duration=240, click=click))
    return Figure(objects, {"kind":"sampled-line", "prefix":prefix, "box":list(box), "x":xs, "values":values, "reference":reference,
                            "domain":[low, high], "points":points, "unit":unit,
                            "axes_stay_static":True, "reveal":"native segment fades"})


def dot_plot(prefix, samples, box, domain, unit, *, click=1, summary_click=2, palette=None):
    """Deterministic observation placement; IQR and median computed from supplied data."""
    _prefix(prefix)
    palette = palette or Palette()
    values = {name:_numbers(items) for name, items in samples.items()}
    if not values or any(len(items) < 2 for items in values.values()):
        raise ValueError("Each distribution requires at least two observations")
    low, high = _domain([v for items in values.values() for v in items], domain)
    x, y, w, h = _box(box)
    yy = lambda v: y+h-(v-low)/(high-low)*h
    objects = _axes(prefix, box, (low, high), unit, palette)
    stats = []
    spacing = w/len(values)
    for i, (name, items) in enumerate(values.items()):
        cx = x+spacing*(i+.5)
        color = palette.accent if i == 0 else palette.secondary
        q1, _, q3 = statistics.quantiles(items, n=4, method="inclusive")
        median = statistics.median(items)
        band = {"id":f"{prefix}-iqr-{i}", "kind":"rect", "box":[cx-78, yy(q3), 156, max(.001, yy(q1)-yy(q3))],
                "fill":palette.pale, "role":"data"}
        # Bands are behind dots; the summary waits for its own semantic click.
        if q1 == q3:
            band = segment(band["id"], [cx-78, yy(q1)], [cx+78, yy(q1)], palette.pale, 3, role="data")
        objects.append(fade_in(band, at=0, duration=350, click=summary_click))
        for j, value in enumerate(items):
            # Horizontal displacement only separates points; it is not an extra variable.
            dx = [-48, 21, -12, 47, -31, 4, 36, -5][j % 8]
            dot = {"id":f"{prefix}-observation-{i}-{j}", "kind":"ellipse", "box":[cx+dx-7, yy(value)-7, 14, 14],
                   "fill":color, "role":"data"}
            objects.append(fade_in(dot, at=j*70, duration=280, click=click))
        objects += [label(f"{prefix}-category-{i}", name, [cx-spacing*.45, y+h+26, spacing*.9, 55],
                          32, palette.ink, palette.font, align="center"),
                    fade_in(segment(f"{prefix}-median-{i}", [cx-90, yy(median)], [cx+90, yy(median)], color, 5,
                                    role="data"), at=100, duration=350, click=summary_click),
                    fade_in(label(f"{prefix}-median-label-{i}", f"中位数 {median:g}",
                                  [cx-160, yy(max(items))-65, 320, 54], 32, palette.ink, palette.font,
                                  align="center", role="data"), at=170, duration=350, click=summary_click)]
        stats.append({"label":name, "n":len(items), "values":items, "median":median,
                      "q1":q1, "q3":q3, "quartiles":"inclusive", "center_x":cx})
    return Figure(objects, {"kind":"observations-iqr-median", "prefix":prefix, "box":list(box), "domain":[low, high], "unit":unit,
                            "statistics":stats, "jitter_is_not_data":True, "axes_stay_static":True})


def process_flow(prefix, labels, box, active=0, *, palette=None):
    _prefix(prefix)
    palette = palette or Palette()
    x, y, w, h = _box(box)
    if len(labels) < 2 or not 0 <= active < len(labels):
        raise ValueError("Process needs at least two stages and a valid active index")
    centers = [[x+w*(i+.5)/len(labels), y+h*.56] for i in range(len(labels))]
    objects = []
    for i, (name, (cx, cy)) in enumerate(zip(labels, centers)):
        objects.append(label(f"{prefix}-stage-{i}", name, [cx-220, y, 440, 90], 54,
                             palette.accent if i == active else palette.muted, palette.font, align="center", bold=True))
        if i < len(labels)-1:
            end = centers[i+1][0]-155
            objects += [segment(f"{prefix}-link-{i}", [cx+155, cy], [end, cy], palette.grid, 3),
                        {"id":f"{prefix}-arrow-{i}", "kind":"polygon", "box":[end-15, cy-9, 15, 18],
                         "points":[[0,0],[15,9],[0,18]], "fill":palette.muted, "role":"decoration"}]
    return Figure(objects, {"kind":"process", "centers":centers, "active":active, "labels":list(labels)})


def sample_network(ident, box, *, changed=False, palette=None):
    """An original schematic network, not a physical molecule or scientific model."""
    palette = palette or Palette()
    w, h = box[2:]
    positions = [[.5,.5],[.22,.24],[.77,.2],[.88,.53],[.71,.83],[.29,.79],[.11,.51]]
    edges = [(0,i) for i in range(1,7)]+[(i,i+1 if i<6 else 1) for i in range(1,7)]
    objects = [segment(f"{ident}-bond-{i}", [positions[a][0]*w,positions[a][1]*h],
                       [positions[b][0]*w,positions[b][1]*h], palette.accent, 2)
               for i,(a,b) in enumerate(edges)]
    for i,(px,py) in enumerate(positions):
        radius = w*(.077 if i == 0 else .034)
        color = palette.secondary if i == 0 and changed else palette.accent
        objects.append({"id":f"{ident}-node-{i}", "kind":"ellipse", "box":[px*w-radius,py*h-radius,radius*2,radius*2],
                        "fill":color, "gradient":{"from":palette.pale,"to":color,"angle":55}})
    return {"id":ident,"kind":"group","box":list(box),"objects":objects,"role":"visual"}
