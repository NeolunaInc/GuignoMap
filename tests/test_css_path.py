from pathlib import Path

def test_css_exists_and_readable():
    css_path = Path("guignomap/assets/styles.css")
    content = css_path.read_text(encoding="utf-8")
    assert isinstance(content, str)
    assert len(content) > 0
