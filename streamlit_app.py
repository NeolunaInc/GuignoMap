# coding: utf-8
import os, sys
os.environ.setdefault("PYTHONUTF8", "1")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pathlib, importlib, traceback
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    app = importlib.import_module("guignomap.app")
    for fn_name in ("main", "run", "render"):
        fn = getattr(app, fn_name, None)
        if callable(fn):
            fn()
            break
    else:
        st.caption("GuignoMap chargé (mode import).")
except Exception:
    st.error("Erreur de démarrage :")
    st.code(traceback.format_exc())
    import platform, streamlit, sqlalchemy
    st.write({
        "python": platform.python_version(),
        "streamlit": streamlit.__version__,
        "sqlalchemy": sqlalchemy.__version__,
        "secrets_keys": list(getattr(st, "secrets", {}).keys()),
    })