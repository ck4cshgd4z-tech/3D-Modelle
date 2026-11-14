"""Aus dem Foto nachgezeichnete Bildbereiche (Pixelkoordinaten des Quellfotos 1560 x 870).

Diese Konturen geben dem Relief echte Tiefenebenen (Scheiben, Raeder, Grill, Lufteinlass,
Scheinwerfer, Spiegel). Sie gelten nur fuer quelle/foto.jpg. Bei einem anderen Foto muessen
sie neu nachgezeichnet werden (Overlay-Kontrolle: generate.py --kontrollbild).
"""
import cv2
import numpy as np

# Schnittlinien, mit denen Schlaufe (oben) und Anhaenger-Lasche (unten) vom Patch getrennt werden
STRAP_CUT = ((685, 24), (935, 14))
TAB_CUT = ((692, 716), (893, 687))

WINDSHIELD = [(470, 192), (530, 140), (600, 97), (700, 82), (800, 85), (900, 95), (975, 104),
              (960, 160), (945, 235), (870, 222), (800, 212), (720, 203), (600, 198)]
WIN_FRONT = [(988, 110), (1040, 99), (1100, 99), (1147, 110), (1190, 211), (1130, 222),
             (1060, 232), (980, 238)]
WIN_REAR = [(1152, 109), (1197, 108), (1232, 136), (1265, 175), (1202, 215), (1193, 211)]
FASCIA = [(76, 310), (330, 322), (585, 338), (592, 380), (582, 425), (330, 408), (80, 382)]
GRILLE = [(183, 333), (300, 343), (455, 352), (458, 385), (300, 375), (185, 362)]
INTAKE = [(140, 455), (300, 470), (545, 505), (552, 555), (480, 566), (150, 522)]

WHEEL_F = dict(c=(791, 503), ax=(94, 112), ang=0)
RIM_F = dict(c=(791, 500), ax=(80, 98), ang=0)
WHEEL_R = dict(c=(1378, 425), ax=(54, 116), ang=0)
RIM_R = dict(c=(1380, 422), ax=(42, 92), ang=0)
HUBS = [((787, 497), 9), ((1384, 418), 6)]
HEADLIGHTS = [((112, 340), 17), ((155, 345), 17), ((500, 375), 21), ((553, 385), 21)]
MIRROR = dict(c=(1087, 208), ax=(40, 18), ang=-5)
MIRROR_STALK = ((1028, 252), (1058, 226))

# Lamellen: vereinfacht auf druck- und praegbaren Abstand (~0,7 mm bei 90 mm Patchlaenge)
INTAKE_SLATS_T = (0.2, 0.4, 0.6, 0.8)
INTAKE_DIVIDER = ((500, 500), (505, 560))
GRILLE_DIVIDER = ((298, 340), (298, 377))


def poly_mask(shape, pts):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m


def ell_mask(shape, e):
    m = np.zeros(shape, np.uint8)
    cv2.ellipse(m, e["c"], e["ax"], e["ang"], 0, 360, 1, -1)
    return m


def line_mask(shape, p, q, width):
    m = np.zeros(shape, np.uint8)
    cv2.line(m, tuple(int(round(v)) for v in p), tuple(int(round(v)) for v in q), 1, width)
    return m


def draw_overlay(img_bgr):
    """Kontrollbild: alle nachgezeichneten Bereiche ueber dem Foto."""
    ov = img_bgr.copy()
    for pts, c in [(WINDSHIELD, (255, 0, 0)), (WIN_FRONT, (0, 255, 0)), (WIN_REAR, (0, 0, 255)),
                   (FASCIA, (0, 165, 255)), (GRILLE, (0, 255, 255)), (INTAKE, (255, 0, 255))]:
        cv2.polylines(ov, [np.array(pts, np.int32)], True, c, 1)
    for e in (WHEEL_F, RIM_F, WHEEL_R, RIM_R, MIRROR):
        cv2.ellipse(ov, e["c"], e["ax"], e["ang"], 0, 360, (255, 255, 0), 1)
    for c, r in HEADLIGHTS + HUBS:
        cv2.circle(ov, c, r, (0, 0, 255), 1)
    cv2.line(ov, *MIRROR_STALK, (255, 255, 0), 1)
    cv2.line(ov, *STRAP_CUT, (0, 0, 255), 1)
    cv2.line(ov, *TAB_CUT, (0, 0, 255), 1)
    return ov
