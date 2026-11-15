"""Gemeinsame Pipeline fuer Leder-Praegewerkzeuge (Matrize + Patrizen) aller Projekte.

Ein Projekt liefert nur seine Sichtseite auf dem Plattenraster:
    F_form  = Formflaeche (breite Formen, daraus entsteht die Patrize)
    grooves = schmale Rillen/Abschraegungen (nur Matrize, formen durch Verdichtung)
    outer   = Maske der Schnittkontur
Dann erzeugt build_tool_set() Matrize, Patrizen, Netze (STL/3MF), Vorschauen und Pruefungen.
"""
import json
import time
from dataclasses import asdict

import cv2
import numpy as np

import dies
import mesh

_T0 = [time.time()]


def log(msg):
    print(f"[{time.time() - _T0[0]:6.1f}s] {msg}", flush=True)


def fmt_mm(g):
    return f"{g:.1f}".replace(".", ",")


def hillshade(Z, res, az_xy=(-0.5, -0.85), alt_deg=40):
    """Schattierte Ansicht einer Hoehenkarte (Zeilen = von oben nach unten)."""
    gy, gx = np.gradient(Z, res)
    alt = np.radians(alt_deg)
    lx, ly, lz = np.cos(alt) * az_xy[0], np.cos(alt) * az_xy[1], np.sin(alt)
    n = np.dstack([-gx, -gy, np.ones_like(Z)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    s = np.clip(n[..., 0] * lx + n[..., 1] * ly + n[..., 2] * lz, 0, 1)
    return (s ** 1.2 * 235 + 10).astype(np.uint8)


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


def save_tool_previews(out, F, Zm, Zps, X, Y, p, sections=(10.0, 0.0, -10.0),
                       xlabel="x [mm] (Blick auf die Sichtseite)"):
    """Draufsichten, 3D-Schraegansicht und Querschnitte in Pressstellung."""
    res = p.res
    mask = dies.plate_mask(X, Y, p)

    def tinted(Z, tint):
        h = hillshade(Z, res).astype(np.float32) / 255
        rgb = np.dstack([h * tint[2], h * tint[1], h * tint[0]])
        rgb[~mask] = (0.96, 0.96, 0.96)
        return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

    cv2.imwrite(str(out / "vorschau_matrize.png"), tinted(Zm, (0.93, 0.80, 0.62)))
    for g, Zp in Zps.items():
        cv2.imwrite(str(out / f"vorschau_patrize_leder-{g:.1f}mm.png"), tinted(Zp, (0.62, 0.78, 0.93)))

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

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    stop = p.stop_factor * g_mid
    fig, axes = plt.subplots(len(sections), 1, figsize=(11, 1.55 * len(sections)))
    for ax, yv in zip(np.atleast_1d(axes), sections):
        i = int(np.argmin(np.abs(Y[:, 0] - yv)))
        x = X[i]
        sel = np.abs(x) <= p.blank_w / 2 + 3
        zp = Zps[g_mid][i] - p.patrize_base                   # Patrize, Nahtrand-Ebene = 0
        zm_face = stop + F[i]                                 # Matrizenflaeche auf Anschlag
        ax.fill_between(x[sel], -2.5, zp[sel], color="#8fb3d9", label="Patrize")
        ax.fill_between(x[sel], zp[sel], zm_face[sel], color="#c8a27a", alpha=0.85,
                        label=f"Leder {fmt_mm(g_mid)} mm (gepresst bis Anschlag {fmt_mm(stop)} mm)")
        ax.fill_between(x[sel], zm_face[sel], zm_face[sel].max() + 1.5, color="#e2c79c", label="Matrize")
        ax.set_xlim(-p.blank_w / 2 - 3, p.blank_w / 2 + 3)
        ax.set_ylim(-1, zm_face[sel].max() + 1.2)
        ax.set_aspect("equal")
        ax.set_title(f"Schnitt bei y = {yv:+.0f} mm", fontsize=9)
        ax.tick_params(labelsize=7)
    np.atleast_1d(axes)[0].legend(fontsize=7, loc="upper right")
    np.atleast_1d(axes)[-1].set_xlabel(xlabel, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "vorschau_querschnitt_pressstellung.png", dpi=130)
    plt.close(fig)


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
    ys, xs = np.where(outer)
    w = (xs.max() - xs.min()) * p.res
    h = (ys.max() - ys.min()) * p.res
    res.append(("Patch passt in Lederzuschnitt", w < p.blank_w - 4 and h < p.blank_h - 4,
                dict(patch_mm=[round(float(w), 2), round(float(h), 2)], zuschnitt_mm=[p.blank_w, p.blank_h])))
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


def build_tool_set(F_form, grooves, outer, X, Y, p, leders, out, size_label, target_faces,
                   name_prefix="", sections=(10.0, 0.0, -10.0), xlabel="x [mm] (Blick auf die Sichtseite)"):
    """Matrize + Patrizen bauen, als STL/3MF exportieren, Vorschauen und Pruefungen erzeugen.
    Rueckgabe: dict(F, Zm, Zps, files, checks)."""
    F = F_form - grooves
    pmask = dies.plate_mask(X, Y, p)
    log("Matrize (Negativ) aufbauen")
    Zm = dies.build_matrize(F, X, Y, p, "MATRIZE - NEGATIV")
    Zps, rels, closeds = {}, {}, {}
    for lg in leders:
        log(f"Patrize (Positiv) fuer Leder {lg} mm aufbauen (Kugel-Versatz)")
        Zps[lg], rels[lg], closeds[lg] = dies.build_patrize(F_form, lg, X, Y, p, f"PATRIZE - LEDER {lg:.1f} MM")

    meshes, files, errors = {}, [], {}
    items = [(f"{name_prefix}Matrize_Negativ_{size_label}", Zm)]
    items += [(f"{name_prefix}Patrize_Positiv_{size_label}_Leder-{lg:.1f}mm", Zps[lg]) for lg in leders]
    for stem, Z in items:
        log(f"Netz erzeugen: {stem}")
        v, f = mesh.heightfield_mesh(Z, pmask, X, Y)
        m = mesh.decimate_watertight(v, f, target_faces)
        meshes[stem] = m
        errors[stem] = decimation_error(m, Z, pmask, X, Y)
        mesh.export(m, out / stem)
        files += [stem + ".stl", stem + ".3mf"]
        log(f"  {len(m.faces):,} Dreiecke, Abweichung p99.9/max = {errors[stem]}")

    log("Vorschauen und Pruefungen")
    save_tool_previews(out, F, Zm, Zps, X, Y, p, sections, xlabel)
    checks = run_checks(F, closeds, outer, Zm, Zps, rels, X, Y, p, meshes)
    for name, (e999, emax) in errors.items():
        if e999 is not None:
            checks.append((f"Reduktionsfehler {name} (p99.9 < 0.03 mm)", e999 < 0.03,
                           dict(p99_9_mm=round(e999, 4), max_mm=round(emax, 4))))
    return dict(F=F, Zm=Zm, Zps=Zps, files=files, checks=checks)


def write_report(out, version, p, files, checks, **extra):
    """pruefbericht.json schreiben, Ergebnis ausgeben; Rueckgabe Exit-Code (0 = alles OK)."""
    report = dict(version=version, **extra, parameter=asdict(p), dateien=files,
                  pruefungen=[dict(name=n, ok=bool(ok), detail=d) for n, ok, d in checks])
    (out / "pruefbericht.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(("  OK    " if ok else "  FEHLER") + f"  {n}  {d}")
    log("fertig" if not failed else f"{len(failed)} Pruefung(en) fehlgeschlagen")
    return 1 if failed else 0
