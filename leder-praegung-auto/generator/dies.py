"""Relief -> Hoehenfelder der Praegewerkzeuge (Matrize und Patrize) auf einem mm-Raster.

Koordinaten: Plattenmitte = Ursprung, x nach rechts, y nach oben. Array-Zeile 0 = oberer
Plattenrand (groesstes y), Spalte 0 = linker Rand. Hoehe z in mm ueber der Druckplatte.

Pressen (Stapel von unten nach oben):  Patrize (Gesicht oben) | Leder, Narbenseite oben | Matrize
 - Matrize beruehrt die Sichtseite und traegt das volle Detail:   Pressflaeche = F
 - Patrize beruehrt die Fleischseite: F um die Lederstaerke g nach innen versetzt
   (Kugel-Erosion = echter Normalenabstand) + halbes Feindetail, begrenzt so, dass der
   Spalt nirgends unter MIN_GAP_FACTOR * g faellt.
 - Die Matrize wird zum Drucken um die y-Achse gewendet -> im Druckbild spiegelverkehrt.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class DieParams:
    res: float = 0.08              # Rasterweite mm (Duese 0,4 mm -> mehr als ausreichend)
    plate_w: float = 126.0
    plate_h: float = 78.0
    corner_r: float = 4.0
    blank_w: float = 100.0         # empfohlener Lederzuschnitt (muss zwischen die Stifte passen)
    blank_h: float = 52.0
    patrize_base: float = 4.0      # Plattenstaerke der Patrize unter der Nahtrand-Ebene
    matrize_flange: float = 6.5    # Staerke der Matrize auf Nahtrand-Ebene
    detail_beta: float = 0.5       # Anteil Feindetail auf der Patrize
    detail_sigma: float = 0.6      # mm, Trennung grob/fein
    min_gap_factor: float = 0.85   # minimaler Spalt = Faktor * Lederstaerke
    stop_factor: float = 0.85      # Hoehe der Anschlagringe = Faktor * Lederstaerke
    pin_h: float = 6.5             # Stifthoehe ueber Patrizen-Grundflaeche
    pin_chamfer: float = 0.8
    hole_clear: float = 0.25       # radiales Spiel Bohrung/Stift
    hole_depth: float = 6.0        # Sackloch-Tiefe ab Nahtrand-Ebene der Matrize
    hole_chamfer: float = 0.6
    collar_r: float = 5.5          # Anschlagring-Aussenradius
    label_depth: float = 0.4
    # (x, y, Durchmesser) - ein dickerer Stift = Verdrehschutz
    pins: list = field(default_factory=lambda: [(-57.0, 33.0, 8.0), (57.0, 33.0, 6.0),
                                                (57.0, -33.0, 6.0), (-57.0, -33.0, 6.0)])


def plate_grid(p: DieParams):
    nx = int(round(p.plate_w / p.res)) + 1
    ny = int(round(p.plate_h / p.res)) + 1
    xs = -p.plate_w / 2 + np.arange(nx) * p.res
    ys = p.plate_h / 2 - np.arange(ny) * p.res
    X, Y = np.meshgrid(xs, ys)
    return X.astype(np.float32), Y.astype(np.float32)


def plate_mask(X, Y, p: DieParams):
    """Abgerundetes Rechteck (Knotenmaske)."""
    ax = np.abs(X) - (p.plate_w / 2 - p.corner_r)
    ay = np.abs(Y) - (p.plate_h / 2 - p.corner_r)
    d = np.hypot(np.maximum(ax, 0), np.maximum(ay, 0))
    return d <= p.corner_r + 1e-6


def relief_to_plate(F_px, outer_px, info, X, Y):
    """Relief vom Fotoraster auf das Plattenraster (Patch zentriert). Ausserhalb: 0."""
    mmpp = info["mmpp"]
    x0, y0, x1, y1 = info["bbox_px"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    map_x = (cx + X / mmpp).astype(np.float32)
    map_y = (cy - Y / mmpp).astype(np.float32)        # Bildzeilen laufen nach unten
    F = cv2.remap(F_px, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    M = cv2.remap(outer_px.astype(np.float32), map_x, map_y, cv2.INTER_LINEAR,
                  borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return F.astype(np.float32), M > 0.5


def ball_erode(Z, R, res):
    """E(x) = min_{|d|<=R} Z(x+d) - sqrt(R^2-|d|^2): Flaeche im Normalenabstand R darunter."""
    n = int(np.floor(R / res))
    pad = np.pad(Z, n, mode="edge")
    H, W = Z.shape
    out = np.full_like(Z, np.inf)
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            rr = (dx * dx + dy * dy) * res * res
            if rr > R * R:
                continue
            cap = np.sqrt(R * R - rr)
            np.minimum(out, pad[n + dy:n + dy + H, n + dx:n + dx + W] - cap, out=out)
    return out


def patrize_relative(F, g, p: DieParams):
    """Oberflaeche der Patrize relativ zur Nahtrand-Ebene der Lederunterseite."""
    coarse = ball_erode(F, g, p.res) + g
    fine = F - cv2.GaussianBlur(F, (0, 0), p.detail_sigma / p.res)
    limit = ball_erode(F, p.min_gap_factor * g, p.res) + g
    return np.minimum(coarse + p.detail_beta * fine, limit).astype(np.float32)


def _disk_profile(X, Y, cx, cy, r, h_top, chamfer):
    """Zylinder mit Fase oben: Hoehe als Funktion des Radius (nan ausserhalb)."""
    rr = np.hypot(X - cx, Y - cy)
    z = np.minimum(h_top, h_top - chamfer + (r - rr))
    return np.where(rr <= r, z, np.nan)


def _engrave_text(Z, X, Y, text, center_xy, height_mm, depth, p: DieParams):
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale_px = height_mm / p.res
    fs = scale_px / 22.0
    th = max(1, int(round(0.55 / p.res)))
    (tw, tht), _ = cv2.getTextSize(text, font, fs, th)
    m = np.zeros(Z.shape, np.uint8)
    col = int(round((center_xy[0] + p.plate_w / 2) / p.res - tw / 2))
    row = int(round((p.plate_h / 2 - center_xy[1]) / p.res + tht / 2))
    cv2.putText(m, text, (col, row), font, fs, 1, th, cv2.LINE_AA)
    return Z - depth * (m > 0)


def build_patrize(F, g, X, Y, p: DieParams, label):
    rel = patrize_relative(F, g, p)
    Z = p.patrize_base + rel
    stop_h = p.patrize_base + p.stop_factor * g
    for (cx, cy, d) in p.pins:
        ring = np.hypot(X - cx, Y - cy) <= p.collar_r
        collar = np.where(ring, np.minimum(stop_h, stop_h - 0.4 + (p.collar_r - np.hypot(X - cx, Y - cy))), -np.inf)
        Z = np.maximum(Z, collar)
        pin = _disk_profile(X, Y, cx, cy, d / 2, p.patrize_base + p.pin_h, p.pin_chamfer)
        Z = np.where(np.isnan(pin), Z, np.maximum(Z, pin))
    Z = _engrave_text(Z, X, Y, label, (0.0, -(p.plate_h / 2 + p.blank_h / 2) / 2), 3.6, p.label_depth, p)
    return Z.astype(np.float32), rel


def build_matrize(F, X, Y, p: DieParams, label):
    """Druckausrichtung: Gesicht oben, um y-Achse gewendet (x gespiegelt)."""
    Zp = p.matrize_flange - F                 # in Pressausrichtung gerechnet
    Z = Zp[:, ::-1].copy()                    # wenden -> spiegeln in x
    bottom = p.matrize_flange - p.hole_depth
    for (cx, cy, d) in p.pins:
        hx = -cx                              # Stift (cx,cy) liegt nach dem Wenden bei (-cx, cy)
        r = d / 2 + p.hole_clear
        rr = np.hypot(X - hx, Y - cy)
        hole = np.where(rr <= r, bottom, p.matrize_flange - (r + p.hole_chamfer - rr))
        Z = np.where(rr <= r + p.hole_chamfer, np.minimum(Z, hole), Z)
    Z = _engrave_text(Z, X, Y, label, (0.0, -(p.plate_h / 2 + p.blank_h / 2) / 2), 3.6, p.label_depth, p)
    return Z.astype(np.float32)
