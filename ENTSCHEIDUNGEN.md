# Entscheidungen

## leder-praegung-auto (Stand 1.1.0, 2026-11-14)

1. **Werkzeugsatz aus Matrize und Patrize statt Einzelstempel.** Auf dem Foto ist das Auto
   *erhaben*. Das gelingt nur, wenn die Narbenseite in ein Negativ (Matrize) gedrückt und von
   hinten mit einem Positiv (Patrize) gestützt wird. Ein einzelner Stempel würde das Motiv
   vertieft und spiegelverkehrt einprägen.
2. **Die Matrize trägt das volle Detail, die Patrize ist um die Lederstärke versetzt.** Feine
   Details formt nur das Werkzeug, das die Sichtseite berührt. Die Patrize entsteht durch
   Kugel-Erosion (echter Normalenabstand statt reiner Verschiebung nach unten), seit v1.1
   beruhigt (siehe Nr. 12). Der Mindestspalt von 0,85 × Lederstärke ist garantiert und wird
   geprüft.
3. **Eine Matrize und drei Patrizen (Leder 1,2 / 1,6 / 2,0 mm).** Nur die Patrize hängt von der
   Lederstärke ab. Anschlagringe in Höhe 0,85 × Lederstärke verhindern Überpressen und sorgen
   für gleichmäßige Ergebnisse.
4. **Relief über Shape-from-Shading statt KI-Tiefenschätzung.** Das Foto zeigt bereits ein
   Relief, das von oben beleuchtet ist. Integriert man die Helligkeit als Flächenneigung (Poisson,
   DCT), entsteht dessen Plastik deterministisch und ohne Modell-Download. Die Hosts für
   KI-Modelle sind in dieser Umgebung ohnehin gesperrt. Ergänzt wird das durch nachgezeichnete
   Tiefenebenen (Scheiben, Räder, Grill, Lufteinlass, Spiegel) und erkannte Karosseriefugen.
5. **Ledernarbung entfernen.** Die Narbung gehört zum Leder, nicht zum Werkzeug. Sie wird per
   bilateralem Filter und Fast-Global-Smoother entfernt, Linien bleiben dabei erhalten.
6. **Details auf Druckbarkeit ausgelegt (0,4-mm-Düse).** Fugen werden auf etwa 0,45 mm
   verbreitert. Die sehr feinen Lamellen aus dem Foto (0,4 mm Abstand) sind auf vier bzw. eine
   Lamelle mit etwa 0,7 mm Abstand vereinfacht.
7. **Alle schmalen Rillen nur in der Matrize** (seit v1.1 auch die Karosseriefugen). Sie prägen
   sich durch Verdichtung wie beim Punzieren. Geprüft wird höchstens 50 % (aktuell 46 / 37 / 32 %
   bei 1,2 / 1,6 / 2,0 mm). Die Patrize bleibt im Randbereich eben.
8. **Ausrichtung über 4 Stifte und Sacklöcher, ein Stift ist dicker (Ø 8 statt Ø 6 mm).** Damit
   kann die Matrize nicht verdreht aufgesetzt werden. Sacklöcher statt Durchgangslöcher, damit
   kein Stift aus der Matrize herausragt.
9. **Netz als Höhenfeld mit Quadrik-Reduktion.** Ein Höhenfeld ergibt garantiert ein geschlossenes
   Netz. Die Reduktion auf 450 000 Dreiecke weicht höchstens 0,01 mm ab. Artefakt-Dreiecke werden
   entfernt, bei Topologiefehlern wird mit anderem Ziel wiederholt.
10. **Patchlänge 90 mm.** Geschätzt über das Anhänger-Schild auf dem Foto (etwa 25 mm breit),
    über `--laenge` änderbar.
11. **STL nicht im Git.** Je Datei etwa 22 MB. Versioniert wird das kompakte 3MF (etwa 6 MB), die
    STL-Dateien kommen über den Generator oder das Übergabe-ZIP.
12. **Patrize beruhigt (v1.1).** Eine reine Kugel-Erosion der Sichtseite macht aus jeder feinen
    Mulde eine Kugeldelle mit scharfen Graten dazwischen. Das ergibt eine unruhige
    „Golfball“-Oberfläche, die bei dünnem Leder durchdrücken kann. Neu: Fugen gehen gar nicht erst
    in die Patrize ein. Flache Mulden werden höchstens 0,10 mm aufgefüllt, eine stärkere
    Schließung würde echte Vertiefungen wie das Hinterrad füllen und dort bis 58 % quetschen.
    Nach der Erosion werden die Grate geglättet (σ 0,25 mm), das senkt nur die Grate, der Spalt
    wird also nicht kleiner. Das Grat-Maß sinkt dadurch von 16 auf 6 µm. Die Patrize wirkt bewusst
    weicher als die Matrize, weil die Details nur von der Sichtseite her entstehen.

## gemeinsam/ (2026-11-15)

1. **Werkzeugbau als gemeinsame Bibliothek statt Kopie je Projekt.** Matrize, Patrize, Netz,
   Vorschauen und Prüfungen sind für jedes Motiv gleich, ein Projekt liefert nur seine Sichtseite.
   Den Umbau habe ich per Geometrie-Vergleich abgesichert: Das Auto-Werkzeug ist identisch.

## logo-anhaenger-popko (Stand 1.0.0, 2026-11-15)

1. **Zwei Formen: Gesamtlogo 60 × 30 mm und PKD-Emblem Ø 45 mm.** Das Logo ist etwa 5,6-mal so
   breit wie hoch, also wird es auf 60 × 30 mm am größten. „PKD“ wäre im Gesamtlogo nur 0,7 mm
   hoch und damit weder druck- noch prägbar. Es hat deshalb eine eigene, große Form (Wunsch des
   Nutzers, höchstens 50 mm).
2. **Logo erhaben durch Kantenabschrägung, nicht durch Formen von hinten.** Striche von 0,4–0,9 mm
   sind viel schmaler als das Leder dick ist und lassen sich von der Fleischseite aus nicht
   formen. Die Matrize drückt deshalb den Rand um die Buchstaben ab (0,38 mm, Auslauf 1,0 mm),
   wie beim Punzieren. Die Patrize ist ein glattes Kissen. Kleine Innenräume (unter 40 mm²) werden
   ganz eingedrückt, sonst stünde in ihrer Mitte ein Punkt.
3. **Mindeststrich 0,40 mm.** „DESIGN“ ist von 0,34 auf 0,40 mm verstärkt. Mehr geht nicht, ohne
   die Lücken im E unter etwa 0,4 mm zu drücken. Die Ringstärke folgt den feinen Buchstaben.
4. **Abschrägung 0,38 statt 0,40 mm.** Damit liegt die Verdichtung auch bei 1,2-mm-Leder unter
   50 % (49 %).
5. **Vorlage als Pfad-SVG.** Die Schrift „abnes“ ist nicht verfügbar. Eine Ersatzschrift hätte das
   Logo verfälscht, und die Canva-Version ist älter (DESGN, PKD waagerecht).
