#!/usr/bin/env python3
"""Ausgabedateien dieses Projekts unabhaengig pruefen (siehe gemeinsam/pruefe_ausgabe.py).
Aufruf: python3 generator/check.py [ausgabe-ordner]"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "gemeinsam"))
import pruefe_ausgabe  # noqa: E402

if __name__ == "__main__":
    sys.exit(pruefe_ausgabe.main(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "ausgabe"))
