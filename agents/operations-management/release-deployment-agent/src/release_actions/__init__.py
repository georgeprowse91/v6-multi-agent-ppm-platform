"""Release & Deployment Agent - Action handlers package.

Each sub-module contains a single top-level async function that implements
one (or a small group of closely related) agent actions.  The main
``ReleaseDeploymentAgent`` class delegates to these functions from its
``process()`` router.
"""

from release_actions.assess_readiness import assess_readiness
from release_actions.create_deployment_plan import create_deployment_plan
from release_actions.deployment_metrics import track_deployment_metrics
from release_actions.execute_deployment import execute_deployment
from release_actions.manage_environment import check_configuration_drift, manage_environment
from release_actions.plan_release import plan_release
from release_actions.query_status import (
    get_deployment_history,
    get_deployment_status,
    get_release_calendar,
    get_release_status,
)
from release_actions.release_notes import generate_release_notes
from release_actions.rollback_deployment import rollback_deployment
from release_actions.schedule_window import schedule_deployment_window
from release_actions.verify_post_deployment import verify_post_deployment

__all__ = [
    "assess_readiness",
    "check_configuration_drift",
    "create_deployment_plan",
    "execute_deployment",
    "generate_release_notes",
    "get_deployment_history",
    "get_deployment_status",
    "get_release_calendar",
    "get_release_status",
    "manage_environment",
    "plan_release",
    "rollback_deployment",
    "schedule_deployment_window",
    "track_deployment_metrics",
    "verify_post_deployment",
]
