from pathlib import Path


def test_wbs_and_timeline_canvas_assets_present():
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "/api/wbs/" in app_js
    assert "/api/schedule/" in app_js
    assert "dragstart" in app_js
    assert "dragover" in app_js
    assert "drop" in app_js
    assert 'data-gantt-view="Week"' in app_js
    assert "change_view_mode" in app_js
    assert 'dependencies: (task.dependencies || []).join(",")' in app_js


def test_guidance_panel_includes_wbs_and_timeline_next_steps():
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "Drag WBS rows to reprioritize and adjust the hierarchy." in app_js
    assert "Drop items on the root area to promote them to the top level." in app_js
    assert "Review dependency links and validate critical path overlaps." in app_js
    assert "Use zoom controls to switch between week and month views." in app_js
