# Regeln für KI-Assistenten (identisch mit AGENTS.md)

Dieses Repository wird abwechselnd von mehreren KI-Assistenten bearbeitet (Claude, Codex u. a.).
`CLAUDE.md` und `AGENTS.md` haben **immer denselben Inhalt**. Wer eine der beiden Dateien ändert,
ändert die andere mit.

## Zusammenarbeit
1. **Vor jeder Aufgabe** den neuesten Stand holen (`git fetch` und `git pull` auf `main` bzw. dem
   Arbeitszweig) und `PROJEKTSTATUS.md` lesen, besonders den Abschnitt „Übergabe“.
2. Auf einem eigenen Arbeitszweig arbeiten. Fertige und **getestete** Arbeit selbst nach `main`
   übernehmen (Merge, dann Push).
3. **Nach jeder Aufgabe** die „Übergabe“ in `PROJEKTSTATUS.md` neu schreiben: Stand, was erledigt
   ist, was offen ist, worauf der Nächste achten muss.
4. Wichtige technische oder fachliche Entscheidungen kurz in `ENTSCHEIDUNGEN.md` festhalten.
5. Klar trennen zwischen *umgesetzt*, *geplant* und *nur vorgeschlagen*. Nie behaupten, etwas sei
   getestet, wenn kein Test lief.
6. Dokumentation und Nutzertexte auf Deutsch, kompakt und widerspruchsfrei halten.

## Projektstruktur
- Jedes Modell bekommt einen eigenen Ordner, z. B. `leder-praegung-auto/`, mit:
  `quelle/` (Vorlagen), `generator/` (reproduzierbare Skripte), `ausgabe/` (Druckdateien und
  Vorschauen) und `ANLEITUNG.md`.
- Druckdateien werden **nur über den Generator** erzeugt, nie von Hand bearbeitet. Zuerst
  Parameter oder Code ändern, dann neu erzeugen.
- `*.stl` wird nicht versioniert (Größe). Versioniert werden `.3mf`, Vorschauen und Prüfbericht.
  STL-Dateien entstehen lokal über den Generator oder werden als ZIP übergeben.

## Projekt `leder-praegung-auto` (Prägewerkzeug Leder)
- Pipeline: `relief.py` (Foto → Höhenkarte der Leder-Sichtseite F) → `dies.py` (Matrize und
  Patrizen als Höhenfelder in mm) → `mesh.py` (wasserdichtes Netz, Reduktion, STL/3MF) →
  `generate.py` (Ablauf, Vorschauen, Prüfungen) → `check.py` (unabhängige Dateiprüfung).
- Koordinaten: Plattenmitte = Ursprung, x nach rechts, y nach oben. Array-Zeile 0 = oberer Rand
  (+y). Fotozeilen laufen nach unten, deshalb beim Umrechnen y spiegeln (`relief_to_plate`).
- Die **Matrize** trägt die Sichtseite F und das volle Detail. Sie wird zum Druck um die y-Achse
  gewendet und ist dadurch spiegelverkehrt. Die **Patrize** entsteht durch Kugel-Erosion um die
  Lederstärke plus halbes Feindetail und hat einen Mindestspalt von 0,85 × Lederstärke.
  Naht-, Trenn- und Schnittkanten-Rillen gibt es **nur** in der Matrize.
- Nachgezeichnete Bildbereiche (`shapes.py`) gelten nur für `quelle/foto.jpg`. Bei einem neuen
  Foto neu zeichnen und mit `generate.py --kontrollbild` kontrollieren.
- Abnahmekriterium: `generate.py` und `check.py` enden mit Exit-Code 0 (alle Prüfungen OK).
