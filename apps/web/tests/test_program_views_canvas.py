from pathlib import Path


def test_program_views_canvas_assets_present():
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(
        encoding="utf-8"
    )
    assert "/api/dependency-map/" in app_js
    assert "/api/program-roadmap/" in app_js
    assert "dependency-map" in app_js
    assert "program-roadmap" in app_js
    assert "forceSimulation" in app_js
    assert "roadmap-canvas" in app_js
