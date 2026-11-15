#!/usr/bin/env python3
"""Erzeugt aus quelle/foto.jpg die Praegewerkzeuge (Matrize + Patrizen) als STL/3MF.

Aufruf (aus dem Projektordner leder-praegung-auto):
    python3 generator/generate.py                       # Standard: 90 mm, Leder 1.2/1.6/2.0 mm
    python3 generator/generate.py --laenge 110 --leder 1.8
    python3 generator/generate.py --schnell             # grobes Raster, nur zum Testen
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
import relief  # noqa: E402
import shapes  # noqa: E402
import werkzeugsatz as ws  # noqa: E402
from werkzeugsatz import log  # noqa: E402

VERSION = "1.1.0"


def save_photo_comparison(out, F, X, Y, p, img_bgr, info):
    """Relief (Sichtseite, wie im Foto) unter dem Foto."""
    res = p.res
    r = ws.hillshade(F, res)
    rows = np.where(np.abs(Y[:, 0]) <= p.blank_h / 2)[0]
    cols = np.where(np.abs(X[0]) <= p.blank_w / 2)[0]
    r_crop = r[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    x0, y0, x1, y1 = info["bbox_px"]
    photo = cv2.cvtColor(img_bgr[max(0, y0 - 10):y1 + 10, max(0, x0 - 10):x1 + 10], cv2.COLOR_BGR2GRAY)
    lut = np.array([255 * ((i / 255) ** 0.5) for i in range(256)], np.uint8)
    photo = cv2.LUT(photo, lut)
    photo = cv2.resize(photo, (r_crop.shape[1], int(photo.shape[0] * r_crop.shape[1] / photo.shape[1])))
    cv2.imwrite(str(out / "vorschau_vergleich_foto_relief.png"), np.vstack([photo, r_crop]))


def save_svg(out, outer_px, info, p):
    """1:1-Schnittschablone (mm): Aussenkontur + Stichlinie, zentriert wie auf den Platten."""
    from scipy import ndimage as ndi
    mmpp = info["mmpp"]
    x0, y0, x1, y1 = info["bbox_px"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    W, H = p.blank_w, p.blank_h

    def contour_path(mask):
        cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
        c = cv2.approxPolyDP(c.astype(np.float32), 0.6, True)[:, 0, :]
        pts = [((px - cx) * mmpp + W / 2, (py - cy) * mmpp + H / 2) for px, py in c]
        return "M " + " L ".join(f"{a:.3f},{b:.3f}" for a, b in pts) + " Z"

    d_out = ndi.distance_transform_edt(outer_px)
    stitch = d_out > info["stitch_px"]
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">
  <title>Schnittschablone Leder-Patch 1:1 (Zuschnitt {W:.0f} x {H:.0f} mm)</title>
  <rect x="0" y="0" width="{W}" height="{H}" fill="none" stroke="#999" stroke-width="0.2"/>
  <path d="{contour_path(outer_px)}" fill="none" stroke="#000" stroke-width="0.25"/>
  <path d="{contour_path(stitch)}" fill="none" stroke="#c00" stroke-width="0.2" stroke-dasharray="1.6,1.0"/>
  <text x="2" y="{H - 2}" font-family="sans-serif" font-size="2.5">schwarz: Schnittkante  rot: Stichlinie  Rahmen: Lederzuschnitt</text>
</svg>
'''
    (out / "schnittschablone_1zu1.svg").write_text(svg, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--foto", default=str(base / "quelle" / "foto.jpg"))
    ap.add_argument("--ausgabe", default=str(base / "ausgabe"))
    ap.add_argument("--laenge", type=float, default=90.0, help="Patch-Laenge in mm (Standard 90)")
    ap.add_argument("--leder", type=float, nargs="+", default=[1.2, 1.6, 2.0], help="Lederstaerken in mm")
    ap.add_argument("--raster", type=float, default=0.08, help="Rasterweite mm")
    ap.add_argument("--dreiecke", type=int, default=450_000, help="Ziel-Dreiecke je Werkzeug")
    ap.add_argument("--schnell", action="store_true", help="grobes Raster fuer Tests")
    ap.add_argument("--kontrollbild", action="store_true", help="nur Overlay der Konturen schreiben")
    a = ap.parse_args()

    out = Path(a.ausgabe)
    out.mkdir(parents=True, exist_ok=True)
    img, g = relief.load_gray(a.foto)
    if a.kontrollbild:
        cv2.imwrite(str(out / "kontrolle_konturen.png"), shapes.draw_overlay(img))
        return 0

    p = dies.DieParams(res=0.2 if a.schnell else a.raster)
    scale = a.laenge / 90.0
    if abs(scale - 1) > 1e-6:          # Platte und Zuschnitt mitskalieren, Stifte in die Ecken
        p.plate_w, p.plate_h = 36 + 90 * scale, 37 + 41.3 * scale
        p.blank_w, p.blank_h = 10 + 90 * scale, 10.7 + 41.3 * scale
        hx, hy = p.plate_w / 2 - 6, p.plate_h / 2 - 6
        p.pins = [(-hx, hy, 8.0), (hx, hy, 6.0), (hx, -hy, 6.0), (-hx, -hy, 6.0)]
    target = 150_000 if a.schnell else a.dreiecke

    log("Patch segmentieren")
    outer_px = relief.segment_patch(g)
    log("Relief aus Foto ableiten (Narbung entfernen, Shape-from-Shading, Linien)")
    Fb_px, gr_px, info = relief.build_relief(g, outer_px, a.laenge)
    F_px = Fb_px - gr_px
    log(f"  Patch {info['patch_w_mm']:.1f} x {info['patch_h_mm']:.1f} mm, Relief {F_px.min():.2f} .. {F_px.max():.2f} mm")

    X, Y = dies.plate_grid(p)
    Fb, outer = dies.relief_to_plate(Fb_px, outer_px, info, X, Y)
    gr, _ = dies.relief_to_plate(gr_px, outer_px, info, X, Y)

    res = ws.build_tool_set(Fb, gr, outer, X, Y, p, a.leder, out, f"{a.laenge:.0f}mm", target,
                            xlabel="x [mm] (Blick auf die Sichtseite, Front links)")
    save_photo_comparison(out, res["F"], X, Y, p, img, info)
    save_svg(out, outer_px, info, p)
    F = res["F"]
    return ws.write_report(out, VERSION, p, res["files"], res["checks"], laenge_mm=a.laenge, leder_mm=a.leder,
                           patch_mm=[round(info["patch_w_mm"], 2), round(info["patch_h_mm"], 2)],
                           relief_mm=[round(float(F.min()), 3), round(float(F.max()), 3)])


if __name__ == "__main__":
    sys.exit(main())
