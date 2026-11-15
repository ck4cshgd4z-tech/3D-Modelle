"""Pfad-SVG des Popko-Logos -> Sichtseite des Leders auf dem Plattenraster.

Machart (beide Varianten): flacher Nahtrand mit Stich- und Schnittkanten-Rille, darin ein
gepolstertes Feld (Kissen). Das Logo bleibt auf Feldhoehe stehen, rund um die Buchstaben wird
das Leder abgeschraegt eingedrueckt (Kantenabschraegung wie beim Punzieren). So erscheint das
Logo erhaben, auch bei feinen Strichen, die sich nicht von hinten formen lassen.

Rueckgabe wie im Auto-Projekt: F_form (breite Form -> Patrize), grooves (schmale Rillen und
Abschraegungen -> nur Matrize), outer (Schnittkontur).
"""
from dataclasses import dataclass

import cv2
import numpy as np
from scipy import ndimage as ndi
from svgelements import SVG, Close, Line, Move, Path

# Element-IDs der Pfad-SVG (Inkscape: Objekt in Pfad umgewandelt)
GROUPS = {"popko": ["text1"], "design": ["text2", "text3", "text4"],
          "pkd": ["text5", "text6", "text7"]}
RING_ID = "path4"


@dataclass
class TagDesign:
    form: str                  # "rechteck" (abgerundet) oder "kreis"
    width: float               # mm (Kreis: Durchmesser)
    height: float              # mm
    corner_r: float = 6.0
    stitch_from_edge: float = 2.5
    pillow_from_edge: float = 4.0
    pillow_h: float = 0.90
    pillow_lambda: float = 0.8
    pillow_dome: float = 0.15
    bevel_depth: float = 0.38  # Abschraegung direkt an der Buchstabenkante (<= 50 % Verdichtung bei 1,2 mm)
    bevel_width: float = 1.0   # Auslauf der Abschraegung
    counter_full_area: float = 40.0  # mm2: kleinere Innenraeume (O, P, D, Ring) ganz eindruecken
    stitch_depth: float = 0.30
    cut_depth: float = 0.18
    edge_groove: float = 0.22


def _polys(elem, n_curve=24):
    """Pfad -> Liste geschlossener Polygone (mm, SVG-Koordinaten mit y nach unten)."""
    polys, cur = [], []
    for seg in Path(elem).segments():
        if isinstance(seg, Move):
            if len(cur) > 2:
                polys.append(np.array(cur))
            cur = [(seg.end.x, seg.end.y)]
        elif isinstance(seg, (Line, Close)):
            if seg.end is not None:
                cur.append((seg.end.x, seg.end.y))
        else:                                   # Bezier/Bogen: abtasten
            for t in np.linspace(0, 1, n_curve)[1:]:
                q = seg.point(t)
                cur.append((q.x, q.y))
    if len(cur) > 2:
        polys.append(np.array(cur))
    return polys


def load_logo(svg_path):
    """Elemente der SVG in mm (1 SVG-Einheit = 1 mm). Ring als Mittelpunkt/Radius."""
    svg = SVG.parse(str(svg_path), reify=True, ppi=25.4)
    by_id = {e.id: e for e in svg.elements() if getattr(e, "id", None)}
    groups = {g: [p for i in ids for p in _polys(by_id[i])] for g, ids in GROUPS.items()}
    x0, y0, x1, y1 = by_id[RING_ID].bbox()
    ring = dict(cx=(x0 + x1) / 2, cy=(y0 + y1) / 2, r=(x1 - x0) / 2)
    return groups, ring


def _bbox(polys):
    a = np.vstack(polys)
    return a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()


def stroke_width(mask, hr):
    """Typische Strichstaerke (mm) einer Maske: 2 x 97. Perzentil der Innenabstaende."""
    dt = ndi.distance_transform_edt(mask)
    return 2 * float(np.percentile(dt[mask > 0], 97)) * hr if mask.any() else 0.0


def build_logo_masks(groups, ring, variant, target_w, ring_stroke, strokes_min, include_pkd, hr=0.01):
    """Logo-Elemente auf ein hochaufgeloestes Raster (hr mm/px) in Endgroesse setzen.
    variant "logo": Ring + Popko + DESIGN (+ PKD), Breite target_w.
    variant "emblem": Ring + PKD, Ring-Aussendurchmesser target_w.
    Rueckgabe: (Maske gesamt, Gruppenmasken, Raster-Ursprung (x0, y1) in mm, Info)."""
    use = ["popko", "design"] + (["pkd"] if include_pkd else []) if variant == "logo" else ["pkd"]
    # Massstab: Ringstrich in Endmass vorgeben, daraus Quellbreite bestimmen
    if variant == "logo":
        bx0, by0, bx1, by1 = _bbox([p for g in use for p in groups[g]])
        bx0 = min(bx0, ring["cx"] - ring["r"])
        by0, by1 = min(by0, ring["cy"] - ring["r"]), max(by1, ring["cy"] + ring["r"])
        s = (target_w - ring_stroke) / (bx1 - bx0)
    else:
        s = (target_w - ring_stroke) / (2 * ring["r"])
        bx0, bx1 = ring["cx"] - ring["r"], ring["cx"] + ring["r"]
        by0, by1 = ring["cy"] - ring["r"], ring["cy"] + ring["r"]
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    to_mm = lambda pts: np.column_stack([(pts[:, 0] - cx) * s, -(pts[:, 1] - cy) * s])   # y nach oben
    half_w = (bx1 - bx0) * s / 2 + ring_stroke + 3.0
    half_h = (by1 - by0) * s / 2 + ring_stroke + 3.0
    W, H = int(2 * half_w / hr), int(2 * half_h / hr)
    ox, oy = -half_w, half_h                                  # Rasterursprung links oben (mm)
    to_px = lambda q: np.column_stack([(q[:, 0] - ox) / hr, (oy - q[:, 1]) / hr])
    masks, info = {}, dict(scale=s)
    for g in use:
        m = np.zeros((H, W), np.uint8)
        pts = [np.round(to_px(to_mm(p)) * 16).astype(np.int32) for p in groups[g]]
        cv2.fillPoly(m, pts, 1, lineType=cv2.LINE_8, shift=4)
        w0 = stroke_width(m, hr)
        grow = max(0.0, (strokes_min.get(g, 0.0) - w0) / 2)
        if grow > 0:
            m = (ndi.distance_transform_edt(1 - m) * hr <= grow).astype(np.uint8)
        masks[g] = m
        info[g] = dict(strich_original_mm=round(w0, 3), strich_mm=round(stroke_width(m, hr), 3),
                       verstaerkt_mm=round(2 * grow, 3))
    # Ring analytisch
    yy, xx = np.mgrid[0:H, 0:W]
    rx, ry = (ring["cx"] - cx) * s, -(ring["cy"] - cy) * s
    rr = np.hypot(ox + (xx + 0.5) * hr - rx, oy - (yy + 0.5) * hr - ry)
    masks["ring"] = (np.abs(rr - ring["r"] * s) <= ring_stroke / 2).astype(np.uint8)
    info["ring"] = dict(durchmesser_aussen_mm=round(2 * ring["r"] * s + ring_stroke, 2), strich_mm=ring_stroke)
    if "pkd" in masks:
        info["pkd"]["buchstabenhoehe_mm"] = round(3.35 * s, 2)        # P/K/D je 3,35 mm im Original
    total = np.zeros((H, W), np.uint8)
    for m in masks.values():
        total |= m
    info["logo_mm"] = [round((bx1 - bx0) * s + ring_stroke, 2), round((by1 - by0) * s + ring_stroke, 2)]
    return total, masks, (ox, oy), info


def tag_distance(X, Y, t: TagDesign):
    """Abstand nach innen zur Schnittkontur (mm), negativ ausserhalb."""
    if t.form == "kreis":
        return t.width / 2 - np.hypot(X, Y)
    qx = np.abs(X) - (t.width / 2 - t.corner_r)
    qy = np.abs(Y) - (t.height / 2 - t.corner_r)
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)
    return -(outside - t.corner_r)


def build_face(X, Y, res, t: TagDesign, logo_mask, origin, hr=0.01):
    """Sichtseite auf dem Plattenraster: (F_form, grooves, outer, logo_auf_platte)."""
    d = tag_distance(X, Y, t)
    outer = d >= 0
    u = d - t.pillow_from_edge
    F_form = np.where(u > 0, t.pillow_h * np.tanh(u / t.pillow_lambda)
                      + t.pillow_dome * (1 - np.exp(-np.maximum(u, 0) / 4.0)), 0.0)

    # Abschraegung um das Logo (hochaufgeloest rechnen, flaechentreu auf das Plattenraster)
    dl = ndi.distance_transform_edt(1 - logo_mask) * hr
    bevel = np.where(dl < t.bevel_width, t.bevel_depth * np.clip(1 - dl / t.bevel_width, 0, 1) ** 1.5, 0.0)
    # Kleine geschlossene Innenraeume (Punzen von O/P/D, kleiner Ring) ganz eindruecken, sonst
    # bliebe in ihrer Mitte ein stehender "Punkt" uebrig
    lab, n = ndi.label(1 - logo_mask)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    areas = ndi.sum(np.ones_like(lab), lab, range(1, n + 1)) * hr * hr
    small_holes = [k + 1 for k, a in enumerate(areas) if (k + 1) not in border and a < t.counter_full_area]
    if small_holes:
        bevel = np.where(np.isin(lab, small_holes), t.bevel_depth, bevel)
    bevel = np.where(logo_mask > 0, 0.0, bevel).astype(np.float32)
    f = res / hr
    Hh, Wh = logo_mask.shape
    small = cv2.resize(bevel, (int(round(Wh / f)), int(round(Hh / f))), interpolation=cv2.INTER_AREA)
    logo_small = cv2.resize(logo_mask.astype(np.float32), small.shape[::-1], interpolation=cv2.INTER_AREA)
    j0 = int(round((origin[0] - X[0, 0]) / res))
    i0 = int(round((Y[0, 0] - origin[1]) / res))
    grooves = np.zeros_like(X, dtype=np.float32)
    logo_plate = np.zeros_like(X, dtype=np.float32)
    grooves[i0:i0 + small.shape[0], j0:j0 + small.shape[1]] = small
    logo_plate[i0:i0 + small.shape[0], j0:j0 + small.shape[1]] = logo_small

    grooves += t.edge_groove * np.exp(-0.5 * (u / 0.3) ** 2) * (u < 0)
    grooves += t.stitch_depth * np.exp(-0.5 * ((d - t.stitch_from_edge) / 0.25) ** 2) * outer
    grooves += t.cut_depth * np.exp(-0.5 * (d / 0.14) ** 2)
    return F_form.astype(np.float32), grooves.astype(np.float32), outer, logo_plate


def outline_svg(t: TagDesign, blank_w, blank_h, title):
    """1:1-Schablone (mm): Schnittkante, Stichlinie, Lederzuschnitt."""
    cx, cy = blank_w / 2, blank_h / 2

    def shape(inset, style):
        if t.form == "kreis":
            return f'<circle cx="{cx}" cy="{cy}" r="{t.width / 2 - inset:.3f}" {style}/>'
        w, h = t.width - 2 * inset, t.height - 2 * inset
        r = max(t.corner_r - inset, 0.1)
        return (f'<rect x="{cx - w / 2:.3f}" y="{cy - h / 2:.3f}" width="{w:.3f}" height="{h:.3f}" '
                f'rx="{r:.3f}" {style}/>')

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{blank_w}mm" height="{blank_h}mm" viewBox="0 0 {blank_w} {blank_h}">
  <title>{title}</title>
  <rect x="0" y="0" width="{blank_w}" height="{blank_h}" fill="none" stroke="#999" stroke-width="0.2"/>
  {shape(0, 'fill="none" stroke="#000" stroke-width="0.25"')}
  {shape(t.stitch_from_edge, 'fill="none" stroke="#c00" stroke-width="0.2" stroke-dasharray="1.6,1.0"')}
</svg>
'''
