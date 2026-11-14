"""Foto -> Relief-Hoehenkarte der Leder-Sichtseite (Narbenseite).

Ergebnis F(x, y) in mm relativ zur Ebene des Nahtrands (0 mm), auf dem Pixelraster des Fotos.
Positive Werte = erhaben (wie das Auto im Foto), negative = Rillen (Naht, Schnittkante).

Pipeline:
 1. Patch-Kontur segmentieren (Helligkeit + Texturmass, damit der Schlagschatten unten nicht
    mitgenommen wird), Schlaufe/Lasche abtrennen, Kontur glaetten.
 2. Ledernarbung entfernen (iterierter bilateraler Filter + Fast-Global-Smoother): die Narbung
    gehoert zum Leder, nicht zum Werkzeug.
 3. Shape-from-Shading: Helligkeit ~ Flaechenneigung zum Licht (oben), per Poisson-Gleichung zu
    einer Hoehe integriert -> plastische Formen (Sicken, Spiegel, Hutze, Felgen).
 4. Kissenform (Fahrzeug hebt sich vom Nahtrand ab) + nachgezeichnete Tiefenebenen
    + gerichtete Linienerkennung fuer Karosseriefugen (auf druckbare Breite verbreitert).
 5. Nahtrand: Stichrille und Schnittkanten-Rille.
"""
import cv2
import numpy as np
from scipy import ndimage as ndi
from scipy.fft import dctn, idctn

import shapes as S

# --- Gestaltungsparameter (Hoehen in mm, Abstaende in Fotopixeln) -------------------------
FLANGE_PX = 62          # Breite des flachen Nahtrands (Kontur -> Fahrzeugrelief)
STITCH_PX = 36          # Lage der Stichrille, gemessen von der Aussenkante
PILLOW_STEP = 1.35      # Hoehe der Relief-Stufe am Fahrzeugrand
PILLOW_DOME = 0.35      # zusaetzliche Woelbung zur Mitte
SFS_GAIN = 0.38         # Gewicht Shape-from-Shading (pro Standardabweichung)
SFS_LIMIT = 0.75        # weiche Begrenzung des SfS-Anteils
LINE_DEPTH = 0.22       # Tiefe der Karosseriefugen
STITCH_DEPTH = 0.30
CUTLINE_DEPTH = 0.18
EDGE_GROOVE = 0.22      # Trennrille zwischen Nahtrand und Fahrzeug


def load_gray(path):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(path)
    return img, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0


def segment_patch(g):
    """Maske des Leder-Patches ohne Schlaufe/Lasche/Schatten."""
    H, W = g.shape
    gb = cv2.GaussianBlur(g * 255, (0, 0), 2.0)
    hp = g * 255 - cv2.GaussianBlur(g * 255, (0, 0), 2.0)
    local_mean = cv2.GaussianBlur(g * 255, (0, 0), 5) + 8
    texture = cv2.GaussianBlur(np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), 4)) / local_mean, (0, 0), 2)
    m = ((gb < 115) & ((texture > 0.05) | (gb < 22))).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    m = _largest(m)
    m = ndi.binary_fill_holes(m).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    yy, xx = np.mgrid[0:H, 0:W]
    for (x0, y0), (x1, y1), above in ((S.STRAP_CUT[0], S.STRAP_CUT[1], True),
                                      (S.TAB_CUT[0], S.TAB_CUT[1], False)):
        sel = (xx >= x0 - 5) & (xx <= x1 + 5)
        ycut = y0 + (xx - x0) * (y1 - y0) / (x1 - x0)
        m[sel & ((yy < ycut) if above else (yy > ycut))] = 0
    m = _largest(m)
    m = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), 4) > 0.5).astype(np.uint8)
    return m


def _largest(m):
    lab, n = ndi.label(m)
    if n == 0:
        raise RuntimeError("Keine Patch-Kontur gefunden")
    sizes = ndi.sum(m, lab, range(1, n + 1))
    return (lab == 1 + int(np.argmax(sizes))).astype(np.uint8)


def remove_grain(g):
    L = g ** 0.6                       # dunkles Leder aufhellen (wahrnehmungsnah)
    s = L.copy()
    for _ in range(6):
        s = cv2.bilateralFilter(s, -1, 0.05, 4)
    s8 = (np.clip(s, 0, 1) * 255).astype(np.uint8)
    sf = cv2.ximgproc.fastGlobalSmootherFilter(s8, s8, lambda_=25, sigma_color=5).astype(np.float32) / 255
    return s, sf


def _poisson_neumann(div):
    H, W = div.shape
    D = dctn(div, type=2, norm="ortho")
    yy = np.arange(H)[:, None]
    xx = np.arange(W)[None, :]
    den = (2 * np.cos(np.pi * yy / H) - 2) + (2 * np.cos(np.pi * xx / W) - 2)
    den[0, 0] = 1
    U = D / den
    U[0, 0] = 0
    return idctn(U, type=2, norm="ortho")


def shape_from_shading(img, weight, light_dir=(0.2, 1.0), s_lo=1.5, s_hi=60):
    """Licht kommt im Foto von oben (leicht links): Helligkeit ~ Ableitung der Hoehe in
    Lichtrichtung. Gradientenfeld bilden und per Poisson (DCT, Neumann-Rand) integrieren."""
    Lb = (cv2.GaussianBlur(img, (0, 0), s_lo) - cv2.GaussianBlur(img, (0, 0), s_hi)) * weight
    d = np.array(light_dir, np.float32)
    d /= np.linalg.norm(d)
    p, q = Lb * d[0], Lb * d[1]
    div = np.zeros_like(Lb)
    div[:, 1:] += p[:, 1:] - p[:, :-1]
    div[1:, :] += q[1:, :] - q[:-1, :]
    return _poisson_neumann(div)


def oriented_max(a, s_along=6.0, s_across=0.9, nb=24):
    """Gerichtete Filterbank: verbindet unterbrochene Linien, unterdrueckt Narbungspunkte."""
    R = int(3 * s_along)
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    out = np.zeros_like(a)
    for b in range(nb):
        t = b * np.pi / nb
        u = xx * np.cos(t) + yy * np.sin(t)
        v = -xx * np.sin(t) + yy * np.cos(t)
        k = np.exp(-0.5 * (u / s_along) ** 2 - 0.5 * (v / s_across) ** 2)
        out = np.maximum(out, cv2.filter2D(a, -1, k / k.sum()))
    return out


def _soft(m, s=2.0):
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), s)


def build_relief(g, outer, patch_mm):
    """Gibt (F_form, grooves, info) zurueck, mm auf dem Fotoraster.
    Sichtseite F = F_form - grooves. grooves = alle schmalen Rillen (Karosseriefugen, Naht-,
    Trenn- und Schnittkanten-Rille): sie entstehen nur durch die Matrize (Verdichtung wie beim
    Punzieren). F_form = Formflaeche, aus der die Patrize abgeleitet wird."""
    sh = g.shape
    ys, xs = np.where(outer)
    mmpp = patch_mm / float(xs.max() - xs.min())
    s, sf = remove_grain(g)

    d_out = ndi.distance_transform_edt(outer)
    car = (d_out > FLANGE_PX).astype(np.uint8)
    car = (cv2.GaussianBlur(car.astype(np.float32), (0, 0), 6) > 0.5).astype(np.uint8)
    carf = car.astype(np.float32)
    d_c = cv2.GaussianBlur(ndi.distance_transform_edt(car).astype(np.float32), (0, 0), 3) * mmpp

    # 1) Kissenform
    pillow = PILLOW_STEP * np.tanh(d_c / 1.0) + PILLOW_DOME * (1 - np.exp(-d_c / 4.0))

    # 2) Shape-from-Shading
    h = shape_from_shading(sf, cv2.GaussianBlur(carf, (0, 0), 4))
    h = h - cv2.GaussianBlur(h, (0, 0), 80)
    h /= np.std(h[car > 0])
    sfs = SFS_LIMIT * np.tanh(h * SFS_GAIN / SFS_LIMIT)

    # 3) Tiefenebenen aus nachgezeichneten Bereichen
    sem = np.zeros(sh, np.float32)
    mirror = S.ell_mask(sh, S.MIRROR)
    cv2.line(mirror, S.MIRROR_STALK[0], S.MIRROR_STALK[1], 1, 9)
    mirror_d = cv2.dilate(mirror, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    for P in (S.WINDSHIELD, S.WIN_FRONT, S.WIN_REAR):
        sem -= 0.30 * _soft(S.poly_mask(sh, P) * (1 - mirror_d))
    sem += 0.30 * np.tanh(ndi.distance_transform_edt(mirror) * mmpp / 0.5) * _soft(mirror, 1.0)
    for wheel, rim in ((S.WHEEL_F, S.RIM_F), (S.WHEEL_R, S.RIM_R)):
        sem -= 0.20 * _soft(S.ell_mask(sh, wheel), 2.5)
        sem -= 0.20 * _soft(S.ell_mask(sh, rim), 2.0)
    sem -= 0.15 * _soft(S.poly_mask(sh, S.FASCIA), 2.5)
    sem -= 0.25 * _soft(S.poly_mask(sh, S.GRILLE), 1.5)
    sem -= 0.35 * _soft(S.poly_mask(sh, S.INTAKE), 2.0)
    for c, r in S.HEADLIGHTS:
        m = np.zeros(sh, np.uint8)
        cv2.circle(m, c, int(r * 0.5), 1, -1)
        sem -= 0.20 * _soft(m, 1.5)
    # Lamellen (vereinfacht, druckbar)
    slat = np.zeros(sh, np.uint8)
    P0, P1 = np.array(S.INTAKE[0]), np.array(S.INTAKE[2])
    Q0, Q1 = np.array(S.INTAKE[5]), np.array(S.INTAKE[3])
    for t in S.INTAKE_SLATS_T:
        slat = np.maximum(slat, S.line_mask(sh, P0 + (Q0 - P0) * t, P1 + (Q1 - P1) * t, 5))
    slat = np.maximum(slat, S.line_mask(sh, *S.INTAKE_DIVIDER, 9))
    G0, G1 = np.array(S.GRILLE[0]), np.array(S.GRILLE[2])
    H0, H1 = np.array(S.GRILLE[5]), np.array(S.GRILLE[3])
    slat = np.maximum(slat, S.line_mask(sh, G0 + (H0 - G0) * 0.5, G1 + (H1 - G1) * 0.5, 5))
    slat = np.maximum(slat, S.line_mask(sh, *S.GRILLE_DIVIDER, 7))
    slat *= np.maximum(S.poly_mask(sh, S.INTAKE), S.poly_mask(sh, S.GRILLE))
    sem += 0.28 * _soft(slat, 1.2)
    # Felgenspeichen aus der Helligkeit, Radnaben
    rims = np.maximum(S.ell_mask(sh, S.RIM_F), S.ell_mask(sh, S.RIM_R)).astype(np.float32)
    sp = sf - cv2.GaussianBlur(sf, (0, 0), 7)
    sp /= np.std(sp[rims > 0])
    sem += 0.18 * np.tanh(sp / 1.2) * _soft(rims, 1.5)
    for c, r in S.HUBS:
        m = np.zeros(sh, np.uint8)
        cv2.circle(m, c, r, 1, -1)
        sem += 0.15 * _soft(m, 1.5)

    # 4) Karosseriefugen: Black-Top-Hat -> gerichtete Verstaerkung -> auf ~0,45 mm verbreitert
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    bth = cv2.morphologyEx(s, cv2.MORPH_CLOSE, k) - s
    bth = oriented_max(bth.astype(np.float32))
    dark = np.clip((bth - 0.040) / 0.060, 0, 1)
    dark = ndi.grey_dilation(dark, footprint=cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) > 0)
    dark = cv2.GaussianBlur(dark, (0, 0), 1.2)

    inner = np.clip(d_c / 0.5, 0, 1)
    F = carf * (pillow + inner * (sfs + sem))
    line_grooves = carf * inner * LINE_DEPTH * dark

    # 5) Nahtrand-Rillen
    d_outside = ndi.distance_transform_edt(1 - car) * mmpp
    grooves = line_grooves + EDGE_GROOVE * np.exp(-0.5 * (d_outside / 0.3) ** 2) * (1 - carf)
    d_out_mm = d_out * mmpp
    grooves += STITCH_DEPTH * np.exp(-0.5 * ((d_out_mm - STITCH_PX * mmpp) / 0.25) ** 2) * (outer > 0)
    signed = d_out_mm - ndi.distance_transform_edt(1 - outer) * mmpp   # >0 innen, <0 aussen
    grooves += CUTLINE_DEPTH * np.exp(-0.5 * (signed / 0.14) ** 2)
    F_form = F.astype(np.float32)
    grooves = grooves.astype(np.float32)

    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    info = dict(mmpp=mmpp, bbox_px=bbox, car_mask=car, stitch_px=STITCH_PX,
                patch_w_mm=(bbox[2] - bbox[0]) * mmpp, patch_h_mm=(bbox[3] - bbox[1]) * mmpp)
    return F_form, grooves, info


def hillshade(Z, res, az_xy=(-0.5, -0.85), alt_deg=40):
    """Schattierte Ansicht einer Hoehenkarte (Zeilen = von oben nach unten)."""
    gy, gx = np.gradient(Z, res)
    alt = np.radians(alt_deg)
    lx, ly, lz = np.cos(alt) * az_xy[0], np.cos(alt) * az_xy[1], np.sin(alt)
    n = np.dstack([-gx, -gy, np.ones_like(Z)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    s = np.clip(n[..., 0] * lx + n[..., 1] * ly + n[..., 2] * lz, 0, 1)
    return (s ** 1.2 * 235 + 10).astype(np.uint8)
