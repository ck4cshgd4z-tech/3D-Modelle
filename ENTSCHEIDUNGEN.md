# Entscheidungen

## leder-praegung-auto (Stand 1.0.0, 2026-11-14)

1. **Werkzeugsatz aus Matrize und Patrize statt Einzelstempel.** Auf dem Foto ist das Auto
   *erhaben*. Das gelingt nur, wenn die Narbenseite in ein Negativ (Matrize) gedrückt und von
   hinten mit einem Positiv (Patrize) gestützt wird. Ein einzelner Stempel würde das Motiv
   vertieft und spiegelverkehrt einprägen.
2. **Die Matrize trägt das volle Detail, die Patrize ist um die Lederstärke versetzt.** Feine
   Details formt nur das Werkzeug, das die Sichtseite berührt. Die Patrize entsteht durch
   Kugel-Erosion (echter Normalenabstand statt reiner Verschiebung nach unten) plus 50 %
   Feindetail. Der Mindestspalt von 0,85 × Lederstärke ist garantiert und wird geprüft.
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
7. **Naht-, Trenn- und Schnittkanten-Rillen nur in der Matrize.** Sie prägen sich durch
   Verdichtung (wie beim Punzieren, maximal etwa 34 % bei 1,6-mm-Leder). Die Patrize bleibt im
   Randbereich eben.
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
