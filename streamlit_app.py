# coding: utf-8
"""Entrypoint Streamlit Cloud: garantit que la racine du repo est dans sys.path,
puis importe l'app principale (guignomap/app.py)."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# L'import exécute le code Streamlit de l'app
import guignomap.app  # noqa: F401