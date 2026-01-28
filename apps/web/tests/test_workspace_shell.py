from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def test_index_links_to_workspace():
    index_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "href=\"/workspace\"" in index_html


def test_workspace_shell_layout_strings():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    for label in [
        "Methodology",
        "Monitoring",
        "Document",
        "Tree",
        "Timeline",
        "Spreadsheet",
        "Dashboard",
        "Activity Guidance",
        "Select an activity to view guidance.",
    ]:
        assert label in app_js
    assert "window.location.pathname === \"/workspace\"" in app_js


def test_workspace_css_present():
    workspace_css = (STATIC_DIR / "workspace.css").read_text(encoding="utf-8")
    assert ".workspace-shell" in workspace_css
    assert ".workspace-nav" in workspace_css
    assert ".workspace-assistant" in workspace_css
