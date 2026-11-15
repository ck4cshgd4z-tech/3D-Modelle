#!/usr/bin/env python3
"""Popko-Logo als Leder-Praegewerkzeug (Matrize + Patrizen), zwei Formen:

  logo    komplettes Logo (Ring, POPKO, DESIGN) auf Anhaenger 60 x 30 mm (abgerundet)
  emblem  PKD im Kreis auf rundem Anhaenger Ø 45 mm

Aufruf (aus dem Projektordner logo-anhaenger-popko):
    python3 generator/generate.py                    # beide Formen, Leder 1.2/1.6/2.0 mm
    python3 generator/generate.py --variante emblem --leder 1.6
    python3 generator/generate.py --schnell          # grobes Raster, nur zum Testen
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "gemeinsam"))
import dies  # noqa: E402
import logo  # noqa: E402
import werkzeugsatz as ws  # noqa: E402
from werkzeugsatz import log  # noqa: E402

VERSION = "1.0.0"

VARIANTEN = {
    "logo": dict(
        tag=logo.TagDesign(form="rechteck", width=60.0, height=30.0),
        target_w=48.5,                 # Logobreite: Kissenfeld 52 mm minus Auslauf der Abschraegung
        ring_stroke=0.55,
        strokes_min={"design": 0.42},  # 0,32 mm im Massstab -> druck- und praegbar; Luecken im E bleiben >= 0,4
        include_pkd=False,             # PKD waere nur 0,7 mm hoch -> nicht praegbar (eigene Form "emblem")
        prefix="Popko-Logo_", size_label="60x30mm", sections=(3.0, 0.0, -3.0)),
    "emblem": dict(
        tag=logo.TagDesign(form="kreis", width=45.0, height=45.0),
        target_w=33.0,                 # Ring-Aussendurchmesser
        ring_stroke=0.85,              # wie die Strichstaerke von P, K, D in dieser Groesse
        strokes_min={},
        include_pkd=True,
        prefix="Popko-PKD-Emblem_", size_label="D45mm", sections=(6.0, 0.0, -6.0)),
}


def die_params(t, res, schnell):
    blank_w, blank_h = t.width + 8.0, t.height + 8.0
    plate_w, plate_h = blank_w + 26.0, blank_h + 26.0
    hx, hy = plate_w / 2 - 6, plate_h / 2 - 6
    return dies.DieParams(res=0.12 if schnell else res, plate_w=plate_w, plate_h=plate_h,
                          blank_w=blank_w, blank_h=blank_h, patrize_res=None if schnell else 0.1,
                          pins=[(-hx, hy, 8.0), (hx, hy, 6.0), (hx, -hy, 6.0), (-hx, -hy, 6.0)])


def centroid(mask, origin, hr):
    ii, jj = np.nonzero(mask)
    return origin[0] + (jj.mean() + 0.5) * hr, origin[1] - (ii.mean() + 0.5) * hr


def save_logo_comparison(out, F, logo_plate, X, Y, t, res):
    """Logo-Vorlage (oben) und daraus entstandene Sichtseite (unten), Ausschnitt Anhaenger."""
    cols = np.where(np.abs(X[0]) <= t.width / 2 + 1)[0]
    rows = np.where(np.abs(Y[:, 0]) <= t.height / 2 + 1)[0]
    crop = lambda a: a[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    top = (255 - np.clip(crop(logo_plate), 0, 1) * 200).astype(np.uint8)
    bottom = ws.hillshade(crop(F), res)
    sep = np.full((6, top.shape[1]), 255, np.uint8)
    cv2.imwrite(str(out / "vorschau_vergleich_logo_relief.png"), np.vstack([top, sep, bottom]))


def run_variant(name, cfg, a, svg_groups, ring):
    out = Path(a.ausgabe) / name
    out.mkdir(parents=True, exist_ok=True)
    t = cfg["tag"]
    p = die_params(t, a.raster, a.schnell)
    hr = 0.02 if a.schnell else 0.01
    log(f"[{name}] Logo setzen und Strichstaerken pruefen")
    mask, groups, origin, info = logo.build_logo_masks(svg_groups, ring, name, cfg["target_w"], cfg["ring_stroke"],
                                                       cfg["strokes_min"], cfg["include_pkd"], hr=hr)
    X, Y = dies.plate_grid(p)
    F_form, grooves, outer, logo_plate = logo.build_face(X, Y, p.res, t, mask, origin, hr=hr)
    target = 150_000 if a.schnell else a.dreiecke
    res = ws.build_tool_set(F_form, grooves, outer, X, Y, p, a.leder, out, cfg["size_label"], target,
                            name_prefix=cfg["prefix"], sections=cfg["sections"],
                            xlabel="x [mm] (Blick auf die Sichtseite)")
    checks = res["checks"]
    # Logo-spezifische Pruefungen: Lesrichtung, Strichstaerken, Lage im Kissenfeld
    if name == "logo":
        rx, _ = centroid(groups["ring"], origin, hr)
        px_, py_ = centroid(groups["popko"], origin, hr)
        _, dy_ = centroid(groups["design"], origin, hr)
        checks.append(("Lesrichtung Sichtseite: Ring links, POPKO ueber DESIGN", rx < px_ and py_ > dy_,
                       dict(ring_x=round(rx, 1), popko=[round(px_, 1), round(py_, 1)], design_y=round(dy_, 1))))
    # Emblem: gleiche Abbildung (logo.build_logo_masks) wie beim Logo, dort wird die Lesrichtung
    # geprueft; zusaetzlich Sichtkontrolle in vorschau_vergleich_logo_relief.png
    for g, d in info.items():
        if isinstance(d, dict) and "strich_mm" in d:
            checks.append((f"Mindeststrich {g} >= 0,40 mm (Duese 0,4)", d["strich_mm"] >= 0.40 - 1e-3, d))
    lw, lh = info["logo_mm"]
    field_w = t.width - 2 * t.pillow_from_edge
    checks.append(("Logo liegt im Kissenfeld (mit Auslauf der Abschraegung)",
                   lw + 2 * t.bevel_width <= field_w + 1e-6, dict(logo_mm=[lw, lh], feld_mm=field_w)))

    save_logo_comparison(out, res["F"], logo_plate, X, Y, t, p.res)
    title = f"Schnittschablone Popko {name} 1:1 (Zuschnitt {p.blank_w:.0f} x {p.blank_h:.0f} mm)"
    (out / "schnittschablone_1zu1.svg").write_text(logo.outline_svg(t, p.blank_w, p.blank_h, title), encoding="utf-8")
    F = res["F"]
    return ws.write_report(out, VERSION, p, res["files"], checks, variante=name,
                           anhaenger_mm=[t.width, t.height], form=t.form, leder_mm=a.leder,
                           logo=info, relief_mm=[round(float(F.min()), 3), round(float(F.max()), 3)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = HERE.parent
    ap.add_argument("--svg", default=str(base / "quelle" / "popko_design_logo_pfade.svg"))
    ap.add_argument("--ausgabe", default=str(base / "ausgabe"))
    ap.add_argument("--variante", nargs="+", default=list(VARIANTEN), choices=list(VARIANTEN))
    ap.add_argument("--leder", type=float, nargs="+", default=[1.2, 1.6, 2.0], help="Lederstaerken in mm")
    ap.add_argument("--raster", type=float, default=0.05, help="Rasterweite mm")
    ap.add_argument("--dreiecke", type=int, default=450_000, help="Ziel-Dreiecke je Werkzeug")
    ap.add_argument("--schnell", action="store_true", help="grobes Raster fuer Tests")
    a = ap.parse_args()
    svg_groups, ring = logo.load_logo(a.svg)
    codes = [run_variant(n, VARIANTEN[n], a, svg_groups, ring) for n in a.variante]
    return max(codes)


if __name__ == "__main__":
    sys.exit(main())
