from __future__ import annotations

from typing import Dict, Tuple, Optional

try:
    import webcolors
except Exception:  # pragma: no cover
    webcolors = None  # type: ignore

try:
    from colormath.color_conversions import convert_color
    from colormath.color_objects import sRGBColor, LabColor
    from colormath.color_diff import delta_e_cie2000
except Exception:  # pragma: no cover
    convert_color = None  # type: ignore
    sRGBColor = None  # type: ignore
    LabColor = None  # type: ignore
    delta_e_cie2000 = None  # type: ignore


def _to_rgb(color_name: str) -> Optional[Tuple[int, int, int]]:
    if not webcolors:
        return None
    try:
        return webcolors.name_to_rgb(color_name)
    except Exception:
        # naive parse for hex like #RRGGBB
        if color_name.startswith("#") and len(color_name) == 7:
            try:
                r = int(color_name[1:3], 16)
                g = int(color_name[3:5], 16)
                b = int(color_name[5:7], 16)
                return (r, g, b)
            except Exception:
                return None
        return None


def _rgb_to_lab(rgb: Tuple[int, int, int]) -> Optional[LabColor]:
    if not convert_color or not sRGBColor:
        return None
    srgb = sRGBColor(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    return convert_color(srgb, LabColor)


def infer_palette(items: Dict[str, Dict]) -> Dict[str, str]:
    """Return a simple palette mapping category -> color string if available."""
    palette: Dict[str, str] = {}
    for cat, meta in items.items():
        color = (meta or {}).get("color")
        if isinstance(color, str):
            palette[cat] = color.lower()
    return palette


def palette_score(palette: Dict[str, str]) -> float:
    """Score how harmonious the palette is using CIEDE2000 distances.

    Fallback: if libraries unavailable or colors missing, return neutral 0.5.
    """
    if not palette:
        return 0.5
    if not (convert_color and sRGBColor and LabColor and delta_e_cie2000 and webcolors):
        return 0.5

    labs: Dict[str, LabColor] = {}
    for k, name in palette.items():
        rgb = _to_rgb(name)
        if rgb is None:
            continue
        lab = _rgb_to_lab(rgb)
        if lab is not None:
            labs[k] = lab

    keys = list(labs.keys())
    if len(keys) < 2:
        return 0.6

    # Compute pairwise distances and convert to a normalized harmony score
    dists = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            d = delta_e_cie2000(labs[keys[i]], labs[keys[j]])
            dists.append(float(d))

    if not dists:
        return 0.6

    # Empirical normalization: lower delta E -> higher harmony
    avg = sum(dists) / len(dists)
    # Map avg distance ~[0..100] to [1..0]
    score = max(0.0, min(1.0, 1.0 - (avg / 100.0)))
    # Slightly center towards 0.6 to avoid extremes
    return 0.4 + 0.6 * score
