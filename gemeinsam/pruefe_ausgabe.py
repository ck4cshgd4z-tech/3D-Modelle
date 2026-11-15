#!/usr/bin/env python3
"""Unabhaengige Pruefung exportierter Werkzeugsaetze (laedt STL/3MF neu von der Platte).

Prueft: geschlossen/mannigfaltig, Masse, STL == 3MF, Stifte <-> Sackloecher, und dass Patrize und
gewendete Matrize ineinanderpassen (Korrelation der Reliefs, gespiegelt vs. ungespiegelt; bei
spiegelsymmetrischer Patrize nur die Formkorrelation).
Aufruf: python3 gemeinsam/pruefe_ausgabe.py <ausgabe-ordner> (oder ueber generator/check.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.ndimage import uniform_filter


def heights(m, xs, ys):
    """Oberflaechenhoehe per senkrechtem Strahl von oben."""
    X, Y = np.meshgrid(xs, ys)
    origins = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, 50.0)])
    dirs = np.tile([0.0, 0.0, -1.0], (X.size, 1))
    locs, idx_ray, _ = m.ray.intersects_location(origins, dirs, multiple_hits=False)
    Z = np.full(X.size, np.nan)
    Z[idx_ray] = locs[:, 2]
    return Z.reshape(X.shape)


def main(folder):
    folder = Path(folder)
    rep = json.loads((folder / "pruefbericht.json").read_text(encoding="utf-8"))
    par = rep["parameter"]
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print(("  OK     " if ok else "  FEHLER ") + name + (f"  ({detail})" if detail else ""))

    meshes = {}
    for f in rep["dateien"]:
        if not (folder / f).exists():          # z. B. STL nicht im Git-Repo -> nur 3MF pruefen
            print(f"  --     {f} nicht vorhanden (uebersprungen)")
            continue
        m = trimesh.load(folder / f, force="mesh")
        meshes[f] = m
        ext = m.extents
        check(f"{f}: geschlossen & mannigfaltig", m.is_watertight and m.is_winding_consistent and m.is_volume,
              f"{len(m.faces):,} Dreiecke")
        check(f"{f}: Plattenmass {par['plate_w']} x {par['plate_h']} mm",
              abs(ext[0] - par["plate_w"]) < 0.05 and abs(ext[1] - par["plate_h"]) < 0.05,
              f"{ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} mm")
    stems = sorted({f.rsplit(".", 1)[0] for f in rep["dateien"]})
    def get(stem):
        m = meshes.get(stem + ".stl")
        return m if m is not None else meshes.get(stem + ".3mf")

    for s in stems:
        if s + ".stl" in meshes and s + ".3mf" in meshes:
            a, b = meshes[s + ".stl"], meshes[s + ".3mf"]
            check(f"{s}: STL und 3MF identisch (Volumen)", abs(a.volume - b.volume) / a.volume < 1e-4,
                  f"{a.volume / 1000:.3f} / {b.volume / 1000:.3f} cm3")

    mat = get([s for s in stems if "Matrize_" in s][0])
    flange = par["matrize_flange"]
    xs = np.linspace(-par["blank_w"] / 2 + 1, par["blank_w"] / 2 - 1, 140)
    ys = np.linspace(-par["blank_h"] / 2 + 1, par["blank_h"] / 2 - 1, 70)
    depth_m = flange - heights(mat, xs, ys)                      # Kavitaetstiefe (Druckausrichtung)
    for s in stems:
        if "Patrize_" not in s:
            continue
        pat = get(s)
        relief_p = heights(pat, xs, ys) - par["patrize_base"]
        ok = ~np.isnan(relief_p) & ~np.isnan(depth_m)
        mirrored = depth_m[:, ::-1]                              # Matrize zurueckwenden
        okm = ok & ~np.isnan(mirrored)
        c_m = np.corrcoef(relief_p[okm], mirrored[okm])[0, 1]
        # Detailvergleich (Hochpass), damit die grobe Kissenform das Ergebnis nicht dominiert
        hp = lambda a: np.nan_to_num(a) - uniform_filter(np.nan_to_num(a), 7)
        d_m = np.corrcoef(hp(relief_p)[okm], hp(mirrored)[okm])[0, 1]
        d_n = np.corrcoef(hp(relief_p)[ok], hp(depth_m)[ok])[0, 1]
        sym = np.corrcoef(np.nan_to_num(relief_p).ravel(), np.nan_to_num(relief_p[:, ::-1]).ravel())[0, 1]
        if sym > 0.98:   # Patrize spiegelsymmetrisch (z. B. glattes Kissen): Richtung egal
            check(f"{s}: passt in gewendete Matrize (Form > 0.9, Patrize symmetrisch)", c_m > 0.9,
                  f"Form {c_m:.3f}, Symmetrie {sym:.3f}")
        else:
            check(f"{s}: passt in gewendete Matrize (Form > 0.9, Detail gespiegelt >> ungespiegelt)",
                  c_m > 0.9 and d_m - d_n > 0.3, f"Form {c_m:.3f}, Detail {d_m:.3f} vs. ungespiegelt {d_n:.3f}")
        for (px, py, d) in par["pins"]:
            h_pin = heights(pat, np.array([px]), np.array([py]))[0, 0]
            h_hole = heights(mat, np.array([-px]), np.array([py]))[0, 0]
            check(f"{s}: Stift ({px:+.0f},{py:+.0f}) Ø{d:.0f} trifft Sackloch",
                  abs(h_pin - (par["patrize_base"] + par["pin_h"])) < 0.05 and
                  abs(h_hole - (flange - par["hole_depth"])) < 0.05,
                  f"Stift {h_pin:.2f} mm, Lochgrund {h_hole:.2f} mm")
    print(f"{sum(results)}/{len(results)} Pruefungen bestanden")
    return 0 if all(results) else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Aufruf: python3 gemeinsam/pruefe_ausgabe.py <ausgabe-ordner>")
    sys.exit(main(sys.argv[1]))
