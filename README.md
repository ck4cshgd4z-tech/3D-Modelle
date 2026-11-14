# 3D-Modelle

Sammlung reproduzierbarer 3D-Druckmodelle. Jedes Modell enthält Vorlage, Generator, Druckdateien
und Anleitung.

| Modell | Beschreibung | Drucker |
|---|---|---|
| [leder-praegung-auto](leder-praegung-auto/ANLEITUNG.md) | Leder-Prägewerkzeug (Matrize und Patrize) für einen Muscle-Car-Schlüsselanhänger, abgeleitet aus einem Foto | Bambu Lab P2S |

![Vorschau](leder-praegung-auto/ausgabe/vorschau_3d.png)

## Schnellstart
```bash
pip install -r requirements.txt
python3 leder-praegung-auto/generator/generate.py
python3 leder-praegung-auto/generator/check.py
```

Projektregeln für KI-Assistenten stehen in [CLAUDE.md](CLAUDE.md) bzw. [AGENTS.md](AGENTS.md),
den aktuellen Stand findest du in [PROJEKTSTATUS.md](PROJEKTSTATUS.md), die Begründungen in
[ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md).
