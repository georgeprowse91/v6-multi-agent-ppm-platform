from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def test_dashboard_canvas_calls_portfolio_and_lifecycle_endpoints():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "/api/portfolio-health" in app_js
    assert "/api/lifecycle-metrics" in app_js
    assert "stage-gate" in app_js
