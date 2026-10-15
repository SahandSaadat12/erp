"""
Central categorical colour system for every chart (single source of truth).

* 14 clearly different hues, tuned to stay readable on the dark card
  colours (contrast >= 3:1) and still fine on the light themes.
* Deterministic: a key's preferred colour comes from a stable hash (sha1,
  NOT Python's randomised hash()), so colours never change between
  refreshes or app restarts, and the same name gets the same colour in the
  Dashboard and in the Project View whenever it is not colliding.
* Visible keys never share a colour while palette colours remain; collisions
  are resolved by probing with a step that jumps across hues (so the fallback
  is not a near-identical neighbour).  Beyond len(PALETTE) keys a deterministic
  lighter variant of the palette colours is used.
"""

import hashlib

PALETTE = [
    "#4C8DF6",   # blue
    "#22D3EE",   # cyan
    "#2DD4BF",   # teal
    "#4ADE80",   # green
    "#A3E635",   # lime
    "#FACC15",   # yellow
    "#FBA92C",   # amber
    "#FB7C3C",   # orange
    "#F0526B",   # red
    "#F472B6",   # pink
    "#D946EF",   # magenta
    "#A855F7",   # purple
    "#9486F8",   # violet
    "#7B80F5",   # indigo
]

OTHER = "#8B95A7"          # neutral grey for "Other" / unknown buckets
_STEP = 5                  # gcd(5, 14) == 1 -> probing visits every slot, hue-jumping


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(ra[i] + (rb[i] - ra[i]) * t) for i in range(3))


def _slot(key):
    digest = hashlib.sha1(str(key).strip().lower().encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % len(PALETTE)


def _colour(index):
    """index 0..N-1 -> palette; wraps with a lighter deterministic variant."""
    base = PALETTE[index % len(PALETTE)]
    cycle = index // len(PALETTE)
    return base if cycle == 0 else _mix(base, "#FFFFFF", min(0.14 * cycle, 0.7))


def distinct_colors(keys, preferred=None, fixed=None):
    """
    keys      : visible category names, in display order (earlier = higher priority)
    preferred : optional {key: hex} semantic colours (e.g. status colours); honoured
                unless another visible key already took that exact colour
    fixed     : optional {key: hex} always-honoured colours (e.g. {"Other": OTHER});
                these keys never consume palette colours
    returns   : {key: hex}, one entry per key
    """
    preferred = preferred or {}
    fixed = fixed or {}
    result, used = {}, set()

    for key in keys:
        if key in fixed:
            result[key] = fixed[key]
            used.add(fixed[key].lower())

    free = [k for k in keys if k not in fixed]

    # pass 1: semantic preferences (first come, first served)
    for key in free:
        want = preferred.get(key)
        if want and want.lower() not in used:
            result[key] = want
            used.add(want.lower())

    # pass 2: everything else, hash-preferred slot + hue-jumping probe
    taken_slots = {i for i, c in enumerate(PALETTE) if c.lower() in used}
    overflow = 0
    for key in free:
        if key in result:
            continue
        slot = _slot(key)
        for attempt in range(len(PALETTE)):
            candidate = (slot + _STEP * attempt) % len(PALETTE)
            if candidate not in taken_slots:
                taken_slots.add(candidate)
                result[key] = _colour(candidate)
                break
        else:                       # palette exhausted: next lighter variant, in display order
            result[key] = _colour(len(PALETTE) + overflow)
            overflow += 1
    return result


def color_for(key, keys=None):
    """Colour of one key (optionally within the set of visible keys)."""
    keys = list(keys) if keys else [key]
    if key not in keys:
        keys.append(key)
    return distinct_colors(keys)[key]
