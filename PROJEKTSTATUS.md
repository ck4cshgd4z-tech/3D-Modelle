# Projektstatus

## gemeinsam/ – Werkzeugbau-Bibliothek (seit 2026-11-15)
- `dies.py` (Matrize/Patrize als Höhenfelder, Stifte, Sacklöcher, Anschläge, Beschriftung),
  `mesh.py` (wasserdichtes Netz, Reduktion, STL/3MF), `werkzeugsatz.py` (Gesamtablauf,
  Vorschauen, Prüfungen, Prüfbericht) und `pruefe_ausgabe.py` (unabhängige Dateiprüfung).
- Beide Projekte nutzen sie. Nach dem Umbau ist das Auto-Werkzeug geometrisch identisch zu v1.1
  (Raycast-Vergleich 0,0000 mm, gleiche Volumina, 23/23 und 35/35 Prüfungen).

## leder-praegung-auto – Prägewerkzeug „Muscle-Car-Patch“ · Version 1.1.0 (2026-11-14)

### Umgesetzt
- Relief aus dem Foto abgeleitet: Kontur segmentiert (ohne Schatten, Schlaufe und Lasche),
  Ledernarbung entfernt, Plastik per Shape-from-Shading, Tiefenebenen (Scheiben, Räder mit
  Speichen und Naben, Frontmaske, Grill, Lufteinlass mit Lamellen, Scheinwerferringe, Spiegel),
  Karosseriefugen auf druckbare Breite gebracht, Nahtrille, Trennrille und Schnittkante.
- Werkzeugsatz für die Bambu Lab P2S: 1 Matrize (Negativ, spiegelverkehrt) und 3 Patrizen
  (Positiv) für Leder 1,2 / 1,6 / 2,0 mm. Platten 126 × 78 mm, Patch 90 × 41 mm, Zuschnitt
  100 × 52 mm. Dazu 4 Passstifte mit Verdrehschutz, Sacklöcher, Anschlagringe und Beschriftung.
- v1.1: Patrize beruhigt, die Unruhe aus der reinen Erosion („Golfball“) ist weg.
- Prüfungen: `generate.py` 23/23 und `check.py` 35/35 bestanden.

### Offen / nur in der Zielumgebung prüfbar
- Probedruck auf der P2S und Prägetest mit echtem Leder – kann nur der Nutzer durchführen.

### Bekannte Einschränkungen
- Die Plastik ist aus einem einzigen Foto rekonstruiert und kein Messwert. Die Fugen um die
  Scheibenwischer sind leicht unruhig, das ferne Hinterrad ist weniger scharf als das Vorderrad.

## logo-anhaenger-popko – Popko-Design Logo · Version 1.0.0 (2026-11-15)

### Umgesetzt
- Vorlage: Pfad-SVG des Nutzers (Schrift „abnes“ in Pfade umgewandelt).
- **Gesamtlogo:** Anhänger 60 × 30 mm, Logo 48,5 × 8,8 mm (Ring, POPKO, DESIGN). DESIGN von
  0,34 auf 0,40 mm verstärkt, PKD im kleinen Ring weggelassen (wäre 0,7 mm hoch).
- **PKD-Emblem:** runder Anhänger Ø 45 mm (Vorgabe des Nutzers: höchstens 50 mm), Ring Ø 33 mm,
  P/K/D 5,4 mm hoch.
- Machart: Nahtrand, gepolstertes Feld, Logo erhaben durch Kantenabschrägung (0,38 mm).
  Patrize = glattes Kissen. Je Form 1 Matrize und 3 Patrizen (1,2 / 1,6 / 2,0 mm).
- Prüfungen: `generate.py` 28/28 (Logo) und 26/26 (Emblem), dazu Lesrichtung und
  Mindeststrich; `check.py` 35/35 je Form.

### Offen / nur in der Zielumgebung prüfbar
- Probedruck und Prägetest, besonders wie gut „DESIGN“ mit 0,4- und mit 0,2-mm-Düse wird.

### Vorschläge (nicht umgesetzt)
- Rückenteil und Lasche als Schablone; Goldakzente per Heißfolie.
- Gesamtlogo auf zwei Zeilen umgestellt, wenn ein höherer Anhänger gewünscht ist.

## Übergabe
- **Stand:** Neues Projekt `logo-anhaenger-popko` v1.0.0 mit zwei Formen. Werkzeugbau in
  `gemeinsam/` zusammengeführt. Alle automatischen Prüfungen bestanden, in `main` übernommen
  (Arbeitszweig `claude/beautiful-mendel-b054dg`). Der Nutzer hat dauerhaft freigegeben, fertige
  und getestete Arbeit direkt nach `main` zu übernehmen.
- **Für den Nutzer:** Matrize und passende Patrize der gewünschten Form drucken
  (`logo-anhaenger-popko/ANLEITUNG.md`), am Reststück testen, Ergebnis zurückmelden.
- **Für den nächsten Assistenten:** Zuerst `CLAUDE.md` lesen. Druckdateien nur über die
  Generatoren erzeugen, danach das jeweilige `generator/check.py` ausführen. Beides muss mit
  Exit-Code 0 enden. Änderungen an `gemeinsam/` betreffen **beide** Projekte, also beide neu
  erzeugen und prüfen. Eine reine Neuerzeugung ändert die 3MF-Bytes (zufällige IDs), ohne dass
  sich die Geometrie ändert. Solche Dateien nicht unnötig committen.
  Laufzeit: Auto etwa 2 Minuten, Logo beide Formen etwa 5 Minuten, `--schnell` deutlich kürzer.
- **Umgebung:** Python 3.13, Pakete in `requirements.txt` (OpenCV mit contrib-Modulen,
  svgelements).
