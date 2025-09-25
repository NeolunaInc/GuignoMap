import pytest

def calc_pct(done, total):
    return (done / total * 100) if total else 0

def test_pct_zero_zero():
    assert calc_pct(0, 0) == 0

def test_pct_half():
    assert calc_pct(5, 10) == 50

def test_pct_full():
    assert calc_pct(10, 10) == 100
