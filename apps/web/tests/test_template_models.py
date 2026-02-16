from template_models import (
    render_template_value,
    render_template_value_with_unresolved,
    substitute_placeholders,
)


def test_substitute_placeholders_supports_nested_paths():
    context = {
        "project": {"name": "Atlas", "owner": {"name": "Ava"}},
        "tenant_id": "tenant-a",
    }

    rendered = substitute_placeholders(
        "{{project.name}} / {{project.owner.name}} / {{tenant_id}}",
        context,
    )

    assert rendered == "Atlas / Ava / tenant-a"


def test_render_template_value_with_unresolved_collects_missing_keys():
    context = {"project": {"name": "Atlas"}}

    rendered, unresolved = render_template_value_with_unresolved(
        {
            "title": "{{project.name}}",
            "owner": "{{project.owner.name}}",
            "sections": ["{{project.name}}", "{{missing_key}}"],
        },
        context,
    )

    assert rendered["title"] == "Atlas"
    assert rendered["owner"] == "{{project.owner.name}}"
    assert rendered["sections"] == ["Atlas", "{{missing_key}}"]
    assert unresolved == {"project.owner.name", "missing_key"}


def test_render_template_value_keeps_compatibility():
    rendered = render_template_value(
        {"title": "{{name}}", "count": 1},
        {"name": "Roadmap"},
    )

    assert rendered == {"title": "Roadmap", "count": 1}
