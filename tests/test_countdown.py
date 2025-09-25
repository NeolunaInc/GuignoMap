from datetime import datetime
from zoneinfo import ZoneInfo
import importlib

def _patch_now(monkeypatch, dt):
    app = importlib.import_module("guignomap.app")
    # Remplace la fonction _now(tz) pour renvoyer notre datetime figé
    monkeypatch.setattr(app, "_now", lambda tz: dt, raising=True)
    return app

def test_compte_a_rebours_1_nov(monkeypatch):
    tz = ZoneInfo("America/Toronto")
    dt = datetime(2025, 11, 1, 10, 0, 0, tzinfo=tz)  # avant la cible
    app = _patch_now(monkeypatch, dt)
    res = app.get_compte_a_rebours()
    assert res == "Dans 35 jours et 22 heures"

def test_compte_a_rebours_2_dec(monkeypatch):
    tz = ZoneInfo("America/Toronto")
    dt = datetime(2025, 12, 2, 12, 0, 0, tzinfo=tz)
    app = _patch_now(monkeypatch, dt)
    res = app.get_compte_a_rebours()
    assert res == "Dans 4 jours et 20 heures"

def test_compte_a_rebours_1_dec_07h(monkeypatch):
    tz = ZoneInfo("America/Toronto")
    dt = datetime(2025, 12, 1, 7, 0, 0, tzinfo=tz)
    app = _patch_now(monkeypatch, dt)
    res = app.get_compte_a_rebours()
    assert res == "Dans 6 jours et 1 heures"

def test_compte_a_rebours_1_dec_10h(monkeypatch):
    tz = ZoneInfo("America/Toronto")
    dt = datetime(2025, 12, 1, 10, 0, 0, tzinfo=tz)
    app = _patch_now(monkeypatch, dt)
    res = app.get_compte_a_rebours()
    assert res == "Dans 5 jours et 22 heures"

def test_compte_a_rebours_jour_J(monkeypatch):
    # Premier dimanche de décembre 2025 = 7 décembre
    tz = ZoneInfo("America/Toronto")
    dt = datetime(2025, 12, 7, 10, 0, 0, tzinfo=tz)  # Jour J
    app = _patch_now(monkeypatch, dt)
    res = app.get_compte_a_rebours()
    assert res == "C'est aujourd'hui !"
