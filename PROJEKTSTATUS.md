# Projektstatus

## leder-praegung-auto – Prägewerkzeug „Muscle-Car-Patch“ · Version 1.0.0 (2026-11-14)

### Umgesetzt
- Relief aus dem Foto abgeleitet: Kontur segmentiert (ohne Schatten, Schlaufe und Lasche),
  Ledernarbung entfernt, Plastik per Shape-from-Shading, Tiefenebenen (Scheiben, Räder mit
  Speichen und Naben, Frontmaske, Grill, Lufteinlass mit Lamellen, Scheinwerferringe, Spiegel),
  Karosseriefugen auf druckbare Breite gebracht, Nahtrille, Trennrille und Schnittkante.
- Werkzeugsatz für die Bambu Lab P2S: 1 Matrize (Negativ, spiegelverkehrt) und 3 Patrizen
  (Positiv) für Leder 1,2 / 1,6 / 2,0 mm. Platten 126 × 78 mm, Patch 90 × 41 mm, Zuschnitt
  100 × 52 mm. Dazu 4 Passstifte mit Verdrehschutz, Sacklöcher, Anschlagringe und Beschriftung.
- Export als 3MF (im Repo) und STL (lokal/ZIP), Vorschauen (Vergleich Foto/Relief, 3D-Schrägansicht,
  Draufsichten, Querschnitt in Pressstellung), SVG-Schnittschablone 1:1, `pruefbericht.json`.
- Automatische Prüfungen: `generate.py` (20 Prüfungen) und `check.py` (Dateien von der Platte neu
  geladen: Geschlossenheit, Maße, STL = 3MF, Stift trifft Loch, Passung der gespiegelten Matrize).
  Stand: alle bestanden.

### Offen / nur in der Zielumgebung prüfbar
- Probedruck auf der P2S und Prägetest mit echtem Leder (Passung der Stifte, Prägetiefe,
  Detailschärfe) – kann nur der Nutzer durchführen.
- Je nach Testergebnis feinjustieren: `stop_factor`, `min_gap_factor`, `hole_clear`,
  Reliefhöhe (`PILLOW_STEP`, `SFS_GAIN`).

### Vorschläge (nicht umgesetzt)
- Variante für die 0,2-mm-Düse mit schmaleren Fugen und mehr Lamellen.
- Werkzeug für Rückenteil und Schlüssellasche wie auf dem Foto.
- Weitere Größen, z. B. 110 mm (Generator: `--laenge 110`).

### Bekannte Einschränkungen
- Die Plastik ist aus einem einzigen Foto rekonstruiert. Das kommt dem Original sehr nahe, ist
  aber kein Messwert: Die Fugen um die Scheibenwischer sind leicht unruhig, das ferne Hinterrad ist
  weniger scharf als das Vorderrad.
- Die Konturen in `generator/shapes.py` gelten nur für dieses Foto.

## Übergabe
- **Stand:** v1.0.0 fertig, alle automatischen Prüfungen bestanden. In `main` übernommen
  (Arbeitszweig `claude/beautiful-mendel-b054dg`). Der Nutzer hat dauerhaft freigegeben, fertige
  und getestete Arbeit direkt nach `main` zu übernehmen.
- **Für den Nutzer:** Matrize und die passende Patrize drucken (Einstellungen in
  `leder-praegung-auto/ANLEITUNG.md`), an einem Reststück testen und das Ergebnis zurückmelden.
- **Für den nächsten Assistenten:** Zuerst `CLAUDE.md` lesen. Druckdateien nur über
  `python3 leder-praegung-auto/generator/generate.py` neu erzeugen und danach
  `python3 leder-praegung-auto/generator/check.py` ausführen. Beide müssen mit Exit-Code 0 enden.
  STL wird nicht versioniert. Ein voller Lauf dauert etwa 2 Minuten, `--schnell` etwa 30 Sekunden.
- **Umgebung:** Python 3.13, Pakete in `requirements.txt` (OpenCV mit contrib-Modulen nötig).
