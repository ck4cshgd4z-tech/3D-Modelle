#!/usr/bin/env python3
"""Erzeugt aus quelle/foto.jpg die Praegewerkzeuge (Matrize + Patrizen) als STL/3MF.

Aufruf (aus dem Projektordner leder-praegung-auto):
    python3 generator/generate.py                       # Standard: 90 mm, Leder 1.2/1.6/2.0 mm
    python3 generator/generate.py --laenge 110 --leder 1.8
    python3 generator/generate.py --schnell             # grobes Raster, nur zum Testen
"""
import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dies  # noqa: E402
import mesh  # noqa: E402
import relief  # noqa: E402
import shapes  # noqa: E402

VERSION = "1.1.0"


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.1f}s] {msg}", flush=True)


def fmt_mm(g):
    return f"{g:.1f}".replace(".", ",")


def save_previews(out, F, outer, Zm, Zps, X, Y, p, img_bgr, F_px, info):
    res = p.res
    # Relief (Sichtseite, wie im Foto) neben dem Foto
    r = relief.hillshade(F, res)
    rows = np.where(np.abs(Y[:, 0]) <= p.blank_h / 2)[0]
    cols = np.where(np.abs(X[0]) <= p.blank_w / 2)[0]
    r_crop = r[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    x0, y0, x1, y1 = info["bbox_px"]
    photo = cv2.cvtColor(img_bgr[max(0, y0 - 10):y1 + 10, max(0, x0 - 10):x1 + 10], cv2.COLOR_BGR2GRAY)
    lut = np.array([255 * ((i / 255) ** 0.5) for i in range(256)], np.uint8)
    photo = cv2.LUT(photo, lut)
    photo = cv2.resize(photo, (r_crop.shape[1], int(photo.shape[0] * r_crop.shape[1] / photo.shape[1])))
    cv2.imwrite(str(out / "vorschau_vergleich_foto_relief.png"), np.vstack([photo, r_crop]))

    def tinted(Z, tint):
        h = relief.hillshade(Z, res).astype(np.float32) / 255
        rgb = np.dstack([h * tint[2], h * tint[1], h * tint[0]])
        mask = dies.plate_mask(X, Y, p)
        rgb[~mask] = (0.96, 0.96, 0.96)
        return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

    cv2.imwrite(str(out / "vorschau_matrize.png"), tinted(Zm, (0.93, 0.80, 0.62)))
    for g, Zp in Zps.items():
        cv2.imwrite(str(out / f"vorschau_patrize_leder-{g:.1f}mm.png"), tinted(Zp, (0.62, 0.78, 0.93)))

    # 3D-Schraegansicht beider Werkzeuge (Reliefbereich)
    g_mid = sorted(Zps)[len(Zps) // 2]
    region = (p.blank_w / 2 + 2, p.blank_h / 2 + 2)
    views = [oblique_render(Zm, X, Y, res, (0.86, 0.74, 0.58), region),
             oblique_render(Zps[g_mid], X, Y, res, (0.58, 0.72, 0.88), region)]
    w = max(v.shape[1] for v in views)
    views = [np.pad(v, ((0, 0), (0, w - v.shape[1]), (0, 0)), constant_values=255) for v in views]
    img3d = np.vstack(views)
    fs = w / 1400.0
    for txt, y in (("Matrize (Negativ) - Druckausrichtung, spiegelverkehrt", int(36 * fs)),
                   (f"Patrize (Positiv) - Leder {g_mid:.1f} mm", views[0].shape[0] + int(36 * fs))):
        cv2.putText(img3d, txt, (int(16 * fs), y), cv2.FONT_HERSHEY_SIMPLEX, fs, (60, 60, 60),
                    max(1, int(2 * fs)), cv2.LINE_AA)
    cv2.imwrite(str(out / "vorschau_3d.png"), img3d)

    # Querschnitte in Pressstellung (fuer die mittlere Lederstaerke)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    g = sorted(Zps)[len(Zps) // 2]
    stop = p.stop_factor * g
    fig, axes = plt.subplots(3, 1, figsize=(11, 4.6))
    for ax, yv in zip(axes, (10.0, 0.0, -10.0)):
        i = int(np.argmin(np.abs(Y[:, 0] - yv)))
        x = X[i]
        sel = np.abs(x) <= p.blank_w / 2 + 3
        zp = Zps[g][i] - p.patrize_base                       # Patrize, Nahtrand-Ebene = 0
        zm_face = (stop - g) + g + F[i]                        # Matrizenflaeche (Anschlag beruecksichtigt)
        ax.fill_between(x[sel], -2.5, zp[sel], color="#8fb3d9", label="Patrize")
        ax.fill_between(x[sel], zp[sel], zm_face[sel], color="#c8a27a", alpha=0.85,
                        label=f"Leder {fmt_mm(g)} mm (gepresst bis Anschlag {fmt_mm(stop)} mm)")
        ax.fill_between(x[sel], zm_face[sel], zm_face[sel].max() + 1.5, color="#e2c79c", label="Matrize")
        ax.set_xlim(-p.blank_w / 2 - 3, p.blank_w / 2 + 3)
        ax.set_ylim(-1, zm_face[sel].max() + 1.2)
        ax.set_aspect("equal")
        ax.set_title(f"Schnitt bei y = {yv:+.0f} mm", fontsize=9)
        ax.tick_params(labelsize=7)
    axes[0].legend(fontsize=7, loc="upper right")
    axes[-1].set_xlabel("x [mm] (Blick auf die Sichtseite, Front links)", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "vorschau_querschnitt_pressstellung.png", dpi=130)
    plt.close(fig)


def oblique_render(Z, X, Y, res, tint, region, elev_deg=40):
    """Schraegansicht (Blick von vorne-oben) per Horizont-Verfahren je Spalte: Waende werden
    automatisch gefuellt, keine GPU noetig. region = (x_halb, y_halb) in mm um die Mitte."""
    cols = np.where(np.abs(X[0]) <= region[0])[0]
    rows = np.where(np.abs(Y[:, 0]) <= region[1])[0]
    Zc = Z[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    Yc = Y[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    gy, gx = np.gradient(Zc, res)
    n = np.dstack([-gx, gy, np.ones_like(Zc)])            # Zeilen laufen in -y
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    light = np.array([-0.45, 0.35, 0.82])
    shade = 0.25 + 0.75 * np.clip(n @ (light / np.linalg.norm(light)), 0, 1)
    e = np.radians(elev_deg)
    ppm = 1.0 / res
    V = ((Yc - Yc.min()) * np.sin(e) + Zc * np.cos(e)) * ppm
    V, shade = V[::-1], shade[::-1]                       # von vorne (kleines y) nach hinten
    R = np.maximum.accumulate(V, axis=0)
    Hpx = int(np.ceil(R.max())) + 2
    img = np.full((Hpx, V.shape[1], 3), 255, np.uint8)
    ps = np.arange(Hpx, dtype=np.float64)
    tint = np.array(tint[::-1]) * 255
    for j in range(V.shape[1]):
        k = np.searchsorted(R[:, j], ps)                  # erste Zeile, die Pixel p erreicht
        ok = k < R.shape[0]
        col = np.full((Hpx, 3), 255.0)
        col[ok] = shade[k[ok], j][:, None] * tint
        img[::-1, j] = col.astype(np.uint8)
    return img


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


def run_checks(F, closeds, outer, Zm, Zps, rels, X, Y, p, meshes):
    """Automatische Pruefungen; liefert Liste (Name, ok, Detail)."""
    res = []
    for name, m in meshes.items():
        rep = mesh.mesh_report(m)
        ok = rep["watertight"] and rep["winding_consistent"] and rep["volume_ok"]
        res.append((f"Netz {name}: wasserdicht/mannigfaltig", ok, rep))
    # Lederspalt in Pressstellung: vertikaler Spalt zur (geschlossenen) Formflaeche
    # >= Normalenabstand >= min_gap_factor*g. Schmale Rillen verdichten das Leder gezielt;
    # die staerkste Verdichtung (inkl. Anschlag) wird geprueft (<= 50 %, wie beim Punzieren).
    inside = outer | (np.abs(F) > 1e-4)
    for g, rel in rels.items():
        gap = (g + closeds[g]) - rel
        gmin = float(gap[inside].min())
        stop = p.stop_factor * g
        squeeze = 1 - float(((stop + F) - rel)[inside].min()) / g
        res.append((f"Spalt Leder {fmt_mm(g)} mm >= {p.min_gap_factor:.2f}*g", gmin >= p.min_gap_factor * g - 1e-3,
                    dict(min_vertikal_mm=round(gmin, 3), median_mm=round(float(np.median(gap[inside])), 3))))
        res.append((f"Verdichtung an Rillen Leder {fmt_mm(g)} mm <= 50 %", squeeze <= 0.50,
                    dict(max_verdichtung=f"{squeeze * 100:.0f} %")))
    # Stifte vs. Bohrungen (Matrize gewendet) und Lederzuschnitt
    for (cx, cy, d) in p.pins:
        i = int(np.argmin(np.abs(Y[:, 0] - cy)))
        j = int(np.argmin(np.abs(X[0] - (-cx))))
        hole_ok = abs(Zm[i, j] - (p.matrize_flange - p.hole_depth)) < 1e-3
        clear = (abs(cx) - p.collar_r > p.blank_w / 2) or (abs(cy) - p.collar_r > p.blank_h / 2)
        res.append((f"Stift ({cx:+.0f},{cy:+.0f}) Ø{d:.0f}: Bohrung vorhanden, ausserhalb Zuschnitt",
                    bool(hole_ok and clear), dict(bohrung=bool(hole_ok), frei=bool(clear))))
    # Stift taucht in Endstellung nicht durch den Matrizenboden (Sackloch)
    for g in Zps:
        depth_needed = p.pin_h - p.stop_factor * g
        res.append((f"Stifteintauchtiefe Leder {fmt_mm(g)} mm < Sacklochtiefe", depth_needed < p.hole_depth - 0.3,
                    dict(eintauchen_mm=round(depth_needed, 2), sackloch_mm=p.hole_depth)))
    # Patch passt in den Zuschnitt
    ys, xs = np.where(outer)
    w = (xs.max() - xs.min()) * p.res
    h = (ys.max() - ys.min()) * p.res
    res.append(("Patch passt in Lederzuschnitt", w < p.blank_w - 4 and h < p.blank_h - 4,
                dict(patch_mm=[round(w, 2), round(h, 2)], zuschnitt_mm=[p.blank_w, p.blank_h])))
    res.append(("Matrize Mindest-Bodenstaerke >= 3 mm", float(Zm.min()) >= 0.49 and
                float((p.matrize_flange - F.max())) >= 3.0, dict(boden_mm=round(float(p.matrize_flange - F.max()), 2))))
    return res


def decimation_error(m, Z, mask, X, Y, n=60000, seed=1):
    """Max. Abweichung des reduzierten Netzes vom Hoehenfeld (Stichprobe der Oberseite)."""
    try:
        rng = np.random.default_rng(seed)
        ii = np.argwhere(mask)
        ii = ii[rng.choice(len(ii), size=min(n, len(ii)), replace=False)]
        pts = np.column_stack([X[ii[:, 0], ii[:, 1]], Y[ii[:, 0], ii[:, 1]], Z[ii[:, 0], ii[:, 1]]])
        _, dist, _ = m.nearest.on_surface(pts)
        return float(np.percentile(dist, 99.9)), float(dist.max())
    except Exception as exc:  # rtree fehlt o. ae.
        log(f"Abweichungspruefung uebersprungen: {exc}")
        return None, None


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
    F = Fb - gr
    pmask = dies.plate_mask(X, Y, p)

    log("Matrize (Negativ) aufbauen")
    Zm = dies.build_matrize(F, X, Y, p, "MATRIZE - NEGATIV")
    Zps, rels, closeds = {}, {}, {}
    for lg in a.leder:
        log(f"Patrize (Positiv) fuer Leder {lg} mm aufbauen (Kugel-Versatz)")
        Zps[lg], rels[lg], closeds[lg] = dies.build_patrize(Fb, lg, X, Y, p, f"PATRIZE - LEDER {lg:.1f} MM")

    meshes, files = {}, []
    stem_m = f"Matrize_Negativ_{a.laenge:.0f}mm"
    items = [(stem_m, Zm)] + [(f"Patrize_Positiv_{a.laenge:.0f}mm_Leder-{lg:.1f}mm", Zps[lg]) for lg in a.leder]
    errors = {}
    for stem, Z in items:
        log(f"Netz erzeugen: {stem}")
        v, f = mesh.heightfield_mesh(Z, pmask, X, Y)
        m = mesh.decimate_watertight(v, f, target)
        meshes[stem] = m
        errors[stem] = decimation_error(m, Z, pmask, X, Y)
        mesh.export(m, out / stem)
        files += [stem + ".stl", stem + ".3mf"]
        log(f"  {len(m.faces):,} Dreiecke, Abweichung p99.9/max = {errors[stem]}")

    log("Vorschauen, Schablone, Pruefbericht")
    save_previews(out, F, outer, Zm, Zps, X, Y, p, img, F_px, info)
    save_svg(out, outer_px, info, p)
    checks = run_checks(F, closeds, outer, Zm, Zps, rels, X, Y, p, meshes)
    for name, (e999, emax) in errors.items():
        if e999 is not None:
            checks.append((f"Reduktionsfehler {name} (p99.9 < 0.03 mm)", e999 < 0.03,
                           dict(p99_9_mm=round(e999, 4), max_mm=round(emax, 4))))
    report = dict(version=VERSION, laenge_mm=a.laenge, leder_mm=a.leder,
                  patch_mm=[round(info["patch_w_mm"], 2), round(info["patch_h_mm"], 2)],
                  relief_mm=[round(float(F.min()), 3), round(float(F.max()), 3)],
                  parameter=asdict(p), dateien=files,
                  pruefungen=[dict(name=n, ok=bool(ok), detail=d) for n, ok, d in checks])
    (out / "pruefbericht.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(("  OK    " if ok else "  FEHLER") + f"  {n}  {d}")
    log("fertig" if not failed else f"{len(failed)} Pruefung(en) fehlgeschlagen")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
