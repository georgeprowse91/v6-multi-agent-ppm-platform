"""Action handler: generate_release_notes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from release_utils import generate_release_notes_id, query_tracking_systems

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def generate_release_notes(
    agent: ReleaseAgentProtocol, release_id: str
) -> dict[str, Any]:
    """
    Generate release notes using NLG.

    Returns formatted release notes.
    """
    agent.logger.info("Generating release notes for: %s", release_id)

    release = agent.releases.get(release_id)
    if not release:
        raise ValueError(f"Release not found: {release_id}")

    # Gather release information
    changes = await query_tracking_systems(agent, release_id, record_type="change")
    features = await query_tracking_systems(agent, release_id, record_type="feature")
    bug_fixes = await query_tracking_systems(agent, release_id, record_type="bug")
    known_issues = await query_tracking_systems(agent, release_id, record_type="issue")

    # Generate notes using AI
    release_notes_content = await _generate_notes_content(
        agent, release, changes, features, bug_fixes, known_issues
    )

    # Create release notes record
    notes_id = await generate_release_notes_id()
    release_notes = {
        "notes_id": notes_id,
        "release_id": release_id,
        "content": release_notes_content,
        "features": features,
        "bug_fixes": bug_fixes,
        "known_issues": known_issues,
        "related_tickets": changes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    agent.release_notes[notes_id] = release_notes

    # Persist to database
    await agent.db_service.store("release_notes", notes_id, release_notes)

    # Publish to documentation repository (Confluence or SharePoint)
    publish_result = await agent.doc_publishing_service.publish_release_notes(
        release_id=release_id,
        release_name=release.get("name", release_id),
        content=release_notes_content,
        metadata={
            "environment": release.get("target_environment"),
            "tags": ["release-notes", release.get("target_environment", "")],
        },
    )
    release_notes["published_url"] = publish_result.get("url")
    release_notes["published_platform"] = publish_result.get("platform")

    return {
        "notes_id": notes_id,
        "release_id": release_id,
        "content": release_notes_content,
        "features_count": len(features),
        "bug_fixes_count": len(bug_fixes),
        "known_issues_count": len(known_issues),
        "published_url": publish_result.get("url"),
        "published_platform": publish_result.get("platform"),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _generate_notes_content(
    agent: ReleaseAgentProtocol,
    release: dict[str, Any],
    changes: list[dict[str, Any]],
    features: list[dict[str, Any]],
    bug_fixes: list[dict[str, Any]],
    known_issues: list[dict[str, Any]],
) -> str:
    """Generate release notes content using NLG."""
    if agent.openai_client:
        prompt = await _build_release_notes_prompt(
            release, changes, features, bug_fixes, known_issues
        )
        if hasattr(agent.openai_client, "generate"):
            response = await agent.openai_client.generate(prompt)
            return cast(str, response)
        if hasattr(agent.openai_client, "complete"):
            response = await agent.openai_client.complete(prompt)
            return cast(str, response)
    return f"""Release Notes: {release.get('name')}

Date: {release.get('actual_date', release.get('planned_date'))}
Environment: {release.get('target_environment')}

Features:
{chr(10).join(f"- {f.get('description', 'Feature')}" for f in features)}

Bug Fixes:
{chr(10).join(f"- {b.get('description', 'Fix')}" for b in bug_fixes)}

Known Issues:
{chr(10).join(f"- {i.get('description', 'Issue')}" for i in known_issues)}
"""


async def _build_release_notes_prompt(
    release: dict[str, Any],
    changes: list[dict[str, Any]],
    features: list[dict[str, Any]],
    bug_fixes: list[dict[str, Any]],
    known_issues: list[dict[str, Any]],
) -> str:
    """Build prompt for release notes generation."""
    change_list = "\n".join(f"- {item.get('description', 'Change')}" for item in changes)
    feature_list = "\n".join(f"- {item.get('description', 'Feature')}" for item in features)
    bug_list = "\n".join(f"- {item.get('description', 'Fix')}" for item in bug_fixes)
    issue_list = "\n".join(f"- {item.get('description', 'Issue')}" for item in known_issues)
    return (
        "Create release notes with sections for Changes, Features, Bug Fixes, and Known Issues.\n"
        f"Release: {release.get('name')}\n"
        f"Environment: {release.get('target_environment')}\n"
        f"Planned Date: {release.get('planned_date')}\n"
        f"Changes:\n{change_list}\n"
        f"Features:\n{feature_list}\n"
        f"Bug Fixes:\n{bug_list}\n"
        f"Known Issues:\n{issue_list}\n"
    )
