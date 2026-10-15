"""Small native motion recipes with explicit endpoints and preserved source objects."""
import copy
import math


def _finite(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be a finite number >= {minimum}")


def ellipse_path(rx=9, ry=10):
    """Four cubic arcs, position/tangent continuous at every join and the seam."""
    _finite(rx, "rx", .001)
    _finite(ry, "ry", .001)
    k = .5522847498307936
    return [[0, 0], [k*rx, 0], [rx, -ry+k*ry], [rx, -ry],
            [rx, -ry-k*ry], [k*rx, -2*ry], [0, -2*ry],
            [-k*rx, -2*ry], [-rx, -ry-k*ry], [-rx, -ry],
            [-rx, -ry+k*ry], [-k*rx, 0], [0, 0]]


def _timing(at, duration, click):
    _finite(at, "at")
    _finite(duration, "duration", 1)
    if isinstance(click, bool) or not isinstance(click, int) or click < 0:
        raise ValueError("click must be a nonnegative integer")


def settled_drift(obj, duration=1800, at=0, rx=9, ry=10):
    """Return to static layout before a Morph; lecture waiting time cannot change pose."""
    _timing(at, duration, 0)
    if obj.get("animations"):
        raise ValueError("settled_drift expects an unanimated subject")
    result = copy.deepcopy(obj)
    result["animations"] = [{"kind":"move", "at":at, "duration":duration,
                             "path":ellipse_path(rx, ry), "accel":.25,
                             "decel":.25, "ambient":True}]
    return result


def fade_in(obj, at=0, duration=420, click=0, dy=0):
    """Reveal a semantic object; zero displacement is useful for data markers."""
    _timing(at, duration, click)
    if obj.get("animations"):
        raise ValueError("fade_in expects an unanimated object")
    result = copy.deepcopy(obj)
    result["animations"] = [{"kind":"enter", "at":at, "duration":duration,
                             "click":click, "from":[0, dy], "accel":.1, "decel":.65}]
    return result


def anchored_grow(obj, at=0, duration=950, click=0, initial_scale=.06):
    """Legacy compound transform: baseline depends on both channels staying synchronized.

    Kept for explicit experiments; do not use for WPS data bars. Prefer wipe_in.
    """
    _timing(at, duration, click)
    _finite(initial_scale, "initial_scale", .001)
    if initial_scale > 1 or obj.get("animations") or obj.get("rotation", 0):
        raise ValueError("anchored_grow requires an unrotated, unanimated object and scale <= 1")
    if obj.get("kind") not in ("rect", "ellipse", "group"):
        raise ValueError("anchored_grow requires a bounded shape or group")
    result = copy.deepcopy(obj)
    dy = obj["box"][3]*(1-initial_scale)/2
    common = {"at":at, "duration":duration, "click":click, "accel":.1, "decel":.65}
    result["animations"] = [
        {"kind":"enter", **common, "from":[0, dy]},
        {"kind":"scale", **common, "from":[1, initial_scale], "to":[1, 1]},
    ]
    return result


def wipe_in(obj, at=0, duration=1100, click=0, direction="up"):
    """Native directional reveal; the underlying geometry never changes size or position."""
    _timing(at, duration, click)
    if obj.get("animations") or obj.get("rotation",0) or direction not in ("up","down","left","right"):
        raise ValueError("wipe_in expects an unanimated, unrotated object and a valid direction")
    result=copy.deepcopy(obj)
    result["animations"]=[{"kind":"enter","effect":"wipe","direction":direction,
                           "at":at,"duration":duration,"click":click,"from":[0,0],"to":[0,0],
                           "accel":.1,"decel":.65}]
    return result


def reveal_sequence(objects, click=0, at=0, stagger=90, duration=420):
    """Keep geometry fixed while revealing ordered observations or line segments."""
    _finite(stagger, "stagger")
    return [fade_in(obj, at+i*stagger, duration, click) for i, obj in enumerate(objects)]
