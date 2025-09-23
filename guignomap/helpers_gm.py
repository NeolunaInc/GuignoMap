"""
GM helpers extracted from app.py (modularization)
"""

import os, sqlite3
import pandas as pd
import streamlit as st
import guignomap.db as db

DB_PATH = os.path.join(os.path.dirname(__file__), "guigno_map.db")

def get_conn() -> sqlite3.Connection:
    try:
        return sqlite3.connect(DB_PATH)
    except Exception:
        return sqlite3.connect(":memory:")

def _safe_stats(conn) -> dict:
    try:
        s = db.extended_stats(conn)
        if isinstance(s, dict):
            return {"done": int(s.get("done", 0)), "total": int(s.get("total", 0))}
    except Exception:
        pass
    return {"done": 0, "total": 0}

def _ensure_df(x) -> pd.DataFrame:
    if isinstance(x, pd.DataFrame):
        return x
    if x is None:
        return pd.DataFrame()
    try:
        return pd.DataFrame(x)
    except Exception:
        return pd.DataFrame()

def _load_points_df(conn) -> pd.DataFrame:
    # 1) DB si dispo
    try:
        fn = getattr(db, "list_points", None)
        if callable(fn):
            df = fn(conn)
            return df if isinstance(df, pd.DataFrame) else _ensure_df(df)
    except Exception:
        pass
    # 2) Excel fallback
    try:
        xlsx = os.path.join("import", "nocivique_cp_complement.xlsx")
        if os.path.exists(xlsx):
            df = pd.read_excel(xlsx)
            return df if isinstance(df, pd.DataFrame) else _ensure_df(df)
    except Exception:
        pass
    # 3) vide
    return pd.DataFrame()