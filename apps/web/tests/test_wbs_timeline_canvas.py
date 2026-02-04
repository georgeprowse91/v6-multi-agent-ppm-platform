from pathlib import Path


def test_wbs_and_timeline_canvas_assets_present():
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(
        encoding="utf-8"
    )
    assert "/api/wbs/" in app_js
    assert "/api/schedule/" in app_js
    assert "dragstart" in app_js
    assert "dragover" in app_js
    assert "drop" in app_js
