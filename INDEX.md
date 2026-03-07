# Repository Index

Complete file and folder structure of the repository.

```
multi-agent-ppm-platform-v4/
├── .claude
│   ├── hooks
│   │   └── session-start.sh
│   └── settings.json
├── .devcontainer
│   ├── Dockerfile
│   ├── dev.env
│   └── devcontainer.json
├── .dockerignore
├── .gitattributes
├── .github
│   ├── CODEOWNERS
│   ├── README.md
│   ├── dependabot.yml
│   ├── issue_template
│   │   ├── bug_report.md
│   │   ├── config.yml
│   │   ├── documentation.md
│   │   ├── feature_request.md
│   │   └── security_issue.md
│   ├── pull_request_template.md
│   ├── renovate.json
│   └── workflows
│       ├── README.md
│       ├── cd.yml
│       ├── ci.yml
│       ├── connectors-live-smoke.yml
│       ├── container-scan.yml
│       ├── contract-tests.yml
│       ├── dast-staging.yml
│       ├── dependency-audit.yml
│       ├── e2e-tests.yml
│       ├── iac-scan.yml
│       ├── license-compliance.yml
│       ├── migration-check.yml
│       ├── performance-smoke.yml
│       ├── pr-labeler.yml
│       ├── pr.yml
│       ├── promotion.yml
│       ├── release-gate.yml
│       ├── release.yml
│       ├── sbom.yml
│       ├── secret-scan.yml
│       ├── security-scan.yml
│       ├── static.yml
│       └── storybook-visual-regression.yml
├── .gitignore
├── .gitleaks.toml
├── .pre-commit-config.yaml
├── CLAUDE.md
├── CONTRIBUTING.md
├── INDEX.md
├── LICENSE
├── Makefile
├── README.md
├── SECURITY.md
├── agents
│   ├── AGENT_CATALOG.md
│   ├── README.md
│   ├── __init__.py
│   ├── common
│   │   ├── __init__.py
│   │   ├── connector_integration.py
│   │   ├── health_recommendations.py
│   │   ├── integration_services.py
│   │   ├── metrics_catalog.py
│   │   ├── scenario.py
│   │   └── web_search.py
│   ├── core-orchestration
│   │   ├── README.md
│   │   ├── approval-workflow-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── create_approval.py
│   │   │   │   │   ├── decision_actions.py
│   │   │   │   │   ├── escalation_actions.py
│   │   │   │   │   ├── lifecycle.py
│   │   │   │   │   ├── notification_actions.py
│   │   │   │   │   └── notification_delivery.py
│   │   │   │   ├── approval_utils.py
│   │   │   │   ├── approval_workflow_agent.py
│   │   │   │   ├── engine_infra.py
│   │   │   │   ├── engine_utils.py
│   │   │   │   ├── templates
│   │   │   │   │   ├── en
│   │   │   │   │   │   └── approval_notification.md
│   │   │   │   │   └── fr
│   │   │   │   │       └── approval_notification.md
│   │   │   │   ├── workflow_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── assign_task.py
│   │   │   │   │   ├── cancel_workflow.py
│   │   │   │   │   ├── complete_task.py
│   │   │   │   │   ├── define_workflow.py
│   │   │   │   │   ├── deploy_bpmn.py
│   │   │   │   │   ├── get_workflow_status.py
│   │   │   │   │   ├── handle_event.py
│   │   │   │   │   ├── pause_resume_workflow.py
│   │   │   │   │   ├── query_workflows.py
│   │   │   │   │   ├── retry_failed_task.py
│   │   │   │   │   ├── start_workflow.py
│   │   │   │   │   └── worker.py
│   │   │   │   ├── workflow_engine_agent.py
│   │   │   │   ├── workflow_spec.py
│   │   │   │   ├── workflow_state_store.py
│   │   │   │   └── workflow_task_queue.py
│   │   │   └── workflows
│   │   │       └── schema
│   │   │           └── workflow_spec.schema.json
│   │   ├── intent-router-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── models
│   │   │   │   └── intent_classifier
│   │   │   │       └── README.md
│   │   │   ├── src
│   │   │   │   ├── intent_router_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── routing_actions.py
│   │   │   │   ├── intent_router_agent.py
│   │   │   │   ├── intent_router_models.py
│   │   │   │   └── intent_router_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_intent_router_agent.py
│   │   ├── response-orchestration-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── plan_schema.py
│   │   │   │   ├── response_orchestration_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── orchestration_actions.py
│   │   │   │   ├── response_orchestration_agent.py
│   │   │   │   ├── response_orchestration_models.py
│   │   │   │   └── response_orchestration_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_response_orchestration_agent.py
│   │   └── workspace-setup-agent
│   │       ├── Dockerfile
│   │       ├── README.md
│   │       ├── demo-fixtures
│   │       │   └── sample-response.json
│   │       ├── src
│   │       │   └── workspace_setup_agent.py
│   │       └── tests
│   │           ├── README.md
│   │           └── test_workspace_setup_agent.py
│   ├── delivery-management
│   │   ├── README.md
│   │   ├── compliance-governance-agent
│   │   │   ├── COMPLIANCE_CONTROL_CATALOG.md
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── compliance_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── add_regulation.py
│   │   │   │   │   ├── assess_compliance.py
│   │   │   │   │   ├── audit.py
│   │   │   │   │   ├── dashboard.py
│   │   │   │   │   ├── define_control.py
│   │   │   │   │   ├── evidence.py
│   │   │   │   │   ├── manage_policy.py
│   │   │   │   │   ├── map_controls.py
│   │   │   │   │   ├── monitor_regulatory.py
│   │   │   │   │   ├── release_compliance.py
│   │   │   │   │   ├── reporting.py
│   │   │   │   │   └── test_control.py
│   │   │   │   ├── compliance_models.py
│   │   │   │   ├── compliance_regulatory_agent.py
│   │   │   │   ├── compliance_seed.py
│   │   │   │   └── compliance_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_compliance_regulatory_agent.py
│   │   ├── financial-management-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── financial_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── budget_actions.py
│   │   │   │   │   ├── cost_actions.py
│   │   │   │   │   ├── evm_actions.py
│   │   │   │   │   ├── forecast_actions.py
│   │   │   │   │   ├── profitability_actions.py
│   │   │   │   │   ├── report_actions.py
│   │   │   │   │   └── variance_actions.py
│   │   │   │   ├── financial_management_agent.py
│   │   │   │   ├── financial_models.py
│   │   │   │   └── financial_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_financial_management_agent.py
│   │   ├── lifecycle-governance-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── lifecycle_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── evaluate_gate.py
│   │   │   │   │   ├── initiate_project.py
│   │   │   │   │   ├── monitor_health.py
│   │   │   │   │   ├── override_gate.py
│   │   │   │   │   ├── query_actions.py
│   │   │   │   │   ├── readiness_actions.py
│   │   │   │   │   ├── recommend_methodology.py
│   │   │   │   │   └── transition_phase.py
│   │   │   │   ├── lifecycle_persistence.py
│   │   │   │   ├── lifecycle_utils.py
│   │   │   │   ├── monitoring.py
│   │   │   │   ├── notifications.py
│   │   │   │   ├── orchestration.py
│   │   │   │   ├── project_lifecycle_agent.py
│   │   │   │   ├── readiness_model.py
│   │   │   │   ├── summarization.py
│   │   │   │   └── sync_clients.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_lifecycle_agent.py
│   │   ├── quality-management-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── quality_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── analysis_actions.py
│   │   │   │   │   ├── audit_actions.py
│   │   │   │   │   ├── defect_actions.py
│   │   │   │   │   ├── metric_actions.py
│   │   │   │   │   ├── plan_actions.py
│   │   │   │   │   ├── reporting_actions.py
│   │   │   │   │   ├── requirement_actions.py
│   │   │   │   │   ├── review_actions.py
│   │   │   │   │   └── test_actions.py
│   │   │   │   ├── quality_management_agent.py
│   │   │   │   ├── quality_models.py
│   │   │   │   └── quality_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_quality_management_agent.py
│   │   ├── resource-management-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── resource_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── allocation.py
│   │   │   │   │   ├── analytics.py
│   │   │   │   │   ├── demand_management.py
│   │   │   │   │   ├── helpers.py
│   │   │   │   │   ├── planning.py
│   │   │   │   │   ├── reporting.py
│   │   │   │   │   └── sync.py
│   │   │   │   ├── resource_capacity_agent.py
│   │   │   │   ├── resource_models.py
│   │   │   │   └── resource_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_resource_management_agent.py
│   │   ├── risk-management-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── data
│   │   │   │   └── feedback.sqlite3
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── risk_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── assess_risk.py
│   │   │   │   │   ├── create_mitigation_plan.py
│   │   │   │   │   ├── generate_risk_matrix.py
│   │   │   │   │   ├── generate_risk_report.py
│   │   │   │   │   ├── get_risk_dashboard.py
│   │   │   │   │   ├── get_top_risks.py
│   │   │   │   │   ├── identify_risk.py
│   │   │   │   │   ├── monitor_triggers.py
│   │   │   │   │   ├── prioritize_risks.py
│   │   │   │   │   ├── research_risks.py
│   │   │   │   │   ├── run_monte_carlo.py
│   │   │   │   │   ├── sensitivity_analysis.py
│   │   │   │   │   └── update_risk_status.py
│   │   │   │   ├── risk_management_agent.py
│   │   │   │   ├── risk_management_api.py
│   │   │   │   ├── risk_models.py
│   │   │   │   ├── risk_nlp_training.py
│   │   │   │   └── risk_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_risk_management_agent_delivery.py
│   │   ├── schedule-planning-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── schedule_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── baseline.py
│   │   │   │   │   ├── create_schedule.py
│   │   │   │   │   ├── critical_path.py
│   │   │   │   │   ├── estimate_duration.py
│   │   │   │   │   ├── map_dependencies.py
│   │   │   │   │   ├── milestones.py
│   │   │   │   │   ├── monte_carlo.py
│   │   │   │   │   ├── optimize.py
│   │   │   │   │   ├── resource_scheduling.py
│   │   │   │   │   ├── schedule_crud.py
│   │   │   │   │   ├── sprint_planning.py
│   │   │   │   │   └── what_if.py
│   │   │   │   ├── schedule_models.py
│   │   │   │   ├── schedule_planning_agent.py
│   │   │   │   └── schedule_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_schedule_planning_agent.py
│   │   ├── scope-definition-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── definition_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── baseline_actions.py
│   │   │   │   │   ├── charter_actions.py
│   │   │   │   │   ├── requirements_actions.py
│   │   │   │   │   ├── scope_research_actions.py
│   │   │   │   │   ├── stakeholder_actions.py
│   │   │   │   │   └── wbs_actions.py
│   │   │   │   ├── definition_models.py
│   │   │   │   ├── definition_utils.py
│   │   │   │   ├── project_definition_agent.py
│   │   │   │   ├── scope_research.py
│   │   │   │   └── web_search.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_scope_definition_agent.py
│   │   └── vendor-procurement-agent
│   │       ├── Dockerfile
│   │       ├── PROCUREMENT_WORKFLOW_BOUNDARIES.md
│   │       ├── README.md
│   │       ├── demo-fixtures
│   │       │   └── sample-response.json
│   │       ├── src
│   │       │   ├── vendor_actions
│   │       │   │   ├── __init__.py
│   │       │   │   ├── contract.py
│   │       │   │   ├── event_handlers.py
│   │       │   │   ├── invoice.py
│   │       │   │   ├── onboard_vendor.py
│   │       │   │   ├── procurement_request.py
│   │       │   │   ├── purchase_order.py
│   │       │   │   ├── research_vendor.py
│   │       │   │   ├── rfp.py
│   │       │   │   ├── vendor_performance.py
│   │       │   │   ├── vendor_profile.py
│   │       │   │   └── vendor_search.py
│   │       │   ├── vendor_models.py
│   │       │   ├── vendor_procurement_agent.py
│   │       │   └── vendor_utils.py
│   │       └── tests
│   │           ├── README.md
│   │           └── test_vendor_procurement_agent.py
│   ├── operations-management
│   │   ├── README.md
│   │   ├── analytics-insights-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── analytics_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── aggregate_data.py
│   │   │   │   │   ├── compute_kpis.py
│   │   │   │   │   ├── create_dashboard.py
│   │   │   │   │   ├── data_lineage.py
│   │   │   │   │   ├── generate_narrative.py
│   │   │   │   │   ├── generate_report.py
│   │   │   │   │   ├── infrastructure.py
│   │   │   │   │   ├── insights.py
│   │   │   │   │   ├── periodic_report.py
│   │   │   │   │   ├── query_data.py
│   │   │   │   │   ├── run_prediction.py
│   │   │   │   │   ├── scenario_analysis.py
│   │   │   │   │   └── track_kpi.py
│   │   │   │   ├── analytics_insights_agent.py
│   │   │   │   ├── analytics_models.py
│   │   │   │   └── analytics_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_analytics_insights_agent.py
│   │   ├── change-control-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── change_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── approve_and_review.py
│   │   │   │   │   ├── classify_and_assess.py
│   │   │   │   │   ├── cmdb_actions.py
│   │   │   │   │   ├── implement_change.py
│   │   │   │   │   ├── reporting.py
│   │   │   │   │   ├── submit_change.py
│   │   │   │   │   └── webhook_and_monitoring.py
│   │   │   │   ├── change_configuration_agent.py
│   │   │   │   ├── change_models.py
│   │   │   │   └── change_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_change_configuration_agent.py
│   │   ├── continuous-improvement-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── ci_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── benchmarking.py
│   │   │   │   │   ├── conformance.py
│   │   │   │   │   ├── discovery.py
│   │   │   │   │   ├── improvement.py
│   │   │   │   │   ├── ingest.py
│   │   │   │   │   ├── insights.py
│   │   │   │   │   └── root_cause.py
│   │   │   │   ├── mining_models.py
│   │   │   │   ├── mining_utils.py
│   │   │   │   └── process_mining_agent.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_process_mining_agent.py
│   │   ├── data-synchronisation-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── data_sync_agent.py
│   │   │   │   ├── sync_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── conflicts.py
│   │   │   │   │   ├── connectors.py
│   │   │   │   │   ├── duplicates.py
│   │   │   │   │   ├── master_records.py
│   │   │   │   │   ├── monitoring.py
│   │   │   │   │   ├── retry.py
│   │   │   │   │   ├── schema.py
│   │   │   │   │   ├── sync_data.py
│   │   │   │   │   └── validation.py
│   │   │   │   ├── sync_infrastructure.py
│   │   │   │   ├── sync_models.py
│   │   │   │   └── sync_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_data_sync_agent.py
│   │   ├── knowledge-management-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── knowledge_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── classification_actions.py
│   │   │   │   │   ├── collaboration_actions.py
│   │   │   │   │   ├── document_actions.py
│   │   │   │   │   ├── ingestion_actions.py
│   │   │   │   │   ├── knowledge_graph_actions.py
│   │   │   │   │   └── search_actions.py
│   │   │   │   ├── knowledge_db.py
│   │   │   │   ├── knowledge_management_agent.py
│   │   │   │   ├── knowledge_models.py
│   │   │   │   └── knowledge_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_knowledge_management_agent.py
│   │   ├── release-deployment-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── release_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── assess_readiness.py
│   │   │   │   │   ├── create_deployment_plan.py
│   │   │   │   │   ├── deployment_metrics.py
│   │   │   │   │   ├── execute_deployment.py
│   │   │   │   │   ├── manage_environment.py
│   │   │   │   │   ├── plan_release.py
│   │   │   │   │   ├── query_status.py
│   │   │   │   │   ├── release_notes.py
│   │   │   │   │   ├── rollback_deployment.py
│   │   │   │   │   ├── schedule_window.py
│   │   │   │   │   └── verify_post_deployment.py
│   │   │   │   ├── release_deployment_agent.py
│   │   │   │   ├── release_models.py
│   │   │   │   └── release_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_release_deployment_agent.py
│   │   ├── stakeholder-communications-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── __init__.py
│   │   │   │   ├── actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── briefing_actions.py
│   │   │   │   │   ├── classify_stakeholder.py
│   │   │   │   │   ├── communication_plan.py
│   │   │   │   │   ├── dashboard_actions.py
│   │   │   │   │   ├── delivery_actions.py
│   │   │   │   │   ├── engagement_actions.py
│   │   │   │   │   ├── event_actions.py
│   │   │   │   │   ├── feedback_actions.py
│   │   │   │   │   ├── message_actions.py
│   │   │   │   │   ├── preferences_actions.py
│   │   │   │   │   └── register_stakeholder.py
│   │   │   │   ├── stakeholder_communications_agent.py
│   │   │   │   ├── stakeholder_models.py
│   │   │   │   └── stakeholder_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_stakeholder_communications_agent.py
│   │   └── system-health-agent
│   │       ├── Dockerfile
│   │       ├── README.md
│   │       ├── demo-fixtures
│   │       │   └── sample-response.json
│   │       ├── src
│   │       │   ├── health_actions
│   │       │   │   ├── __init__.py
│   │       │   │   ├── alert_management.py
│   │       │   │   ├── anomaly_detection.py
│   │       │   │   ├── capacity_planning.py
│   │       │   │   ├── check_health.py
│   │       │   │   ├── collect_metrics.py
│   │       │   │   ├── dashboard_reporting.py
│   │       │   │   └── incident_management.py
│   │       │   ├── health_init.py
│   │       │   ├── health_integrations.py
│   │       │   ├── health_utils.py
│   │       │   └── system_health_agent.py
│   │       └── tests
│   │           ├── README.md
│   │           └── test_system_health_agent.py
│   ├── portfolio-management
│   │   ├── README.md
│   │   ├── business-case-agent
│   │   │   ├── BOUNDARY-NOTES.md
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── business_case_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── analysis_actions.py
│   │   │   │   │   ├── generation_actions.py
│   │   │   │   │   ├── query_actions.py
│   │   │   │   │   └── roi_actions.py
│   │   │   │   ├── business_case_investment_agent.py
│   │   │   │   ├── business_case_models.py
│   │   │   │   └── business_case_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_business_case_investment_agent.py
│   │   ├── demand-intake-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── demand_intake_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── intake_actions.py
│   │   │   │   │   └── pipeline_actions.py
│   │   │   │   ├── demand_intake_agent.py
│   │   │   │   ├── demand_intake_models.py
│   │   │   │   └── demand_intake_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_demand_intake_agent.py
│   │   ├── portfolio-optimisation-agent
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures
│   │   │   │   └── sample-response.json
│   │   │   ├── src
│   │   │   │   ├── portfolio_actions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── optimization_actions.py
│   │   │   │   │   ├── prioritization_actions.py
│   │   │   │   │   ├── scenario_actions.py
│   │   │   │   │   └── status_actions.py
│   │   │   │   ├── portfolio_models.py
│   │   │   │   ├── portfolio_strategy_agent.py
│   │   │   │   └── portfolio_utils.py
│   │   │   └── tests
│   │   │       ├── README.md
│   │   │       └── test_portfolio_strategy_agent.py
│   │   └── program-management-agent
│   │       ├── Dockerfile
│   │       ├── README.md
│   │       ├── demo-fixtures
│   │       │   └── sample-response.json
│   │       ├── src
│   │       │   ├── program_actions
│   │       │   │   ├── __init__.py
│   │       │   │   ├── aggregate_benefits.py
│   │       │   │   ├── analyze_change_impact.py
│   │       │   │   ├── approval_actions.py
│   │       │   │   ├── coordinate_resources.py
│   │       │   │   ├── create_program.py
│   │       │   │   ├── generate_roadmap.py
│   │       │   │   ├── get_program_health.py
│   │       │   │   ├── identify_synergies.py
│   │       │   │   ├── optimize_program.py
│   │       │   │   └── track_dependencies.py
│   │       │   ├── program_infrastructure.py
│   │       │   ├── program_management_agent.py
│   │       │   ├── program_models.py
│   │       │   └── program_utils.py
│   │       └── tests
│   │           ├── README.md
│   │           └── test_program_management_agent.py
│   └── runtime
│       ├── README.md
│       ├── __init__.py
│       ├── eval
│       │   ├── README.md
│       │   ├── fixtures
│       │   │   ├── definition
│       │   │   │   └── definition-minimal.yaml
│       │   │   ├── flow-intent-router.yaml
│       │   │   ├── flow-orchestration.yaml
│       │   │   └── tools
│       │   │       └── tools-minimal.yaml
│       │   ├── manifest.yaml
│       │   └── run_eval.py
│       ├── prompts
│       │   ├── approval-workflow
│       │   │   └── approval_prompt_v1.md
│       │   ├── intent-router
│       │   │   └── classification_prompt_v1.md
│       │   ├── knowledge-agent
│       │   │   └── summary_prompt_v1.md
│       │   └── response-orchestration
│       │       └── orchestration_prompt_v1.md
│       ├── src
│       │   ├── __init__.py
│       │   ├── agent_catalog.py
│       │   ├── audit.py
│       │   ├── base_agent.py
│       │   ├── data_service.py
│       │   ├── event_bus.py
│       │   ├── execution_events.py
│       │   ├── memory_store.py
│       │   ├── models.py
│       │   ├── notification_service.py
│       │   ├── orchestrator.py
│       │   ├── policy.py
│       │   └── state_store.py
│       └── timeout_harness.py
├── apps
│   ├── README.md
│   ├── admin-console
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── src
│   │   │   ├── admin_store.py
│   │   │   ├── config.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── README.md
│   ├── analytics-service
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── job_registry.py
│   │   ├── jobs
│   │   │   ├── README.md
│   │   │   ├── manifests
│   │   │   │   └── daily-portfolio-rollup.yaml
│   │   │   └── schema
│   │   │       └── job-manifest.schema.json
│   │   ├── models
│   │   │   └── README.md
│   │   ├── src
│   │   │   ├── config.py
│   │   │   ├── health.py
│   │   │   ├── kpi_engine.py
│   │   │   ├── main.py
│   │   │   ├── metrics_store.py
│   │   │   ├── predictive.py
│   │   │   ├── predictive_models.py
│   │   │   ├── predictive_routes.py
│   │   │   └── scheduler.py
│   │   └── tests
│   │       ├── README.md
│   │       └── test_scheduler.py
│   ├── api-gateway
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── leader-election-configmap.yaml
│   │   │   │   ├── leader-election-rbac.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   ├── secretproviderclass.yaml
│   │   │   │   ├── service.yaml
│   │   │   │   └── serviceaccount.yaml
│   │   │   └── values.yaml
│   │   ├── migrations
│   │   │   └── sql
│   │   │       ├── 001_init_postgresql.sql
│   │   │       └── 001_init_sqlite.sql
│   │   ├── openapi
│   │   │   └── README.md
│   │   ├── src
│   │   │   ├── README.md
│   │   │   └── api
│   │   │       ├── README.md
│   │   │       ├── __init__.py
│   │   │       ├── bootstrap
│   │   │       │   ├── __init__.py
│   │   │       │   ├── components.py
│   │   │       │   ├── connector_component.py
│   │   │       │   ├── document_session_component.py
│   │   │       │   ├── leader_election_component.py
│   │   │       │   ├── orchestrator_component.py
│   │   │       │   ├── registry.py
│   │   │       │   └── secret_rotation_component.py
│   │   │       ├── certification_storage.py
│   │   │       ├── circuit_breaker.py
│   │   │       ├── config.py
│   │   │       ├── connector_loader.py
│   │   │       ├── cors.py
│   │   │       ├── dependencies.py
│   │   │       ├── document_session_store.py
│   │   │       ├── leader_election.py
│   │   │       ├── limiter.py
│   │   │       ├── main.py
│   │   │       ├── middleware
│   │   │       │   ├── __init__.py
│   │   │       │   └── security.py
│   │   │       ├── routes
│   │   │       │   ├── __init__.py
│   │   │       │   ├── admin.py
│   │   │       │   ├── agent_config.py
│   │   │       │   ├── agents.py
│   │   │       │   ├── analytics.py
│   │   │       │   ├── audit.py
│   │   │       │   ├── certifications.py
│   │   │       │   ├── compliance_research.py
│   │   │       │   ├── connectors.py
│   │   │       │   ├── documents.py
│   │   │       │   ├── health.py
│   │   │       │   ├── lineage.py
│   │   │       │   ├── marketplace.py
│   │   │       │   ├── risk_research.py
│   │   │       │   ├── scope_research.py
│   │   │       │   ├── vendor_management.py
│   │   │       │   ├── vendor_research.py
│   │   │       │   └── workflows.py
│   │   │       ├── runtime_bootstrap.py
│   │   │       ├── schemas
│   │   │       │   ├── __init__.py
│   │   │       │   └── certification.schema.json
│   │   │       ├── secret_rotation.py
│   │   │       ├── slowapi_compat.py
│   │   │       └── webhook_storage.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── conftest.py
│   │       ├── test_agents_and_circuit_breaker.py
│   │       ├── test_bootstrap_lifecycle.py
│   │       ├── test_connectors_routes.py
│   │       ├── test_document_session_store_concurrency.py
│   │       ├── test_document_session_store_policy.py
│   │       ├── test_security_middleware.py
│   │       └── test_workflows_routes.py
│   ├── connector-hub
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── registry
│   │   │   └── README.md
│   │   ├── sandbox
│   │   │   ├── README.md
│   │   │   ├── examples
│   │   │   │   └── github-sandbox-connector.yaml
│   │   │   ├── fixtures
│   │   │   │   ├── issues.json
│   │   │   │   └── repo.json
│   │   │   └── schema
│   │   │       └── sandbox-connector.schema.json
│   │   ├── sandbox_registry.py
│   │   ├── src
│   │   │   ├── connector_storage.py
│   │   │   ├── health_aggregator.py
│   │   │   ├── health_models.py
│   │   │   ├── health_routes.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── README.md
│   ├── demo_streamlit
│   │   ├── .streamlit
│   │   │   └── config.toml
│   │   ├── app.py
│   │   ├── data
│   │   │   ├── assistant_outcome_variants.json
│   │   │   └── feature_flags_demo.json
│   │   ├── storage
│   │   │   └── demo_outbox.json
│   │   └── validate_demo.py
│   ├── document-service
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── document_policy_config.py
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── migrations
│   │   │   └── README.md
│   │   ├── policies
│   │   │   ├── README.md
│   │   │   ├── bundles
│   │   │   │   └── default-policy-bundle.yaml
│   │   │   └── schema
│   │   │       └── policy-bundle.schema.json
│   │   ├── src
│   │   │   ├── briefing_renderer.py
│   │   │   ├── config.py
│   │   │   ├── document_policy.py
│   │   │   ├── document_storage.py
│   │   │   └── main.py
│   │   └── tests
│   │       ├── README.md
│   │       └── test_document_dlp_and_crypto.py
│   ├── mobile
│   │   ├── App.tsx
│   │   ├── README.md
│   │   ├── app.json
│   │   ├── babel.config.js
│   │   ├── jest.config.js
│   │   ├── package.json
│   │   ├── src
│   │   │   ├── README.md
│   │   │   ├── api
│   │   │   │   └── client.ts
│   │   │   ├── components
│   │   │   │   ├── AppErrorBoundary.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── LabelValueRow.tsx
│   │   │   │   ├── Sparkline.tsx
│   │   │   │   └── __tests__
│   │   │   │       └── AppErrorBoundary.test.tsx
│   │   │   ├── context
│   │   │   │   ├── AppContext.tsx
│   │   │   │   └── __tests__
│   │   │   │       └── AppContext.test.tsx
│   │   │   ├── i18n
│   │   │   │   ├── index.tsx
│   │   │   │   └── locales
│   │   │   │       ├── de.json
│   │   │   │       └── en.json
│   │   │   ├── integration
│   │   │   │   └── mobileFlows.integration.test.tsx
│   │   │   ├── screens
│   │   │   │   ├── ApprovalsScreen.tsx
│   │   │   │   ├── AssistantScreen.tsx
│   │   │   │   ├── CanvasScreen.tsx
│   │   │   │   ├── ConnectorsScreen.tsx
│   │   │   │   ├── DashboardScreen.tsx
│   │   │   │   ├── LoginScreen.tsx
│   │   │   │   ├── MethodologiesScreen.tsx
│   │   │   │   ├── StatusUpdatesScreen.tsx
│   │   │   │   └── TenantSelectionScreen.tsx
│   │   │   ├── services
│   │   │   │   ├── approvalQueue.ts
│   │   │   │   ├── biometricAuth.ts
│   │   │   │   ├── notifications.ts
│   │   │   │   ├── secureSession.ts
│   │   │   │   ├── statusQueue.ts
│   │   │   │   └── telemetry.ts
│   │   │   └── theme.ts
│   │   └── tsconfig.json
│   ├── orchestration-service
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── leader-election-configmap.yaml
│   │   │   │   ├── leader-election-rbac.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   ├── service.yaml
│   │   │   │   └── serviceaccount.yaml
│   │   │   └── values.yaml
│   │   ├── planners
│   │   │   └── README.md
│   │   ├── policies
│   │   │   ├── README.md
│   │   │   ├── bundles
│   │   │   │   └── default-policy-bundle.yaml
│   │   │   └── schema
│   │   │       └── policy-bundle.schema.json
│   │   ├── src
│   │   │   ├── config.py
│   │   │   ├── leader_election.py
│   │   │   ├── main.py
│   │   │   ├── orchestrator.py
│   │   │   ├── persistence.py
│   │   │   └── workflow_client.py
│   │   ├── storage
│   │   │   └── orchestration-state.json
│   │   └── tests
│   │       └── README.md
│   ├── web
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── data
│   │   │   ├── README.md
│   │   │   ├── agents.json
│   │   │   ├── demo
│   │   │   │   ├── demo_run_log.json
│   │   │   │   └── sor_fixtures.json
│   │   │   ├── demo_conversations
│   │   │   │   ├── deliver_status_report.json
│   │   │   │   ├── design_wbs.json
│   │   │   │   ├── discover_charter.json
│   │   │   │   ├── embed_lessons_learned.json
│   │   │   │   ├── financial_review.json
│   │   │   │   ├── portfolio_review.json
│   │   │   │   ├── project_intake.json
│   │   │   │   ├── resource_request.json
│   │   │   │   ├── risk_review.json
│   │   │   │   ├── stage_gate_approval.json
│   │   │   │   └── vendor_procurement.json
│   │   │   ├── demo_dashboards
│   │   │   │   ├── approvals.json
│   │   │   │   ├── delivery_governance.json
│   │   │   │   ├── executive_portfolio.json
│   │   │   │   ├── lifecycle-metrics.json
│   │   │   │   ├── portfolio-health.json
│   │   │   │   ├── project-dashboard-aggregations.json
│   │   │   │   ├── project-dashboard-health.json
│   │   │   │   ├── project-dashboard-issues.json
│   │   │   │   ├── project-dashboard-kpis.json
│   │   │   │   ├── project-dashboard-narrative.json
│   │   │   │   ├── project-dashboard-quality.json
│   │   │   │   ├── project-dashboard-risks.json
│   │   │   │   ├── project-dashboard-trends.json
│   │   │   │   ├── vendor_procurement_risk.json
│   │   │   │   └── workflow-monitoring.json
│   │   │   ├── demo_seed.json
│   │   │   ├── knowledge.db
│   │   │   ├── llm_models.json
│   │   │   ├── merge_review_seed.json
│   │   │   ├── methodology_node_runtime.json
│   │   │   ├── ppm.db
│   │   │   ├── projects.json
│   │   │   ├── requirements.json
│   │   │   ├── roles.json
│   │   │   ├── seed.json
│   │   │   ├── template_mappings.json
│   │   │   ├── templates.json
│   │   │   └── workflows
│   │   │       ├── change_request.json
│   │   │       └── intake_to_delivery.json
│   │   ├── e2e
│   │   │   └── README.md
│   │   ├── frontend
│   │   │   ├── .eslintrc.cjs
│   │   │   ├── .gitignore
│   │   │   ├── .storybook
│   │   │   │   ├── main.ts
│   │   │   │   ├── preview.ts
│   │   │   │   └── test-runner.ts
│   │   │   ├── README.md
│   │   │   ├── index.html
│   │   │   ├── package-lock.json
│   │   │   ├── package.json
│   │   │   ├── public
│   │   │   │   └── favicon.svg
│   │   │   ├── scripts
│   │   │   │   ├── check-design-tokens.mjs
│   │   │   │   ├── check-raw-json-casts.mjs
│   │   │   │   ├── generate-css-module-types.mjs
│   │   │   │   └── raw-json-cast-allowlist.txt
│   │   │   ├── src
│   │   │   │   ├── App.demo.test.tsx
│   │   │   │   ├── App.module.css
│   │   │   │   ├── App.module.css.d.ts
│   │   │   │   ├── App.tsx
│   │   │   │   ├── README.md
│   │   │   │   ├── auth
│   │   │   │   │   └── permissions.ts
│   │   │   │   ├── components
│   │   │   │   │   ├── agentConfig
│   │   │   │   │   │   ├── AgentGallery.module.css
│   │   │   │   │   │   ├── AgentGallery.module.css.d.ts
│   │   │   │   │   │   ├── AgentGallery.tsx
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── agentRuns
│   │   │   │   │   │   ├── AgentRunDetail.module.css
│   │   │   │   │   │   ├── AgentRunDetail.module.css.d.ts
│   │   │   │   │   │   ├── AgentRunDetail.tsx
│   │   │   │   │   │   ├── AgentRunList.module.css
│   │   │   │   │   │   ├── AgentRunList.module.css.d.ts
│   │   │   │   │   │   ├── AgentRunList.tsx
│   │   │   │   │   │   ├── ProgressBadge.module.css
│   │   │   │   │   │   ├── ProgressBadge.module.css.d.ts
│   │   │   │   │   │   └── ProgressBadge.tsx
│   │   │   │   │   ├── analytics
│   │   │   │   │   │   ├── ScenarioBuilder.module.css
│   │   │   │   │   │   ├── ScenarioBuilder.module.css.d.ts
│   │   │   │   │   │   └── ScenarioBuilder.tsx
│   │   │   │   │   ├── assistant
│   │   │   │   │   │   ├── ActionChipButton.module.css
│   │   │   │   │   │   ├── ActionChipButton.module.css.d.ts
│   │   │   │   │   │   ├── ActionChipButton.tsx
│   │   │   │   │   │   ├── AgentActivityPanel.module.css
│   │   │   │   │   │   ├── AgentActivityPanel.module.css.d.ts
│   │   │   │   │   │   ├── AgentActivityPanel.tsx
│   │   │   │   │   │   ├── AssistantHeader.module.css
│   │   │   │   │   │   ├── AssistantHeader.module.css.d.ts
│   │   │   │   │   │   ├── AssistantHeader.tsx
│   │   │   │   │   │   ├── AssistantPanel.demo.test.tsx
│   │   │   │   │   │   ├── AssistantPanel.module.css
│   │   │   │   │   │   ├── AssistantPanel.module.css.d.ts
│   │   │   │   │   │   ├── AssistantPanel.test.tsx
│   │   │   │   │   │   ├── AssistantPanel.tsx
│   │   │   │   │   │   ├── ChatInput.module.css
│   │   │   │   │   │   ├── ChatInput.module.css.d.ts
│   │   │   │   │   │   ├── ChatInput.test.tsx
│   │   │   │   │   │   ├── ChatInput.tsx
│   │   │   │   │   │   ├── ContextBar.module.css
│   │   │   │   │   │   ├── ContextBar.module.css.d.ts
│   │   │   │   │   │   ├── ContextBar.test.tsx
│   │   │   │   │   │   ├── ContextBar.tsx
│   │   │   │   │   │   ├── ConversationalCommandCard.module.css
│   │   │   │   │   │   ├── ConversationalCommandCard.module.css.d.ts
│   │   │   │   │   │   ├── ConversationalCommandCard.tsx
│   │   │   │   │   │   ├── MessageBubble.module.css
│   │   │   │   │   │   ├── MessageBubble.module.css.d.ts
│   │   │   │   │   │   ├── MessageBubble.tsx
│   │   │   │   │   │   ├── MessageList.module.css
│   │   │   │   │   │   ├── MessageList.module.css.d.ts
│   │   │   │   │   │   ├── MessageList.test.tsx
│   │   │   │   │   │   ├── MessageList.tsx
│   │   │   │   │   │   ├── PromptPicker.module.css
│   │   │   │   │   │   ├── PromptPicker.module.css.d.ts
│   │   │   │   │   │   ├── PromptPicker.tsx
│   │   │   │   │   │   ├── QuickActions.module.css
│   │   │   │   │   │   ├── QuickActions.module.css.d.ts
│   │   │   │   │   │   ├── QuickActions.test.tsx
│   │   │   │   │   │   ├── QuickActions.tsx
│   │   │   │   │   │   ├── ScopeResearchCard.module.css
│   │   │   │   │   │   ├── ScopeResearchCard.module.css.d.ts
│   │   │   │   │   │   ├── ScopeResearchCard.tsx
│   │   │   │   │   │   ├── assistantMode.test.ts
│   │   │   │   │   │   ├── assistantMode.ts
│   │   │   │   │   │   ├── entryQuickActions.ts
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── canvas
│   │   │   │   │   │   ├── AgentAnnotationOverlay.module.css
│   │   │   │   │   │   ├── AgentAnnotationOverlay.module.css.d.ts
│   │   │   │   │   │   ├── AgentAnnotationOverlay.tsx
│   │   │   │   │   │   ├── CanvasWorkspace.module.css
│   │   │   │   │   │   ├── CanvasWorkspace.module.css.d.ts
│   │   │   │   │   │   ├── CanvasWorkspace.tsx
│   │   │   │   │   │   ├── NewCanvasTypes.smoke.test.tsx
│   │   │   │   │   │   ├── PresenceIndicators.module.css
│   │   │   │   │   │   ├── PresenceIndicators.module.css.d.ts
│   │   │   │   │   │   ├── PresenceIndicators.tsx
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── collections
│   │   │   │   │   │   ├── BulkActions.module.css
│   │   │   │   │   │   ├── BulkActions.module.css.d.ts
│   │   │   │   │   │   ├── BulkActions.tsx
│   │   │   │   │   │   ├── EntityTable.module.css
│   │   │   │   │   │   ├── EntityTable.module.css.d.ts
│   │   │   │   │   │   ├── EntityTable.tsx
│   │   │   │   │   │   ├── FacetedFilter.module.css
│   │   │   │   │   │   ├── FacetedFilter.module.css.d.ts
│   │   │   │   │   │   └── FacetedFilter.tsx
│   │   │   │   │   ├── config
│   │   │   │   │   │   ├── ConfigForm.module.css
│   │   │   │   │   │   ├── ConfigForm.module.css.d.ts
│   │   │   │   │   │   ├── ConfigForm.test.tsx
│   │   │   │   │   │   ├── ConfigForm.tsx
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── connectors
│   │   │   │   │   │   ├── CategorySection.tsx
│   │   │   │   │   │   ├── CertificationModal.tsx
│   │   │   │   │   │   ├── ConnectorCard.tsx
│   │   │   │   │   │   ├── ConnectorConfigModal.tsx
│   │   │   │   │   │   ├── ConnectorGallery.module.css
│   │   │   │   │   │   ├── ConnectorGallery.module.css.d.ts
│   │   │   │   │   │   ├── ConnectorGallery.test.tsx
│   │   │   │   │   │   ├── ConnectorGallery.tsx
│   │   │   │   │   │   ├── ConnectorIcon.tsx
│   │   │   │   │   │   ├── ConnectorSearchFilters.tsx
│   │   │   │   │   │   ├── SyncStatusPanel.module.css
│   │   │   │   │   │   ├── SyncStatusPanel.module.css.d.ts
│   │   │   │   │   │   ├── SyncStatusPanel.tsx
│   │   │   │   │   │   ├── connectorGalleryTypes.ts
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── dashboard
│   │   │   │   │   │   ├── HealthBadge.module.css
│   │   │   │   │   │   ├── HealthBadge.module.css.d.ts
│   │   │   │   │   │   ├── HealthBadge.tsx
│   │   │   │   │   │   ├── KpiWidget.module.css
│   │   │   │   │   │   ├── KpiWidget.module.css.d.ts
│   │   │   │   │   │   ├── KpiWidget.tsx
│   │   │   │   │   │   ├── StatusIndicator.module.css
│   │   │   │   │   │   ├── StatusIndicator.module.css.d.ts
│   │   │   │   │   │   └── StatusIndicator.tsx
│   │   │   │   │   ├── docs
│   │   │   │   │   │   ├── CoeditEditor.module.css
│   │   │   │   │   │   ├── CoeditEditor.module.css.d.ts
│   │   │   │   │   │   └── CoeditEditor.tsx
│   │   │   │   │   ├── icon
│   │   │   │   │   │   ├── Icon.module.css
│   │   │   │   │   │   ├── Icon.module.css.d.ts
│   │   │   │   │   │   ├── Icon.tsx
│   │   │   │   │   │   └── iconMap.ts
│   │   │   │   │   ├── intake
│   │   │   │   │   │   ├── AutoClassificationBadge.module.css
│   │   │   │   │   │   ├── AutoClassificationBadge.module.css.d.ts
│   │   │   │   │   │   ├── AutoClassificationBadge.tsx
│   │   │   │   │   │   ├── DuplicateDetectionPanel.module.css
│   │   │   │   │   │   ├── DuplicateDetectionPanel.module.css.d.ts
│   │   │   │   │   │   └── DuplicateDetectionPanel.tsx
│   │   │   │   │   ├── knowledge
│   │   │   │   │   │   ├── RecommendationSidebar.module.css
│   │   │   │   │   │   ├── RecommendationSidebar.module.css.d.ts
│   │   │   │   │   │   └── RecommendationSidebar.tsx
│   │   │   │   │   ├── layout
│   │   │   │   │   │   ├── AppLayout.module.css
│   │   │   │   │   │   ├── AppLayout.module.css.d.ts
│   │   │   │   │   │   ├── AppLayout.test.tsx
│   │   │   │   │   │   ├── AppLayout.tsx
│   │   │   │   │   │   ├── Header.module.css
│   │   │   │   │   │   ├── Header.module.css.d.ts
│   │   │   │   │   │   ├── Header.tsx
│   │   │   │   │   │   ├── LeftPanel.module.css
│   │   │   │   │   │   ├── LeftPanel.module.css.d.ts
│   │   │   │   │   │   ├── LeftPanel.test.tsx
│   │   │   │   │   │   ├── LeftPanel.tsx
│   │   │   │   │   │   ├── MainCanvas.module.css
│   │   │   │   │   │   ├── MainCanvas.module.css.d.ts
│   │   │   │   │   │   ├── MainCanvas.tsx
│   │   │   │   │   │   ├── SearchOverlay.module.css
│   │   │   │   │   │   ├── SearchOverlay.module.css.d.ts
│   │   │   │   │   │   ├── SearchOverlay.tsx
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── methodology
│   │   │   │   │   │   ├── ActivityDetailPanel.test.tsx
│   │   │   │   │   │   ├── ActivityDetailPanel.tsx
│   │   │   │   │   │   ├── MethodologyMapCanvas.module.css
│   │   │   │   │   │   ├── MethodologyMapCanvas.module.css.d.ts
│   │   │   │   │   │   ├── MethodologyMapCanvas.test.tsx
│   │   │   │   │   │   ├── MethodologyMapCanvas.tsx
│   │   │   │   │   │   ├── MethodologyNav.module.css
│   │   │   │   │   │   ├── MethodologyNav.module.css.d.ts
│   │   │   │   │   │   ├── MethodologyNav.test.tsx
│   │   │   │   │   │   ├── MethodologyNav.tsx
│   │   │   │   │   │   ├── MethodologyWorkspaceSurface.test.ts
│   │   │   │   │   │   ├── MethodologyWorkspaceSurface.tsx
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── onboarding
│   │   │   │   │   │   ├── OnboardingTour.module.css
│   │   │   │   │   │   ├── OnboardingTour.module.css.d.ts
│   │   │   │   │   │   ├── OnboardingTour.tsx
│   │   │   │   │   │   └── onboardingMessages.ts
│   │   │   │   │   ├── project
│   │   │   │   │   │   ├── AgentGallery.module.css
│   │   │   │   │   │   ├── AgentGallery.module.css.d.ts
│   │   │   │   │   │   ├── AgentGallery.tsx
│   │   │   │   │   │   ├── CertificationModal.tsx
│   │   │   │   │   │   ├── ConnectorCard.tsx
│   │   │   │   │   │   ├── ConnectorCategorySection.tsx
│   │   │   │   │   │   ├── ConnectorConfigModal.tsx
│   │   │   │   │   │   ├── ConnectorFilterBar.tsx
│   │   │   │   │   │   ├── ConnectorIcon.tsx
│   │   │   │   │   │   ├── McpProjectConfigSection.tsx
│   │   │   │   │   │   ├── ProjectConfigSection.module.css
│   │   │   │   │   │   ├── ProjectConfigSection.module.css.d.ts
│   │   │   │   │   │   ├── ProjectConfigSection.tsx
│   │   │   │   │   │   ├── ProjectConnectorGallery.tsx
│   │   │   │   │   │   ├── ProjectMcpSidebar.module.css
│   │   │   │   │   │   ├── ProjectMcpSidebar.module.css.d.ts
│   │   │   │   │   │   ├── ProjectMcpSidebar.tsx
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   └── projectConnectorTypes.ts
│   │   │   │   │   ├── security
│   │   │   │   │   │   ├── ClassificationBadge.module.css
│   │   │   │   │   │   ├── ClassificationBadge.module.css.d.ts
│   │   │   │   │   │   ├── ClassificationBadge.tsx
│   │   │   │   │   │   ├── PolicyEditor.module.css
│   │   │   │   │   │   ├── PolicyEditor.module.css.d.ts
│   │   │   │   │   │   └── PolicyEditor.tsx
│   │   │   │   │   ├── templates
│   │   │   │   │   │   ├── TemplateGallery.module.css
│   │   │   │   │   │   ├── TemplateGallery.module.css.d.ts
│   │   │   │   │   │   ├── TemplateGallery.tsx
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── theme
│   │   │   │   │   │   └── ThemeProvider.tsx
│   │   │   │   │   ├── tours
│   │   │   │   │   │   ├── TourProvider.module.css
│   │   │   │   │   │   ├── TourProvider.module.css.d.ts
│   │   │   │   │   │   ├── TourProvider.test.tsx
│   │   │   │   │   │   ├── TourProvider.tsx
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── ui
│   │   │   │   │   │   ├── ConfirmDialog.module.css
│   │   │   │   │   │   ├── ConfirmDialog.module.css.d.ts
│   │   │   │   │   │   ├── ConfirmDialog.tsx
│   │   │   │   │   │   ├── EmptyState.module.css
│   │   │   │   │   │   ├── EmptyState.module.css.d.ts
│   │   │   │   │   │   ├── EmptyState.tsx
│   │   │   │   │   │   ├── ErrorBoundary.test.tsx
│   │   │   │   │   │   ├── ErrorBoundary.tsx
│   │   │   │   │   │   ├── FadeIn.module.css
│   │   │   │   │   │   ├── FadeIn.module.css.d.ts
│   │   │   │   │   │   ├── FadeIn.tsx
│   │   │   │   │   │   ├── FocusTrap.tsx
│   │   │   │   │   │   ├── Skeleton.module.css
│   │   │   │   │   │   ├── Skeleton.module.css.d.ts
│   │   │   │   │   │   └── Skeleton.tsx
│   │   │   │   │   └── workflow
│   │   │   │   │       ├── NLWorkflowInput.module.css
│   │   │   │   │       ├── NLWorkflowInput.module.css.d.ts
│   │   │   │   │       └── NLWorkflowInput.tsx
│   │   │   │   ├── e2e
│   │   │   │   │   ├── criticalJourneys.test.tsx
│   │   │   │   │   └── intakeAssistantRegression.test.tsx
│   │   │   │   ├── hooks
│   │   │   │   │   ├── assistant
│   │   │   │   │   │   ├── useAssistantChat.ts
│   │   │   │   │   │   ├── useContextSync.ts
│   │   │   │   │   │   ├── useCopilotStream.ts
│   │   │   │   │   │   ├── useIntakeAssistantAdapter.ts
│   │   │   │   │   │   └── useSuggestionEngine.ts
│   │   │   │   │   ├── useRealtimeConsole.ts
│   │   │   │   │   └── useRequestState.ts
│   │   │   │   ├── i18n
│   │   │   │   │   ├── index.tsx
│   │   │   │   │   └── locales
│   │   │   │   │       ├── de.json
│   │   │   │   │       ├── en.json
│   │   │   │   │       └── pseudo.json
│   │   │   │   ├── main.tsx
│   │   │   │   ├── pages
│   │   │   │   │   ├── AgentMarketplacePage.module.css
│   │   │   │   │   ├── AgentMarketplacePage.module.css.d.ts
│   │   │   │   │   ├── AgentMarketplacePage.tsx
│   │   │   │   │   ├── AgentProfilePage.module.css
│   │   │   │   │   ├── AgentProfilePage.module.css.d.ts
│   │   │   │   │   ├── AgentProfilePage.test.tsx
│   │   │   │   │   ├── AgentProfilePage.tsx
│   │   │   │   │   ├── AgentRunsPage.module.css
│   │   │   │   │   ├── AgentRunsPage.module.css.d.ts
│   │   │   │   │   ├── AgentRunsPage.tsx
│   │   │   │   │   ├── AnalyticsDashboard.module.css
│   │   │   │   │   ├── AnalyticsDashboard.module.css.d.ts
│   │   │   │   │   ├── AnalyticsDashboard.tsx
│   │   │   │   │   ├── ApprovalsPage.module.css
│   │   │   │   │   ├── ApprovalsPage.module.css.d.ts
│   │   │   │   │   ├── ApprovalsPage.tsx
│   │   │   │   │   ├── AuditLogPage.module.css
│   │   │   │   │   ├── AuditLogPage.module.css.d.ts
│   │   │   │   │   ├── AuditLogPage.tsx
│   │   │   │   │   ├── CapacityPlanningPage.module.css
│   │   │   │   │   ├── CapacityPlanningPage.module.css.d.ts
│   │   │   │   │   ├── CapacityPlanningPage.tsx
│   │   │   │   │   ├── ConfigPage.module.css
│   │   │   │   │   ├── ConfigPage.module.css.d.ts
│   │   │   │   │   ├── ConfigPage.test.tsx
│   │   │   │   │   ├── ConfigPage.tsx
│   │   │   │   │   ├── ConnectorDetailPage.module.css
│   │   │   │   │   ├── ConnectorDetailPage.module.css.d.ts
│   │   │   │   │   ├── ConnectorDetailPage.tsx
│   │   │   │   │   ├── ConnectorHealthDashboardPage.module.css
│   │   │   │   │   ├── ConnectorHealthDashboardPage.module.css.d.ts
│   │   │   │   │   ├── ConnectorHealthDashboardPage.tsx
│   │   │   │   │   ├── ConnectorMarketplacePage.tsx
│   │   │   │   │   ├── DemoRunPage.module.css
│   │   │   │   │   ├── DemoRunPage.module.css.d.ts
│   │   │   │   │   ├── DemoRunPage.tsx
│   │   │   │   │   ├── DocumentSearchPage.module.css
│   │   │   │   │   ├── DocumentSearchPage.module.css.d.ts
│   │   │   │   │   ├── DocumentSearchPage.tsx
│   │   │   │   │   ├── EnterpriseUpliftPage.test.tsx
│   │   │   │   │   ├── EnterpriseUpliftPage.tsx
│   │   │   │   │   ├── ExecutiveBriefingPage.module.css
│   │   │   │   │   ├── ExecutiveBriefingPage.module.css.d.ts
│   │   │   │   │   ├── ExecutiveBriefingPage.tsx
│   │   │   │   │   ├── ForbiddenPage.module.css
│   │   │   │   │   ├── ForbiddenPage.module.css.d.ts
│   │   │   │   │   ├── ForbiddenPage.tsx
│   │   │   │   │   ├── GlobalSearch.module.css
│   │   │   │   │   ├── GlobalSearch.module.css.d.ts
│   │   │   │   │   ├── GlobalSearch.security.test.tsx
│   │   │   │   │   ├── GlobalSearch.tsx
│   │   │   │   │   ├── HomePage.module.css
│   │   │   │   │   ├── HomePage.module.css.d.ts
│   │   │   │   │   ├── HomePage.tsx
│   │   │   │   │   ├── IntakeApprovalsPage.module.css
│   │   │   │   │   ├── IntakeApprovalsPage.module.css.d.ts
│   │   │   │   │   ├── IntakeApprovalsPage.tsx
│   │   │   │   │   ├── IntakeFormPage.module.css
│   │   │   │   │   ├── IntakeFormPage.module.css.d.ts
│   │   │   │   │   ├── IntakeFormPage.test.tsx
│   │   │   │   │   ├── IntakeFormPage.tsx
│   │   │   │   │   ├── IntakeStatusPage.module.css
│   │   │   │   │   ├── IntakeStatusPage.module.css.d.ts
│   │   │   │   │   ├── IntakeStatusPage.tsx
│   │   │   │   │   ├── KnowledgeGraphPage.module.css
│   │   │   │   │   ├── KnowledgeGraphPage.module.css.d.ts
│   │   │   │   │   ├── KnowledgeGraphPage.tsx
│   │   │   │   │   ├── LessonsLearnedPage.module.css
│   │   │   │   │   ├── LessonsLearnedPage.module.css.d.ts
│   │   │   │   │   ├── LessonsLearnedPage.tsx
│   │   │   │   │   ├── LoginPage.module.css
│   │   │   │   │   ├── LoginPage.module.css.d.ts
│   │   │   │   │   ├── LoginPage.tsx
│   │   │   │   │   ├── MergeReviewPage.module.css
│   │   │   │   │   ├── MergeReviewPage.module.css.d.ts
│   │   │   │   │   ├── MergeReviewPage.tsx
│   │   │   │   │   ├── MethodologyEditor.module.css
│   │   │   │   │   ├── MethodologyEditor.module.css.d.ts
│   │   │   │   │   ├── MethodologyEditor.test.tsx
│   │   │   │   │   ├── MethodologyEditor.tsx
│   │   │   │   │   ├── NotificationCenterPage.module.css
│   │   │   │   │   ├── NotificationCenterPage.module.css.d.ts
│   │   │   │   │   ├── NotificationCenterPage.tsx
│   │   │   │   │   ├── OrganisationMethodologySettings.tsx
│   │   │   │   │   ├── PerformanceDashboardPage.module.css
│   │   │   │   │   ├── PerformanceDashboardPage.module.css.d.ts
│   │   │   │   │   ├── PerformanceDashboardPage.tsx
│   │   │   │   │   ├── PredictiveDashboardPage.module.css
│   │   │   │   │   ├── PredictiveDashboardPage.module.css.d.ts
│   │   │   │   │   ├── PredictiveDashboardPage.tsx
│   │   │   │   │   ├── ProjectConfigPage.tsx
│   │   │   │   │   ├── ProjectSetupWizardPage.module.css
│   │   │   │   │   ├── ProjectSetupWizardPage.module.css.d.ts
│   │   │   │   │   ├── ProjectSetupWizardPage.tsx
│   │   │   │   │   ├── PromptManager.module.css
│   │   │   │   │   ├── PromptManager.module.css.d.ts
│   │   │   │   │   ├── PromptManager.tsx
│   │   │   │   │   ├── RoleManager.module.css
│   │   │   │   │   ├── RoleManager.module.css.d.ts
│   │   │   │   │   ├── RoleManager.test.tsx
│   │   │   │   │   ├── RoleManager.tsx
│   │   │   │   │   ├── ScenarioAnalysisPage.tsx
│   │   │   │   │   ├── SecurityPostureDashboardPage.module.css
│   │   │   │   │   ├── SecurityPostureDashboardPage.module.css.d.ts
│   │   │   │   │   ├── SecurityPostureDashboardPage.tsx
│   │   │   │   │   ├── WorkflowDesigner.module.css
│   │   │   │   │   ├── WorkflowDesigner.module.css.d.ts
│   │   │   │   │   ├── WorkflowDesigner.test.tsx
│   │   │   │   │   ├── WorkflowDesigner.tsx
│   │   │   │   │   ├── WorkflowMonitoringPage.module.css
│   │   │   │   │   ├── WorkflowMonitoringPage.module.css.d.ts
│   │   │   │   │   ├── WorkflowMonitoringPage.tsx
│   │   │   │   │   ├── WorkspaceDirectoryPage.module.css
│   │   │   │   │   ├── WorkspaceDirectoryPage.module.css.d.ts
│   │   │   │   │   ├── WorkspaceDirectoryPage.tsx
│   │   │   │   │   ├── WorkspacePage.module.css
│   │   │   │   │   ├── WorkspacePage.module.css.d.ts
│   │   │   │   │   ├── WorkspacePage.test.tsx
│   │   │   │   │   ├── WorkspacePage.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── routing
│   │   │   │   │   ├── RouteGuards.test.tsx
│   │   │   │   │   └── RouteGuards.tsx
│   │   │   │   ├── services
│   │   │   │   │   ├── apiClient.ts
│   │   │   │   │   ├── knowledgeApi.ts
│   │   │   │   │   ├── scheduleApi.ts
│   │   │   │   │   └── searchApi.ts
│   │   │   │   ├── store
│   │   │   │   │   ├── agentConfig
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   ├── types.ts
│   │   │   │   │   │   ├── useAgentConfigStore.test.ts
│   │   │   │   │   │   └── useAgentConfigStore.ts
│   │   │   │   │   ├── assistant
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   ├── types.ts
│   │   │   │   │   │   ├── useAssistantStore.ts
│   │   │   │   │   │   └── useIntakeAssistantStore.ts
│   │   │   │   │   ├── connectors
│   │   │   │   │   │   ├── connectorConnectionSlice.ts
│   │   │   │   │   │   ├── connectorFilterSlice.ts
│   │   │   │   │   │   ├── connectorHelpers.ts
│   │   │   │   │   │   ├── connectorListSlice.ts
│   │   │   │   │   │   ├── connectorModalSlice.ts
│   │   │   │   │   │   ├── connectorStoreTypes.ts
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   ├── types.ts
│   │   │   │   │   │   ├── useConnectorStore.test.ts
│   │   │   │   │   │   └── useConnectorStore.ts
│   │   │   │   │   ├── copilot
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   └── useCopilotStore.ts
│   │   │   │   │   ├── documents
│   │   │   │   │   │   ├── coeditStore.ts
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── index.ts
│   │   │   │   │   ├── methodology
│   │   │   │   │   │   ├── demoData.ts
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   ├── types.ts
│   │   │   │   │   │   ├── useMethodologyStore.demo.test.ts
│   │   │   │   │   │   ├── useMethodologyStore.test.ts
│   │   │   │   │   │   └── useMethodologyStore.ts
│   │   │   │   │   ├── prompts
│   │   │   │   │   │   ├── defaultPrompts.ts
│   │   │   │   │   │   ├── index.ts
│   │   │   │   │   │   └── usePromptStore.ts
│   │   │   │   │   ├── realtime
│   │   │   │   │   │   └── useRealtimeStore.ts
│   │   │   │   │   ├── types.ts
│   │   │   │   │   ├── useAppStore.test.ts
│   │   │   │   │   ├── useAppStore.ts
│   │   │   │   │   ├── useCanvasStore.test.ts
│   │   │   │   │   └── useCanvasStore.ts
│   │   │   │   ├── styles
│   │   │   │   │   ├── index.css
│   │   │   │   │   └── tokens.css
│   │   │   │   ├── test
│   │   │   │   │   ├── accessibility.test.ts
│   │   │   │   │   ├── assistantResponses.test.ts
│   │   │   │   │   ├── prompts.test.ts
│   │   │   │   │   ├── searchApi.test.ts
│   │   │   │   │   ├── setup.ts
│   │   │   │   │   └── tokenContrast.test.ts
│   │   │   │   ├── types
│   │   │   │   │   ├── agentRuns.ts
│   │   │   │   │   ├── css-modules.d.ts
│   │   │   │   │   ├── css-modules.typecheck.ts
│   │   │   │   │   └── prompt.ts
│   │   │   │   ├── utils
│   │   │   │   │   ├── apiValidation.ts
│   │   │   │   │   ├── assistantResponses.ts
│   │   │   │   │   ├── prompts.ts
│   │   │   │   │   └── schema.ts
│   │   │   │   └── vite-env.d.ts
│   │   │   ├── tsconfig.css-modules.json
│   │   │   ├── tsconfig.json
│   │   │   ├── tsconfig.node.json
│   │   │   ├── vite.config.ts
│   │   │   └── vitest.config.ts
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── public
│   │   │   └── README.md
│   │   ├── requirements.txt
│   │   ├── scripts
│   │   │   ├── check_legacy_workspace_artifacts.py
│   │   │   ├── generate_metadata.py
│   │   │   └── legacy_workspace_guard_allowlist.txt
│   │   ├── src
│   │   │   ├── README.md
│   │   │   ├── agent_registry.py
│   │   │   ├── agent_settings_models.py
│   │   │   ├── agent_settings_store.py
│   │   │   ├── analytics_proxy.py
│   │   │   ├── bootstrap.py
│   │   │   ├── canonical_template_registry.py
│   │   │   ├── config.py
│   │   │   ├── connector_hub_proxy.py
│   │   │   ├── data_service_proxy.py
│   │   │   ├── demo_integrations.py
│   │   │   ├── demo_seed.py
│   │   │   ├── dependencies.py
│   │   │   ├── document_proxy.py
│   │   │   ├── gating.py
│   │   │   ├── intake_models.py
│   │   │   ├── intake_store.py
│   │   │   ├── knowledge_store.py
│   │   │   ├── legacy_main.py
│   │   │   ├── lineage_proxy.py
│   │   │   ├── llm_preferences_store.py
│   │   │   ├── main.py
│   │   │   ├── merge_review_models.py
│   │   │   ├── merge_review_store.py
│   │   │   ├── methodologies.py
│   │   │   ├── methodology_node_runtime.py
│   │   │   ├── middleware.py
│   │   │   ├── oidc_client.py
│   │   │   ├── orchestrator_proxy.py
│   │   │   ├── pipeline_models.py
│   │   │   ├── pipeline_store.py
│   │   │   ├── routes
│   │   │   │   ├── __init__.py
│   │   │   │   ├── _deps.py
│   │   │   │   ├── _llm_helpers.py
│   │   │   │   ├── _models.py
│   │   │   │   ├── agent_runs.py
│   │   │   │   ├── agents.py
│   │   │   │   ├── analytics.py
│   │   │   │   ├── assistant.py
│   │   │   │   ├── assistant_api.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── briefings.py
│   │   │   │   ├── capacity.py
│   │   │   │   ├── connectors.py
│   │   │   │   ├── copilot_stream.py
│   │   │   │   ├── dashboards.py
│   │   │   │   ├── document_canvas.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── enterprise.py
│   │   │   │   ├── health.py
│   │   │   │   ├── intake.py
│   │   │   │   ├── intake_intelligence.py
│   │   │   │   ├── knowledge.py
│   │   │   │   ├── knowledge_graph.py
│   │   │   │   ├── legacy_pages.py
│   │   │   │   ├── llm.py
│   │   │   │   ├── methodology.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── project_setup.py
│   │   │   │   ├── roles.py
│   │   │   │   ├── scenarios.py
│   │   │   │   ├── search.py
│   │   │   │   ├── security_posture.py
│   │   │   │   ├── spreadsheets.py
│   │   │   │   ├── templates_api.py
│   │   │   │   ├── timeline.py
│   │   │   │   ├── tree.py
│   │   │   │   ├── wbs_schedule.py
│   │   │   │   ├── workflow.py
│   │   │   │   ├── workflows_api.py
│   │   │   │   ├── workspace.py
│   │   │   │   └── workspace_state.py
│   │   │   ├── runtime_lifecycle_store.py
│   │   │   ├── search_service.py
│   │   │   ├── spreadsheet_models.py
│   │   │   ├── spreadsheet_store.py
│   │   │   ├── template_mappings.py
│   │   │   ├── template_models.py
│   │   │   ├── template_registry.py
│   │   │   ├── timeline_models.py
│   │   │   ├── timeline_store.py
│   │   │   ├── tree_models.py
│   │   │   ├── tree_store.py
│   │   │   ├── web_services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analytics.py
│   │   │   │   ├── assistant.py
│   │   │   │   ├── connectors.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── workflow.py
│   │   │   │   └── workspace.py
│   │   │   ├── workflow_models.py
│   │   │   ├── workflow_store.py
│   │   │   ├── workspace_state.py
│   │   │   └── workspace_state_store.py
│   │   ├── static
│   │   │   ├── index.html
│   │   │   └── styles.css
│   │   ├── storage
│   │   │   ├── agile_backlog.json
│   │   │   ├── agile_metrics.json
│   │   │   ├── agile_pi.json
│   │   │   ├── alerts.json
│   │   │   ├── automations.json
│   │   │   ├── board_configs.json
│   │   │   ├── capacity.json
│   │   │   ├── comments.json
│   │   │   ├── demand.json
│   │   │   ├── finance_actuals.json
│   │   │   ├── finance_budget.json
│   │   │   ├── finance_change_requests.json
│   │   │   ├── finance_forecast.json
│   │   │   ├── llm_preferences.json
│   │   │   ├── merge_review_cases.json
│   │   │   ├── notifications.json
│   │   │   ├── packs.json
│   │   │   ├── prioritisation.json
│   │   │   ├── roles.json
│   │   │   ├── scenarios.json
│   │   │   └── sync_center.json
│   │   └── tests
│   │       ├── README.md
│   │       ├── test_agent_gallery.py
│   │       ├── test_architecture_guards.py
│   │       ├── test_assistant_panel.py
│   │       ├── test_assistant_suggestions.py
│   │       ├── test_connector_gallery_proxy.py
│   │       ├── test_dashboard_canvas_proxy.py
│   │       ├── test_dashboard_canvas_rendering.py
│   │       ├── test_demo_auto_auth.py
│   │       ├── test_demo_mode.py
│   │       ├── test_demo_seed_startup.py
│   │       ├── test_document_canvas_proxy.py
│   │       ├── test_enterprise_uplift_api.py
│   │       ├── test_intake_assistant_api.py
│   │       ├── test_llm_preferences_api.py
│   │       ├── test_methodology_config_validation.py
│   │       ├── test_methodology_gating.py
│   │       ├── test_methodology_node_runtime.py
│   │       ├── test_oidc_login_flow.py
│   │       ├── test_orchestrator_proxy.py
│   │       ├── test_portfolio_lifecycle_endpoints.py
│   │       ├── test_program_views_api.py
│   │       ├── test_program_views_canvas.py
│   │       ├── test_router_contract_analytics.py
│   │       ├── test_router_contract_assistant.py
│   │       ├── test_router_contract_connectors.py
│   │       ├── test_router_contract_documents.py
│   │       ├── test_router_contract_workflow.py
│   │       ├── test_router_contract_workspace.py
│   │       ├── test_search_assistant_api.py
│   │       ├── test_spreadsheet_canvas.py
│   │       ├── test_template_gallery.py
│   │       ├── test_template_mappings.py
│   │       ├── test_template_models.py
│   │       ├── test_timeline_canvas.py
│   │       ├── test_tree_canvas.py
│   │       ├── test_wbs_schedule_api.py
│   │       ├── test_wbs_timeline_canvas.py
│   │       ├── test_workspace_shell.py
│   │       └── test_workspace_state_api.py
│   └── workflow-service
│       ├── .dockerignore
│       ├── Dockerfile
│       ├── README.md
│       ├── helm
│       │   ├── Chart.yaml
│       │   ├── README.md
│       │   ├── templates
│       │   │   ├── _helpers.tpl
│       │   │   ├── broker-rabbitmq.yaml
│       │   │   ├── broker-redis.yaml
│       │   │   ├── celery-worker-deployment.yaml
│       │   │   ├── certificate.yaml
│       │   │   ├── configmap.yaml
│       │   │   ├── deployment.yaml
│       │   │   ├── hpa.yaml
│       │   │   ├── ingress.yaml
│       │   │   ├── pdb.yaml
│       │   │   └── service.yaml
│       │   └── values.yaml
│       ├── migrations
│       │   ├── README.md
│       │   └── sql
│       │       ├── 001_init_postgresql.sql
│       │       └── 001_init_sqlite.sql
│       ├── requirements.txt
│       ├── src
│       │   ├── agent_client.py
│       │   ├── circuit_breaker.py
│       │   ├── config.py
│       │   ├── main.py
│       │   ├── nl_workflow.py
│       │   ├── nl_workflow_routes.py
│       │   ├── workflow_audit.py
│       │   ├── workflow_definitions.py
│       │   ├── workflow_runtime.py
│       │   └── workflow_storage.py
│       ├── storage
│       │   └── workflows.db
│       ├── tests
│       │   ├── README.md
│       │   ├── test_storage_policy.py
│       │   └── test_workflow_storage_concurrency.py
│       ├── workflow_registry.py
│       └── workflows
│           ├── README.md
│           ├── definitions
│           │   ├── change-request.workflow.yaml
│           │   ├── deployment-rollback.workflow.yaml
│           │   ├── intake-triage.workflow.yaml
│           │   ├── project-initiation.workflow.yaml
│           │   ├── publish-charter.workflow.yaml
│           │   ├── quality-audit.workflow.yaml
│           │   └── risk-mitigation.workflow.yaml
│           └── schema
│               └── workflow.schema.json
├── config
│   ├── abac
│   │   ├── policies.yaml
│   │   └── rules.yaml
│   └── rbac
│       ├── field-level.yaml
│       ├── permissions.yaml
│       └── roles.yaml
├── connectors
│   ├── README.md
│   ├── __init__.py
│   ├── adp
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── adp_connector.py
│   │   │   ├── main.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── archer
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── archer_connector.py
│   │   │   ├── main.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── asana
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── asana_connector.py
│   │   │   ├── main.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── asana_mcp
│   │   └── manifest.yaml
│   ├── azure_communication_services
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── azure_communication_services_connector.py
│   │   │   ├── main.py
│   │   │   ├── router.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       └── test_contract.py
│   ├── azure_devops
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   ├── project.yaml
│   │   │   └── work-item.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── azure_devops_connector.py
│   │   │   ├── main.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       └── test_contract.py
│   ├── clarity
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── clarity_connector.py
│   │   │   ├── main.py
│   │   │   ├── mappers.py
│   │   │   ├── router.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_clarity_connector.py
│   │       ├── test_clarity_mcp.py
│   │       ├── test_clarity_runtime.py
│   │       ├── test_contract.py
│   │       ├── test_mappers.py
│   │       └── test_outbound_sync.py
│   ├── clarity_mcp
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── confluence
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── confluence_connector.py
│   │   │   ├── main.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── conftest.py
│   ├── google_calendar
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── google_calendar_connector.py
│   │   │   ├── main.py
│   │   │   ├── router.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       └── test_contract.py
│   ├── google_drive
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── google_drive_connector.py
│   │   │   ├── main.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── integration
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── framework.py
│   │   └── mcp_connectors.py
│   ├── iot
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── project.yaml
│   │   │   └── sensor-data.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── iot_connector.py
│   │   │   └── main.py
│   │   └── tests
│   │       ├── test_contract.py
│   │       └── test_iot_connector.py
│   ├── jira
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   ├── project.yaml
│   │   │   └── work-item.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── jira_connector.py
│   │   │   ├── main.py
│   │   │   ├── mappers.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── conftest.py
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_contract.py
│   │       ├── test_jira_connector.py
│   │       └── test_jira_mcp.py
│   ├── jira_mcp
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── project.yaml
│   │   │   └── work-item.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── logicgate
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── logicgate_connector.py
│   │   │   ├── main.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── m365
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── project.yaml
│   │   │   └── resource.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── m365_connector.py
│   │   │   └── main.py
│   │   ├── tests
│   │   │   └── test_contract.py
│   │   └── tool_map.yaml
│   ├── mcp_client
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── client.py
│   │   ├── errors.py
│   │   └── models.py
│   ├── mock
│   │   ├── __init__.py
│   │   ├── azure_devops
│   │   │   └── manifest.yaml
│   │   ├── clarity
│   │   │   └── manifest.yaml
│   │   ├── jira
│   │   │   └── manifest.yaml
│   │   ├── mock_connectors.py
│   │   ├── planview
│   │   │   └── manifest.yaml
│   │   ├── sap
│   │   │   └── manifest.yaml
│   │   ├── servicenow
│   │   │   └── manifest.yaml
│   │   ├── teams
│   │   │   └── manifest.yaml
│   │   └── workday
│   │       └── manifest.yaml
│   ├── monday
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── monday_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── ms_project_server
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── ms_project_server_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── netsuite
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── netsuite_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── notification_hubs
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── notification_hubs_connector.py
│   │   │   ├── router.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       └── test_contract.py
│   ├── oracle
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── oracle_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── outlook
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── outlook_connector.py
│   │   │   ├── router.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       └── test_contract.py
│   ├── planview
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── mappers.py
│   │   │   ├── planview_connector.py
│   │   │   ├── router.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── conftest.py
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_contract.py
│   │       ├── test_mappers.py
│   │       ├── test_outbound_sync.py
│   │       ├── test_planview_connector.py
│   │       ├── test_planview_mcp.py
│   │       └── test_planview_runtime.py
│   ├── planview_mcp
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── registry
│   │   ├── README.md
│   │   ├── connectors.json
│   │   ├── generate.py
│   │   ├── schemas
│   │   │   ├── auth-config.schema.json
│   │   │   ├── capabilities.schema.json
│   │   │   ├── connector-manifest.schema.json
│   │   │   └── connector-mapping.schema.json
│   │   └── signing
│   │       ├── README.md
│   │       ├── public-keys
│   │       │   └── README.md
│   │       └── signing-policy.md
│   ├── regulatory_compliance
│   │   ├── Dockerfile
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── audit_trail.yaml
│   │   │   ├── compliance_event.yaml
│   │   │   └── finding.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── regulatory_compliance_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── conftest.py
│   │       └── test_regulatory_compliance_connector.py
│   ├── salesforce
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── router.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_contract.py
│   │       └── test_router.py
│   ├── sap
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── mappers.py
│   │   │   ├── router.py
│   │   │   ├── sap_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_contract.py
│   │       ├── test_mappers.py
│   │       ├── test_outbound_sync.py
│   │       └── test_sap_mcp.py
│   ├── sap_mcp
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── project.yaml
│   │   │   └── purchase-order.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── sap_successfactors
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── sap_successfactors_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── sdk
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── connector_maturity_inventory.py
│   │   ├── connector_migration_tracker.md
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── base_connector.py
│   │   │   ├── classification.py
│   │   │   ├── clients
│   │   │   │   ├── erp_client.py
│   │   │   │   ├── hris_client.py
│   │   │   │   └── ppm_client.py
│   │   │   ├── connector_registry.py
│   │   │   ├── connector_secrets.py
│   │   │   ├── data_service_client.py
│   │   │   ├── http_client.py
│   │   │   ├── iot_connector.py
│   │   │   ├── mcp_client.py
│   │   │   ├── operation_router.py
│   │   │   ├── project_connector_store.py
│   │   │   ├── quality.py
│   │   │   ├── regulatory_compliance_connector.py
│   │   │   ├── rest_connector.py
│   │   │   ├── runtime.py
│   │   │   ├── sync_controls.py
│   │   │   ├── sync_router.py
│   │   │   ├── telemetry.py
│   │   │   └── transformations.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── fixtures
│   │       │   └── connector_contract_fixture.json
│   │       ├── test_auth.py
│   │       ├── test_connector_contract_harness.py
│   │       ├── test_connector_runtime.py
│   │       ├── test_http_client.py
│   │       ├── test_mcp_client.py
│   │       ├── test_mcp_project_config.py
│   │       └── test_rest_connector_docs.py
│   ├── servicenow
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── router.py
│   │   │   ├── servicenow_grc_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_contract.py
│   │       └── test_router.py
│   ├── sharepoint
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── sharepoint_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       └── test_contract.py
│   ├── slack
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   ├── project.yaml
│   │   │   └── resource.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── mappers.py
│   │   │   ├── router.py
│   │   │   ├── slack_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── conftest.py
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_contract.py
│   │       └── test_slack_mcp.py
│   ├── slack_mcp
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── project.yaml
│   │   │   └── resource.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── smartsheet
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── router.py
│   │   │   ├── smartsheet_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       └── test_contract.py
│   ├── teams
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── mappers.py
│   │   │   ├── router.py
│   │   │   ├── teams_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_contract.py
│   │       └── test_teams_mcp.py
│   ├── teams_mcp
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── project.yaml
│   │   │   └── resource.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── test_contract.py
│   ├── twilio
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   └── project.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── router.py
│   │   │   ├── twilio_connector.py
│   │   │   └── webhooks.py
│   │   └── tests
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       └── test_contract.py
│   ├── workday
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── README.md
│   │   │   ├── project.yaml
│   │   │   └── resource.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── mappers.py
│   │   │   ├── router.py
│   │   │   ├── webhooks.py
│   │   │   └── workday_connector.py
│   │   └── tests
│   │       ├── README.md
│   │       ├── fixtures
│   │       │   └── projects.json
│   │       ├── test_contract.py
│   │       ├── test_router.py
│   │       └── test_workday_mcp.py
│   ├── workday_mcp
│   │   ├── manifest.yaml
│   │   ├── mappings
│   │   │   ├── project.yaml
│   │   │   └── resource.yaml
│   │   ├── src
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── test_contract.py
│   └── zoom
│       ├── README.md
│       ├── manifest.yaml
│       ├── mappings
│       │   └── project.yaml
│       ├── src
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── webhooks.py
│       │   └── zoom_connector.py
│       └── tests
│           └── test_contract.py
├── constraints
│   └── py313.txt
├── data
│   ├── README.md
│   ├── __init__.py
│   ├── alerts.json
│   ├── analytics_alerts.json
│   ├── analytics_events.json
│   ├── analytics_kpi_history.json
│   ├── analytics_lineage.json
│   ├── analytics_outputs.json
│   ├── approval_notification_store.json
│   ├── approval_store.json
│   ├── audit
│   │   └── audit_logs.db
│   ├── business_case_store.json
│   ├── change_requests.json
│   ├── cmdb.json
│   ├── compliance_evidence.json
│   ├── demand_intake_store.json
│   ├── demo
│   │   ├── approvals.json
│   │   ├── budgets.json
│   │   ├── contracts.json
│   │   ├── demo_run_log.json
│   │   ├── epics.json
│   │   ├── issues.json
│   │   ├── notifications.json
│   │   ├── policies.json
│   │   ├── portfolios.json
│   │   ├── programs.json
│   │   ├── projects.json
│   │   ├── resources.json
│   │   ├── risks.json
│   │   ├── sprints.json
│   │   ├── tasks.json
│   │   └── vendors.json
│   ├── deployment_plans.json
│   ├── financial_actuals.json
│   ├── financial_budgets.json
│   ├── financial_forecasts.json
│   ├── fixtures
│   │   ├── exchange_rates.json
│   │   └── tax_rates.json
│   ├── health_snapshots.json
│   ├── improvement_backlog.json
│   ├── improvement_history.json
│   ├── incidents.json
│   ├── knowledge_documents.json
│   ├── knowledge_management.db
│   ├── lineage
│   │   ├── README.md
│   │   ├── example-lineage.json
│   │   └── sync_lineage.json
│   ├── master_records.json
│   ├── migrations
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── env.py
│   │   ├── models.py
│   │   ├── validate_registry_consistency.py
│   │   └── versions
│   │       ├── 0001_create_core_tables.py
│   │       ├── 0002_create_orchestration_states.py
│   │       ├── 0003_create_missing_tables.py
│   │       ├── 0004_add_enum_constraints.py
│   │       ├── 0005_create_workflow_engine_tables.py
│   │       ├── 0006_add_integration_config_tables.py
│   │       ├── 0007_add_idempotency_key_to_workflow_instances.py
│   │       ├── 0008_add_entities_schema_version_index.py
│   │       ├── 0009_create_schema_registry_tables.py
│   │       ├── 0010_add_structured_skills_taxonomy.py
│   │       └── 0011_add_methodology_definitions.py
│   ├── portfolio_strategy_store.json
│   ├── process_conformance.json
│   ├── process_event_logs.json
│   ├── process_models.json
│   ├── process_recommendations.json
│   ├── program_dependency_store.json
│   ├── program_roadmap_store.json
│   ├── program_store.json
│   ├── project_charters.json
│   ├── project_health_history.json
│   ├── project_lifecycle.json
│   ├── project_schedules.json
│   ├── project_wbs.json
│   ├── quality
│   │   ├── README.md
│   │   └── rules.yaml
│   ├── quality_audits.json
│   ├── quality_coverage_trends.json
│   ├── quality_defects.json
│   ├── quality_plans.json
│   ├── quality_requirement_links.json
│   ├── quality_test_cases.json
│   ├── release_calendar.json
│   ├── resource_allocations.json
│   ├── resource_calendars.json
│   ├── resource_pool.json
│   ├── risk_register.json
│   ├── rollback_scripts
│   │   └── rollback_DEPLOY-TEST.sh
│   ├── schedule_baselines.json
│   ├── schema_registry.json
│   ├── schemas
│   │   ├── README.md
│   │   ├── agent-manifest.schema.json
│   │   ├── agent-run.schema.json
│   │   ├── agent_config.schema.json
│   │   ├── audit-event.schema.json
│   │   ├── budget.schema.json
│   │   ├── demand.schema.json
│   │   ├── document.schema.json
│   │   ├── examples
│   │   │   ├── agent_config.json
│   │   │   ├── audit-event.json
│   │   │   ├── budget.json
│   │   │   ├── demand.json
│   │   │   ├── document.json
│   │   │   ├── issue.json
│   │   │   ├── portfolio.json
│   │   │   ├── program.json
│   │   │   ├── project.json
│   │   │   ├── resource.json
│   │   │   ├── risk.json
│   │   │   ├── roi.json
│   │   │   ├── vendor.json
│   │   │   └── work-item.json
│   │   ├── issue.schema.json
│   │   ├── methodology.schema.json
│   │   ├── portfolio.schema.json
│   │   ├── program.schema.json
│   │   ├── project.schema.json
│   │   ├── resource.schema.json
│   │   ├── risk.schema.json
│   │   ├── roi.schema.json
│   │   ├── scenario.schema.json
│   │   ├── vendor.schema.json
│   │   └── work-item.schema.json
│   ├── scope_baselines.db
│   ├── scope_baselines.json
│   ├── seed
│   │   └── manifest.csv
│   ├── stakeholder_comms.db
│   ├── stakeholders.json
│   ├── sync_audit_events.json
│   ├── sync_events.json
│   ├── sync_retry_queue.json
│   ├── sync_state.json
│   ├── vendor_contracts.json
│   ├── vendor_invoices.json
│   ├── vendor_performance.json
│   ├── vendor_procurement_events.json
│   ├── vendors.json
│   ├── workflow_events.json
│   ├── workflow_instances.json
│   ├── workflow_subscriptions.json
│   ├── workflow_tasks.json
│   └── workflows.json
├── docs
│   ├── CHANGELOG.md
│   ├── README.md
│   ├── REPO_STRUCTURE.md
│   ├── UI.md
│   ├── agents.md
│   ├── api
│   │   ├── README.md
│   │   ├── analytics-openapi.yaml
│   │   ├── connector-hub-openapi.yaml
│   │   ├── document-openapi.yaml
│   │   ├── graphql-schema.graphql
│   │   ├── openapi.yaml
│   │   └── orchestration-openapi.yaml
│   ├── architecture
│   │   ├── README.md
│   │   ├── adr
│   │   │   ├── 0000-adr-template.md
│   │   │   ├── 0001-record-architecture.md
│   │   │   ├── 0002-llm-provider-abstraction.md
│   │   │   ├── 0003-eventing-and-message-bus.md
│   │   │   ├── 0004-workflow-service-selection.md
│   │   │   ├── 0005-rbac-abac-field-level-security.md
│   │   │   ├── 0006-data-lineage-and-audit.md
│   │   │   ├── 0007-connector-certification.md
│   │   │   ├── 0008-prompt-management-and-versioning.md
│   │   │   ├── 0009-multi-tenancy-strategy.md
│   │   │   └── 0010-secrets-management.md
│   │   ├── diagrams
│   │   │   ├── c4-component.puml
│   │   │   ├── c4-container.puml
│   │   │   ├── c4-context.puml
│   │   │   ├── data-lineage.puml
│   │   │   ├── deployment-overview.puml
│   │   │   ├── seq-connector-sync.puml
│   │   │   ├── seq-intent-routing.puml
│   │   │   ├── seq-stage-gate-enforcement.puml
│   │   │   ├── service-topology.puml
│   │   │   └── threat-model-flow.puml
│   │   ├── grafana
│   │   │   ├── cost_dashboard.json
│   │   │   └── multi_agent_tracing.json
│   │   └── images
│   │       ├── grafana-ppm-platform.svg
│   │       └── grafana-ppm-slo.svg
│   ├── assets
│   │   └── ui
│   │       └── screenshots
│   │           └── README.md
│   ├── change-management.md
│   ├── compliance.md
│   ├── connectors
│   │   ├── README.md
│   │   └── generated
│   │       ├── capability-matrix.md
│   │       └── maturity-inventory.json
│   ├── data.md
│   ├── demo-environment.md
│   ├── dependency-management.md
│   ├── design-system.md
│   ├── dr-runbook.md
│   ├── frontend-spa-migration.md
│   ├── generated
│   │   └── services
│   │       ├── README.md
│   │       ├── agent-config.md
│   │       ├── agent-runtime.md
│   │       ├── audit-log.md
│   │       ├── auth-service.md
│   │       ├── data-lineage-service.md
│   │       ├── data-service.md
│   │       ├── data-sync-service.md
│   │       ├── identity-access.md
│   │       ├── memory-service.md
│   │       ├── notification-service.md
│   │       ├── policy-engine.md
│   │       ├── realtime-coedit-service.md
│   │       └── telemetry-service.md
│   ├── merge-conflict-troubleshooting.md
│   ├── methodology
│   │   ├── README.md
│   │   ├── adaptive
│   │   │   ├── README.md
│   │   │   ├── gates.yaml
│   │   │   └── map.yaml
│   │   ├── customisation-guide.md
│   │   ├── hybrid
│   │   │   ├── README.md
│   │   │   ├── gates.yaml
│   │   │   └── map.yaml
│   │   └── predictive
│   │       ├── README.md
│   │       ├── gates.yaml
│   │       └── map.yaml
│   ├── onboarding
│   │   └── developer-onboarding.md
│   ├── outbound_dependency_inventory.md
│   ├── platform-commercials.md
│   ├── platform-description.md
│   ├── platform-userguide.md
│   ├── production-readiness
│   │   ├── README.md
│   │   └── maturity-scorecards
│   │       ├── README.md
│   │       └── latest.md
│   ├── react-native-typescript-alignment.md
│   ├── root-file-policy.md
│   ├── runbooks
│   │   ├── backup-recovery.md
│   │   ├── credential-acquisition.md
│   │   ├── deployment.md
│   │   ├── disaster-recovery.md
│   │   ├── monitoring-dashboards.md
│   │   ├── schema-promotion-rollback.md
│   │   ├── secret-init.md
│   │   ├── secret-rotation.md
│   │   └── troubleshooting.md
│   ├── runbooks.md
│   ├── schema-compatibility-matrix.md
│   ├── solution-index.md
│   ├── templates
│   │   ├── CHANGELOG.md
│   │   ├── Executive-Report-Templates.md
│   │   ├── README.md
│   │   ├── advanced-business-case-template.md
│   │   ├── agile-ceremonies-templates.md
│   │   ├── agile-release-plan-template.md
│   │   ├── agile-risk-board-template.md
│   │   ├── agile-scrum-framework.md
│   │   ├── agile-stakeholder-map-template.md
│   │   ├── agile-team-charter-template.md
│   │   ├── ai-implementation-status.md
│   │   ├── api_documentation_template.md
│   │   ├── architecture_decision_record.md
│   │   ├── art_coordination_template.md
│   │   ├── backlog-management-template.md
│   │   ├── backlog-refinement-template.md
│   │   ├── batch_record_template.md
│   │   ├── budget-dashboard-template.md
│   │   ├── budget-template.md
│   │   ├── business-case.md
│   │   ├── business-continuity-disaster-recovery-plan.md
│   │   ├── business_case_template.md
│   │   ├── business_requirements_document_template.md
│   │   ├── capacity-planning-worksheet.md
│   │   ├── change-management-plan.md
│   │   ├── change-request.md
│   │   ├── change_management_plan_template.md
│   │   ├── change_request_template.md
│   │   ├── ci-cd-pipeline-definition.md
│   │   ├── cicd_pipeline_planning_template.md
│   │   ├── cleaning_validation_protocol_template.md
│   │   ├── clinical-trial-project-charter.md
│   │   ├── clinical_trial_protocol_template.md
│   │   ├── closure-checklist.md
│   │   ├── communication-plan.md
│   │   ├── compliance-management-template.md
│   │   ├── compliance-risk-assessment.md
│   │   ├── compliance_risk_assessment_template.md
│   │   ├── components
│   │   │   ├── assumptions.yaml
│   │   │   ├── benefits.yaml
│   │   │   ├── controls.yaml
│   │   │   ├── core-communication-plan--data-table.yaml
│   │   │   ├── core-deployment-checklist--deployment.yaml
│   │   │   ├── core-deployment-checklist--post-deployment.yaml
│   │   │   ├── core-deployment-checklist--pre-deployment.yaml
│   │   │   ├── core-executive-dashboard--budget-performance.yaml
│   │   │   ├── core-executive-dashboard--decisions-required.yaml
│   │   │   ├── core-executive-dashboard--portfolio-health.yaml
│   │   │   ├── core-executive-dashboard--schedule-performance.yaml
│   │   │   ├── core-product-backlog--data-table.yaml
│   │   │   ├── core-project-charter--budget-summary.yaml
│   │   │   ├── core-project-charter--governance.yaml
│   │   │   ├── core-project-charter--objectives.yaml
│   │   │   ├── core-project-charter--problem-statement.yaml
│   │   │   ├── core-project-charter--scope.yaml
│   │   │   ├── core-project-charter--success-criteria.yaml
│   │   │   ├── core-project-management-plan--cost-baseline.yaml
│   │   │   ├── core-project-management-plan--management-approach.yaml
│   │   │   ├── core-project-management-plan--project-overview.yaml
│   │   │   ├── core-project-management-plan--schedule-baseline.yaml
│   │   │   ├── core-project-management-plan--scope-baseline.yaml
│   │   │   ├── core-project-management-plan--stakeholder-engagement.yaml
│   │   │   ├── core-requirements--acceptance-criteria.yaml
│   │   │   ├── core-requirements--business-requirements.yaml
│   │   │   ├── core-requirements--constraints.yaml
│   │   │   ├── core-requirements--functional-requirements.yaml
│   │   │   ├── core-requirements--non-functional-requirements.yaml
│   │   │   ├── core-requirements--traceability.yaml
│   │   │   ├── core-risk-register--data-table.yaml
│   │   │   ├── core-sprint-planning--candidate-work.yaml
│   │   │   ├── core-sprint-planning--capacity.yaml
│   │   │   ├── core-sprint-planning--commitment.yaml
│   │   │   ├── core-sprint-planning--dependencies.yaml
│   │   │   ├── core-sprint-planning--sprint-goal.yaml
│   │   │   ├── core-sprint-retrospective--experiments.yaml
│   │   │   ├── core-sprint-retrospective--owners-and-dates.yaml
│   │   │   ├── core-sprint-retrospective--root-causes.yaml
│   │   │   ├── core-sprint-retrospective--what-did-not-go-well.yaml
│   │   │   ├── core-sprint-retrospective--what-went-well.yaml
│   │   │   ├── core-sprint-review--backlog-adjustments.yaml
│   │   │   ├── core-sprint-review--completed-increment.yaml
│   │   │   ├── core-sprint-review--rejected-or-carried-over-items.yaml
│   │   │   ├── core-sprint-review--sprint-goal-outcome.yaml
│   │   │   ├── core-sprint-review--stakeholder-feedback.yaml
│   │   │   ├── core-status-report--budget-status.yaml
│   │   │   ├── core-status-report--decisions-needed.yaml
│   │   │   ├── core-status-report--next-period-plan.yaml
│   │   │   ├── core-status-report--overall-health-rag.yaml
│   │   │   ├── core-status-report--progress-vs-plan.yaml
│   │   │   ├── core-status-report--reporting-period.yaml
│   │   │   ├── core-status-report--summary.yaml
│   │   │   ├── milestones.yaml
│   │   │   └── risks.yaml
│   │   ├── computer_system_validation_protocol_template.md
│   │   ├── configuration-management-plan.md
│   │   ├── construction-pm-templates.md
│   │   ├── construction-project-charter.md
│   │   ├── construction-risk-register.md
│   │   ├── construction-wbs.md
│   │   ├── core
│   │   │   ├── communication-plan
│   │   │   │   └── manifest.yaml
│   │   │   ├── deployment-checklist
│   │   │   │   └── manifest.yaml
│   │   │   ├── executive-dashboard
│   │   │   │   └── manifest.yaml
│   │   │   ├── product-backlog
│   │   │   │   └── manifest.yaml
│   │   │   ├── project-charter
│   │   │   │   └── manifest.yaml
│   │   │   ├── project-management-plan
│   │   │   │   └── manifest.yaml
│   │   │   ├── requirements
│   │   │   │   └── manifest.yaml
│   │   │   ├── risk-register
│   │   │   │   └── manifest.yaml
│   │   │   ├── sprint-planning
│   │   │   │   └── manifest.yaml
│   │   │   ├── sprint-retrospective
│   │   │   │   └── manifest.yaml
│   │   │   ├── sprint-review
│   │   │   │   └── manifest.yaml
│   │   │   └── status-report
│   │   │       └── manifest.yaml
│   │   ├── cross_team_coordination_template.md
│   │   ├── current-state-analysis-template.md
│   │   ├── cybersecurity-training-plan.md
│   │   ├── cybersecurity_assessment_template.md
│   │   ├── daily-standup-template.md
│   │   ├── data-quality-framework.md
│   │   ├── data_center_design_template.md
│   │   ├── decision-authority.md
│   │   ├── decision-framework.md
│   │   ├── decision-log.md
│   │   ├── deployment-checklist.md
│   │   ├── devsecops_template.md
│   │   ├── digital-kpi-dashboard.md
│   │   ├── digital-maturity-assessment.md
│   │   ├── digital_transformation_strategy_template.md
│   │   ├── disaster_recovery_template.md
│   │   ├── enterprise-risk-assessment-template.md
│   │   ├── enterprise-stakeholder-analysis-template.md
│   │   ├── equipment_qualification_protocol_template.md
│   │   ├── escalation-matrix.md
│   │   ├── evm-dashboard-template.md
│   │   ├── executive-communication-automation.md
│   │   ├── executive-dashboard-slides.md
│   │   ├── executive-dashboard-workbook.md
│   │   ├── executive-dashboard.md
│   │   ├── executive-status-report.md
│   │   ├── executive-summary-template.md
│   │   ├── extensions
│   │   │   ├── agile
│   │   │   │   ├── product-backlog.patch.yaml
│   │   │   │   ├── project-charter.patch.yaml
│   │   │   │   ├── risk-register.patch.yaml
│   │   │   │   ├── sprint-planning.patch.yaml
│   │   │   │   ├── sprint-retrospective.patch.yaml
│   │   │   │   ├── sprint-review.patch.yaml
│   │   │   │   └── status-report.patch.yaml
│   │   │   ├── compliance
│   │   │   │   └── privacy
│   │   │   │       └── project-charter.patch.yaml
│   │   │   ├── devops
│   │   │   │   └── deployment-checklist.patch.yaml
│   │   │   ├── hybrid
│   │   │   │   ├── project-charter.patch.yaml
│   │   │   │   ├── project-management-plan.patch.yaml
│   │   │   │   ├── risk-register.patch.yaml
│   │   │   │   └── status-report.patch.yaml
│   │   │   ├── safe
│   │   │   │   ├── executive-dashboard.patch.yaml
│   │   │   │   ├── product-backlog.patch.yaml
│   │   │   │   ├── risk-register.patch.yaml
│   │   │   │   ├── sprint-planning.patch.yaml
│   │   │   │   └── status-report.patch.yaml
│   │   │   └── waterfall
│   │   │       ├── project-charter.patch.yaml
│   │   │       ├── project-management-plan.patch.yaml
│   │   │       ├── requirements.patch.yaml
│   │   │       └── status-report.patch.yaml
│   │   ├── final-report.md
│   │   ├── financial-forecasting-models.md
│   │   ├── financial-services-pm-templates.md
│   │   ├── financial_services_project_charter.md
│   │   ├── future-state-blueprint-template.md
│   │   ├── gap-analysis-matrix-template.md
│   │   ├── github-projects-integration-toolkit.md
│   │   ├── governance-assessment-template.md
│   │   ├── governance-charter.md
│   │   ├── governance-framework.md
│   │   ├── governance-roles.md
│   │   ├── guides
│   │   │   ├── agent-generation-patterns.md
│   │   │   └── tailoring-playbook.md
│   │   ├── gxp-compliance-checklist.md
│   │   ├── gxp_training_plan_template.md
│   │   ├── handover-template.md
│   │   ├── health-pharma-pm-templates.md
│   │   ├── health_authority_communication_plan_template.md
│   │   ├── healthcare-risk-register.md
│   │   ├── hybrid-infrastructure-template.md
│   │   ├── hybrid-pm-templates--tools.md
│   │   ├── hybrid-project-management-plan-template.md
│   │   ├── hybrid_project_charter_template.md
│   │   ├── hybrid_quality_management_template.md
│   │   ├── hybrid_release_planning_template.md
│   │   ├── hybrid_team_management_template.md
│   │   ├── incident-response-plan.md
│   │   ├── incident_response_template.md
│   │   ├── index.json
│   │   ├── infrastructure-change-management-protocol.md
│   │   ├── infrastructure-requirements-template.md
│   │   ├── infrastructure_as_code_template.md
│   │   ├── infrastructure_assessment_template.md
│   │   ├── installation_qualification_protocol_template.md
│   │   ├── integrated_change_strategy_template.md
│   │   ├── integration-toolkits.md
│   │   ├── issue-alignment-summary.md
│   │   ├── issue-log.md
│   │   ├── issue_log_template.md
│   │   ├── it-pm-templates.md
│   │   ├── it-project-charter.md
│   │   ├── it-risk-register.md
│   │   ├── jira-integration-toolkit.md
│   │   ├── less_retrospective_template.md
│   │   ├── lessons-learned.md
│   │   ├── manufacturing_batch_record_template.md
│   │   ├── mappings
│   │   │   └── template-field-map.json
│   │   ├── meeting-templates.md
│   │   ├── methodology-comparison.md
│   │   ├── methodology-selector.md
│   │   ├── metrics_dashboard_template.md
│   │   ├── migration
│   │   │   ├── consolidation-map.md
│   │   │   ├── dependency-map.json
│   │   │   ├── legacy-to-canonical.csv
│   │   │   └── migration-status.csv
│   │   ├── migration_plan_template.md
│   │   ├── milestone-review.md
│   │   ├── monitoring_alerting_template.md
│   │   ├── ms-project-integration-toolkit.md
│   │   ├── okr-template.md
│   │   ├── operational_qualification_protocol_template.md
│   │   ├── organizational_change_management_framework.md
│   │   ├── overall_product_backlog_template.md
│   │   ├── performance-dashboard.md
│   │   ├── performance_qualification_protocol_template.md
│   │   ├── pharmaceutical_qbd_template.md
│   │   ├── pi_planning_template.md
│   │   ├── pm-utilities.md
│   │   ├── portfolio-financial-aggregation.md
│   │   ├── portfolio_kanban_template.md
│   │   ├── prioritization-framework-guide.md
│   │   ├── problem_management_process_template.md
│   │   ├── process-digitization-workflow.md
│   │   ├── process-maturity-assessment-template.md
│   │   ├── process_control_template.md
│   │   ├── process_validation_master_plan_template.md
│   │   ├── process_validation_protocol_template.md
│   │   ├── product-metrics-dashboard.md
│   │   ├── product-owner-templates.md
│   │   ├── product-strategy-canvas.md
│   │   ├── product-vision-template.md
│   │   ├── product_backlog_example.md
│   │   ├── product_backlog_template.md
│   │   ├── professional-standards.md
│   │   ├── program-manager-pm-templates.md
│   │   ├── program_charter_template.md
│   │   ├── program_management_plan_template.md
│   │   ├── progressive-complexity.md
│   │   ├── progressive_acceptance_plan_template.md
│   │   ├── project-charter-example.md
│   │   ├── project-closure-phase.md
│   │   ├── project-dashboard-template.md
│   │   ├── project-execution-phase.md
│   │   ├── project-health-assessment-template.md
│   │   ├── project-initiation-phase.md
│   │   ├── project-intelligence-cli-gateway.md
│   │   ├── project-intelligence-cli-implementation-report.md
│   │   ├── project-management-plan-example.md
│   │   ├── project-monitoring-control-phase.md
│   │   ├── project-planning-phase.md
│   │   ├── project-schedule.md
│   │   ├── project_closure_report_template.md
│   │   ├── project_execution_status_report_template.md
│   │   ├── project_management_plan_template.md
│   │   ├── project_performance_monitoring_template.md
│   │   ├── project_roadmap_template.md
│   │   ├── project_schedule_template.md
│   │   ├── purchase_order_template.md
│   │   ├── quality-checklist.md
│   │   ├── quality-prediction.md
│   │   ├── quality-test-plan-template.md
│   │   ├── quality_management_review_template.md
│   │   ├── raid_log_template.md
│   │   ├── real-time-budget-variance-analysis.md
│   │   ├── real-time-data-sync.md
│   │   ├── regulatory_inspection_readiness_plan_template.md
│   │   ├── regulatory_strategy_plan_template.md
│   │   ├── release_management_template.md
│   │   ├── remediation-action-plan-template.md
│   │   ├── requirements_traceability_matrix_template.md
│   │   ├── resource-management-assessment-template.md
│   │   ├── resource-management-plan-template.md
│   │   ├── resource-optimization.md
│   │   ├── resource-planning.md
│   │   ├── risk-assessment-framework.md
│   │   ├── risk-management-assessment-template.md
│   │   ├── risk-management-plan-template.md
│   │   ├── risk-prediction.md
│   │   ├── risk-register.md
│   │   ├── risk_assessment_template.md
│   │   ├── roadmap-product-backlog.md
│   │   ├── roi-sample-data.csv
│   │   ├── roi-setup-guide.md
│   │   ├── roi-tracking-automation.md
│   │   ├── roi_tracking_template.md
│   │   ├── safe_art_coordination_template.md
│   │   ├── safe_metrics_dashboard_template.md
│   │   ├── safe_metrics_reporting_template.md
│   │   ├── safe_portfolio_kanban_template.md
│   │   ├── safe_program_increment_planning_template.md
│   │   ├── schedule-intelligence.md
│   │   ├── schemas
│   │   │   ├── README.md
│   │   │   └── examples
│   │   │       ├── core-project-charter.example.yaml
│   │   │       └── extension-agile-status-report.example.yaml
│   │   ├── scope-statement.md
│   │   ├── security-awareness-program.md
│   │   ├── security-change-management-protocol.md
│   │   ├── security-controls-matrix.md
│   │   ├── security-implementation-roadmap.md
│   │   ├── setup.md
│   │   ├── skills-matrix-template.md
│   │   ├── software-development-pm-templates.md
│   │   ├── software-project-charter.md
│   │   ├── software-requirements-specification-template.md
│   │   ├── software-risk-register.md
│   │   ├── software-test-plan.md
│   │   ├── sprint-planning-template.md
│   │   ├── sprint-retrospective-template.md
│   │   ├── sprint-review-template.md
│   │   ├── sprint_planning_example.md
│   │   ├── sprint_retrospective_example.md
│   │   ├── sprint_review_example.md
│   │   ├── stakeholder-collaboration-framework.md
│   │   ├── stakeholder-engagement-assessment-template.md
│   │   ├── stakeholder-register.md
│   │   ├── stakeholder-update.md
│   │   ├── stakeholder_communication_planning.md
│   │   ├── standards
│   │   │   ├── index-governance.md
│   │   │   ├── modularization.md
│   │   │   ├── placeholders.md
│   │   │   ├── tailoring-guidance.md
│   │   │   ├── template-naming-rules.md
│   │   │   └── template-taxonomy.md
│   │   ├── status-report.md
│   │   ├── story-writing-checklist.md
│   │   ├── system-security-plan.md
│   │   ├── team-assignments.md
│   │   ├── team-charter-template.md
│   │   ├── team-charter.md
│   │   ├── team-dashboard.md
│   │   ├── team-performance-assessment-template.md
│   │   ├── technical-debt-log.md
│   │   ├── technical-design-document-template.md
│   │   ├── technology-adoption-roadmap.md
│   │   ├── template-index.md
│   │   ├── template-selector.md
│   │   ├── test-plan-template.md
│   │   ├── timesheet-tracking-template.md
│   │   ├── traditional-project-charter-template.md
│   │   ├── traditional-project-management-plan-template.md
│   │   ├── uat-plan-template.md
│   │   ├── uat-strategy-template.md
│   │   ├── user-story-mapping-template.md
│   │   ├── user-story-template.md
│   │   ├── user_story_template.md
│   │   ├── validation-master-plan-template.md
│   │   ├── validation_master_plan.md
│   │   ├── vulnerability-management-plan.md
│   │   ├── waterfall-project-assessment-template.md
│   │   ├── work-breakdown-structure-template.md
│   │   └── work-breakdown-structure.md
│   ├── testing
│   │   └── README.md
│   └── versioning.md
├── examples
│   ├── README.md
│   ├── abac-evaluation.json
│   ├── connector-configs
│   │   ├── README.md
│   │   └── mcp-project-config.json
│   ├── demo-scenarios
│   │   ├── README.md
│   │   ├── approvals.json
│   │   ├── assistant-responses.json
│   │   ├── full-platform-expected-output.json
│   │   ├── full-platform-llm-response.json
│   │   ├── full-platform-request.json
│   │   ├── full-platform-workflow.json
│   │   ├── global-search.json
│   │   ├── lifecycle-metrics.json
│   │   ├── portfolio-health.json
│   │   ├── quickstart-expected-output.json
│   │   ├── quickstart-llm-response.json
│   │   ├── quickstart-request.json
│   │   ├── quickstart-workflow.json
│   │   ├── schedule.json
│   │   ├── wbs.json
│   │   └── workflow-monitoring.json
│   ├── integration_demo.py
│   ├── mcp_cross_system_demo.py
│   ├── methodology-maps
│   │   └── README.md
│   ├── portfolio-intake-request.json
│   ├── schema
│   │   └── portfolio-intake.schema.json
│   └── workflows
│       ├── README.md
│       ├── mcp-cross-system.workflow.yaml
│       └── portfolio-intake.workflow.yaml
├── integrations
│   ├── __init__.py
│   └── services
│       ├── __init__.py
│       └── integration
│           ├── README.md
│           ├── __init__.py
│           ├── ai_models.py
│           ├── analytics.py
│           ├── databricks.py
│           ├── event_bus.py
│           ├── external_sync.py
│           ├── ml.py
│           └── persistence.py
├── mkdocs.yml
├── ops
│   ├── config
│   │   ├── .env.demo
│   │   ├── .env.example
│   │   ├── README.md
│   │   ├── agents
│   │   │   ├── README.md
│   │   │   ├── approval-workflow-agent
│   │   │   │   ├── durable_workflows.yaml
│   │   │   │   └── workflow_templates.yaml
│   │   │   ├── approval_policies.yaml
│   │   │   ├── approval_workflow.yaml
│   │   │   ├── business-case-settings.yaml
│   │   │   ├── data-synchronisation-agent
│   │   │   │   ├── mapping_rules.yaml
│   │   │   │   ├── pipelines.yaml
│   │   │   │   ├── quality_thresholds.yaml
│   │   │   │   ├── schema_registry.yaml
│   │   │   │   └── validation_rules.yaml
│   │   │   ├── demo-participants.yaml
│   │   │   ├── intent-router.yaml
│   │   │   ├── intent-routing.yaml
│   │   │   ├── knowledge_agent.yaml
│   │   │   ├── orchestration.yaml
│   │   │   ├── portfolio.yaml
│   │   │   ├── risk_adjustments.yaml
│   │   │   └── schema
│   │   │       └── intent-routing.schema.json
│   │   ├── alembic.ini
│   │   ├── approval_policies.json
│   │   ├── common.yaml
│   │   ├── connector_maturity_policy.yaml
│   │   ├── connectors
│   │   │   ├── integrations.yaml
│   │   │   └── mock
│   │   │       ├── README.md
│   │   │       ├── azure_devops.yaml
│   │   │       ├── clarity.yaml
│   │   │       ├── jira.yaml
│   │   │       ├── planview.yaml
│   │   │       ├── sap.yaml
│   │   │       ├── servicenow.yaml
│   │   │       ├── teams.yaml
│   │   │       └── workday.yaml
│   │   ├── data-classification
│   │   │   └── levels.yaml
│   │   ├── demo-workflows
│   │   │   ├── approval-gating.workflow.yaml
│   │   │   ├── procurement.workflow.yaml
│   │   │   ├── project-intake.workflow.yaml
│   │   │   ├── resource-reallocation.workflow.yaml
│   │   │   ├── risk-mitigation.workflow.yaml
│   │   │   └── vendor-onboarding.workflow.yaml
│   │   ├── environments
│   │   │   ├── dev.yaml
│   │   │   ├── prod.yaml
│   │   │   └── test.yaml
│   │   ├── feature-flags
│   │   │   └── flags.yaml
│   │   ├── human_review.yaml
│   │   ├── iam
│   │   │   └── role-mapping.yaml
│   │   ├── maturity_model.yaml
│   │   ├── plans
│   │   │   ├── example_plan.yaml
│   │   │   ├── plan-009a18b1-fc3f-40d2-8b28-5f4e1973da71.yaml
│   │   │   ├── plan-00b0753c-ede8-4fd9-971b-3f004d68f0e2.yaml
│   │   │   ├── plan-00dd7510-5ae7-4df2-9e03-6429d18e7b80.yaml
│   │   │   ├── plan-016689eb-695d-4b8c-9e22-2d1f817a2b35.yaml
│   │   │   ├── plan-01a6da67-0c72-4fbc-8251-2a8860a577d8.yaml
│   │   │   ├── plan-02adff3d-d4ef-49e8-a9d1-14ef6394378c.yaml
│   │   │   ├── plan-02e1f68b-4250-4c18-b3dc-3ef15411fd1d.yaml
│   │   │   ├── plan-02f0d773-5c6f-4e23-b77b-89f7e083eebb.yaml
│   │   │   ├── plan-0319e4ca-2738-47a5-b41a-773737554fa2.yaml
│   │   │   ├── plan-038fd2ff-2341-4797-aa49-2fc0934bc4e3.yaml
│   │   │   ├── plan-04152270-9559-4b43-a629-0d1bcf5d2afc.yaml
│   │   │   ├── plan-047fd643-3afb-4432-a3b5-2be0678f3f75.yaml
│   │   │   ├── plan-04b34eb7-10a3-4d26-882f-8c89027fb2e4.yaml
│   │   │   ├── plan-04d128c4-1d46-49e4-bf48-dafd5f774fbb.yaml
│   │   │   ├── plan-05050ff1-f8f1-45f0-bc96-ed138b14672d.yaml
│   │   │   ├── plan-051d970e-388c-4a2f-954a-4f9117ca1d3c.yaml
│   │   │   ├── plan-05301b55-e5d2-47d7-ab43-f6f2d0791983.yaml
│   │   │   ├── plan-054fb346-f8f2-46bd-8994-b7677f812a78.yaml
│   │   │   ├── plan-05a8bcd1-d591-4803-ba38-00acbed6fc26.yaml
│   │   │   ├── plan-05bddf30-9aff-4123-9691-fe4167c9bde7.yaml
│   │   │   ├── plan-05dbd619-6457-41f8-85f7-5e0eb4d69e00.yaml
│   │   │   ├── plan-06077498-de50-48e0-bbc7-320e1cad56f5.yaml
│   │   │   ├── plan-064cab5d-212b-4b42-a109-a045d0de693a.yaml
│   │   │   ├── plan-064da57a-d9a2-4e04-8d44-e646b4ed73ef.yaml
│   │   │   ├── plan-06539710-fdb0-46a3-8d32-9cf77230b086.yaml
│   │   │   ├── plan-0721c146-259b-487e-897d-ab1f8dcbb417.yaml
│   │   │   ├── plan-07654e1e-dd35-4c71-8d7e-4800c9b501e5.yaml
│   │   │   ├── plan-07abddcf-a0b6-4679-a213-806a1986cfbe.yaml
│   │   │   ├── plan-08ef7fbf-e5ad-42af-8d25-7f0700db44a8.yaml
│   │   │   ├── plan-0900c66f-9efa-4b05-b2fc-a38b59ee93db.yaml
│   │   │   ├── plan-0905ef7b-01ea-49d0-88b0-cd9204ad366d.yaml
│   │   │   ├── plan-092cead2-6bfc-4715-9eb3-dc7cacdbfb98.yaml
│   │   │   ├── plan-09b3a660-c5bc-4af9-b04e-0dab461d50ed.yaml
│   │   │   ├── plan-0a862adc-04dc-484a-9a8b-d449d4ed8573.yaml
│   │   │   ├── plan-0a8cdb58-d3f5-45ea-a3a3-9fdcbab50da4.yaml
│   │   │   ├── plan-0ac3e63f-df20-4cc7-87f3-68f8630fe97f.yaml
│   │   │   ├── plan-0b82bfc7-4b29-42c2-94e7-393dc911d0e9.yaml
│   │   │   ├── plan-0c5fff09-51c1-4542-b990-a9c550b9a29e.yaml
│   │   │   ├── plan-0c6567c9-3051-48d9-96bf-0d43e386b98f.yaml
│   │   │   ├── plan-0d68534c-5409-4dc7-8206-7996667981ae.yaml
│   │   │   ├── plan-0dc6d029-5187-4859-b92b-8042bffa9109.yaml
│   │   │   ├── plan-0dec3edf-ba18-4af1-bc3a-a9a3856290e4.yaml
│   │   │   ├── plan-0e4dec05-a702-4faa-b4db-bf8e7467de82.yaml
│   │   │   ├── plan-0eff7343-541c-4f27-99d3-8f58c0507356.yaml
│   │   │   ├── plan-0f0fb398-d56c-40c8-889a-2087f3eb1774.yaml
│   │   │   ├── plan-0f13964e-5617-442e-9f99-5c05fa850bb6.yaml
│   │   │   ├── plan-0f2b12ed-5d52-467d-8810-6fece6faeb7e.yaml
│   │   │   ├── plan-0f69914c-850a-434f-b355-03460ba8b771.yaml
│   │   │   ├── plan-0f7f9a09-6f79-4c29-9024-d1ed9a32d407.yaml
│   │   │   ├── plan-100033f8-8ae5-4107-b492-947fb342f828.yaml
│   │   │   ├── plan-10225097-9545-44a1-9458-f953d2b8684d.yaml
│   │   │   ├── plan-1117fe37-4bd3-477c-bde0-3030741f560b.yaml
│   │   │   ├── plan-113c7683-8fdf-4078-8334-b12a6fc3573a.yaml
│   │   │   ├── plan-1141cbfe-294c-48e5-8e70-ea5f19096347.yaml
│   │   │   ├── plan-1185e646-b8d9-4bc4-9e3a-1bd91fc96ce6.yaml
│   │   │   ├── plan-1186930e-4021-4d67-a9f8-0ccf84232875.yaml
│   │   │   ├── plan-11cd3a22-c8a1-443f-99b6-4c1513b609f3.yaml
│   │   │   ├── plan-12c86284-c310-4b30-a8fc-d243902df891.yaml
│   │   │   ├── plan-1363008e-e9fa-49c9-9355-5c6d69d0bd1f.yaml
│   │   │   ├── plan-139ed6e5-b624-4e1f-a0d8-65197d315d7a.yaml
│   │   │   ├── plan-142f0e68-323a-4a46-985f-8d4c51345354.yaml
│   │   │   ├── plan-14319cbc-52a7-4015-a8a2-ef4a203cac70.yaml
│   │   │   ├── plan-14a87167-1b18-4b54-8dd3-3eb4808d5af7.yaml
│   │   │   ├── plan-14cdea0e-232c-4711-8c2e-aee5d100dab7.yaml
│   │   │   ├── plan-1519fb9a-68cc-47ec-ae42-d51a65380702.yaml
│   │   │   ├── plan-157dc38e-d9ce-4096-94a3-53ce13ded9a0.yaml
│   │   │   ├── plan-1583da7f-e3c0-4bee-ad1f-288ae00b8ca2.yaml
│   │   │   ├── plan-158d6b33-0dc0-4969-af37-52b0fc7a77c2.yaml
│   │   │   ├── plan-1611b429-3d91-4572-baa1-f57dc2294b65.yaml
│   │   │   ├── plan-16932d0c-be35-45fa-baed-dbf969b18bc2.yaml
│   │   │   ├── plan-16cbc1eb-ccce-43a3-bc4d-f2b9c531802f.yaml
│   │   │   ├── plan-1701b54f-8bc9-4aad-b118-6d49ce879899.yaml
│   │   │   ├── plan-170c006b-d7bd-4021-a8a6-9b345766237d.yaml
│   │   │   ├── plan-176a0dbc-e0ad-4b77-b182-f8876b9b1e6d.yaml
│   │   │   ├── plan-1822128e-2777-4c29-8c8d-782a036de385.yaml
│   │   │   ├── plan-1850edd6-9c91-495b-9829-6b25276fc665.yaml
│   │   │   ├── plan-191dfa9d-ea6c-4cb3-8dd6-1cebf9593f23.yaml
│   │   │   ├── plan-192a7aa6-74ef-4426-9ec2-f7cbada9eb63.yaml
│   │   │   ├── plan-19653b43-237a-41e1-a20d-49818be38ef3.yaml
│   │   │   ├── plan-19a149cc-f794-4683-a111-8978c72dba01.yaml
│   │   │   ├── plan-19da90e8-cfd4-4e12-bd56-63dcd99ec85c.yaml
│   │   │   ├── plan-1a66b204-2ac4-44c9-bfe4-ca4df6f7672c.yaml
│   │   │   ├── plan-1a875687-b670-49cf-81a2-d078e9cc093c.yaml
│   │   │   ├── plan-1a8c79ab-0bd1-40c7-8304-ff34ed928986.yaml
│   │   │   ├── plan-1a970be5-b09f-4a1e-af37-79770c97e220.yaml
│   │   │   ├── plan-1b195c65-4ff9-4499-8ff8-7c6f02a48041.yaml
│   │   │   ├── plan-1bf52746-892e-4034-a783-f26f775d5409.yaml
│   │   │   ├── plan-1c16b376-b037-41b1-887c-c9eebdac21c0.yaml
│   │   │   ├── plan-1ca1a436-d4ef-4100-8d19-c432cbcfc0c4.yaml
│   │   │   ├── plan-1da69850-babe-4f26-9da2-88073044dbfd.yaml
│   │   │   ├── plan-1df58621-9b23-41d4-8f0c-ef3098799573.yaml
│   │   │   ├── plan-1e0fb06f-d15a-4f0a-83cf-e6fa726ee360.yaml
│   │   │   ├── plan-1e63e179-246f-4441-86d5-558c8d7675c9.yaml
│   │   │   ├── plan-1eb55f0d-553b-435c-87b0-10ba68353ab5.yaml
│   │   │   ├── plan-1f1ee941-07cd-49b8-8be3-d743b1e8ac05.yaml
│   │   │   ├── plan-1f27dec8-643d-411d-9a38-95d5f151827f.yaml
│   │   │   ├── plan-1fa1684a-34c7-416e-bdc2-d5ab6315c991.yaml
│   │   │   ├── plan-20204b2f-aee3-4ba3-822d-c3e3bc43ad69.yaml
│   │   │   ├── plan-20c2b4d4-f4ff-4729-8dda-f10879084f17.yaml
│   │   │   ├── plan-218b0c08-6eed-4166-b9f7-736cd898e7e1.yaml
│   │   │   ├── plan-219b67e0-d3db-4025-81ca-50b72c0e0bcc.yaml
│   │   │   ├── plan-225d2341-d558-46cb-a933-f260d3d2fd90.yaml
│   │   │   ├── plan-22b1fb34-04d9-487d-bf41-309ca3f2bdbd.yaml
│   │   │   ├── plan-23c7849f-5498-4967-a6da-547bbfe5d66a.yaml
│   │   │   ├── plan-23d9e8e0-3e89-4142-a718-8f92ee3047b4.yaml
│   │   │   ├── plan-23e07b74-1e31-49b6-80f7-7a9428d0e08e.yaml
│   │   │   ├── plan-24db9d07-37f8-4df8-8b61-faa1d7770e8e.yaml
│   │   │   ├── plan-254020a8-f94c-4493-adeb-53f8cf68e802.yaml
│   │   │   ├── plan-255b73d9-b011-42a0-a8e4-9bdbd568fa7d.yaml
│   │   │   ├── plan-25cb3ed2-fc67-4dc2-b937-dd09fd6df557.yaml
│   │   │   ├── plan-25f63635-511f-4925-a4cc-277f20aae33e.yaml
│   │   │   ├── plan-2600fa16-7079-449d-bdcc-3d1d44a61366.yaml
│   │   │   ├── plan-26535b75-de6b-42c4-94d0-ac502ea4a62d.yaml
│   │   │   ├── plan-265addda-2eff-4b4f-aa47-1364d7d2155c.yaml
│   │   │   ├── plan-26ba06dc-51df-4053-830d-4e9aa729cb95.yaml
│   │   │   ├── plan-2716d513-ec35-4e42-9827-cc361c5825c5.yaml
│   │   │   ├── plan-277aa922-b2d9-466c-af2f-5ce652648890.yaml
│   │   │   ├── plan-27955aa1-8e39-4c9a-a2c7-03e0c1f5b6bf.yaml
│   │   │   ├── plan-27980bdc-dbb7-4505-b313-c2c891741820.yaml
│   │   │   ├── plan-2857a975-fc3c-4dc1-9067-d6796e7ec7d7.yaml
│   │   │   ├── plan-28b6f563-af19-406c-942c-ad19c35b9419.yaml
│   │   │   ├── plan-28fafb27-84ba-4959-ad12-aa206806ef18.yaml
│   │   │   ├── plan-293fb28d-6493-45ca-81df-aad2ecb01e2c.yaml
│   │   │   ├── plan-2975294a-c824-4b6c-bcd5-7eefa755e8e7.yaml
│   │   │   ├── plan-298cb0a1-52b9-4a8e-8260-abc5d614a24d.yaml
│   │   │   ├── plan-29f19422-898b-4dde-83c4-f88ec7ee9943.yaml
│   │   │   ├── plan-2a1de743-8be4-48cb-bd12-20f8aba9d3ff.yaml
│   │   │   ├── plan-2b82a33a-390e-4b04-bde4-c6d88e04a0c3.yaml
│   │   │   ├── plan-2bd5ab37-e7a0-4a64-b27b-07bff646f5e7.yaml
│   │   │   ├── plan-2bdcadf1-24cd-494f-a2bc-37e26f14094c.yaml
│   │   │   ├── plan-2be0fe60-99d8-46ea-a8ec-09611902e41f.yaml
│   │   │   ├── plan-2bf38ace-bd89-43d7-93ab-a0fdabb9a39f.yaml
│   │   │   ├── plan-2c11c962-b91e-4f19-aac2-04a175e660f9.yaml
│   │   │   ├── plan-2c399e1e-e736-4ae1-ba06-53ee0db38589.yaml
│   │   │   ├── plan-2c39f9d0-64e4-4f42-b306-765d192b9d61.yaml
│   │   │   ├── plan-2ccd5bc1-248d-4fe7-a5e2-541796161a63.yaml
│   │   │   ├── plan-2cda00a3-d251-4c11-9a8d-224d86641cde.yaml
│   │   │   ├── plan-2ced46b6-34a5-4aa7-98a9-c39d904c4d6d.yaml
│   │   │   ├── plan-2d02fa4c-ae40-4179-a598-31bf426a8622.yaml
│   │   │   ├── plan-2db6b556-5d34-49b7-a62f-f1cf1ecf256d.yaml
│   │   │   ├── plan-2dd50d7e-10df-4477-8c06-b799728feef6.yaml
│   │   │   ├── plan-2ebe71e2-aec3-4ba1-8154-57bcf4353199.yaml
│   │   │   ├── plan-2ee4fe91-60c3-4ccf-af55-d5398ab5f5e9.yaml
│   │   │   ├── plan-2f34c5b3-0826-4862-95ce-8835da0256ce.yaml
│   │   │   ├── plan-2fa8f35f-ed2b-4eb2-9140-77fa915aecfb.yaml
│   │   │   ├── plan-2fb0e847-c23b-46d6-a8ec-24c321410a73.yaml
│   │   │   ├── plan-3089e9c9-d667-4d90-8fd4-d6e1cd53f2fd.yaml
│   │   │   ├── plan-3190cdc3-db45-48b9-b635-70575a8364f8.yaml
│   │   │   ├── plan-31e2a230-42e5-4beb-9516-94159bdc0351.yaml
│   │   │   ├── plan-3285ca99-659f-464c-8967-29ce2256d3f2.yaml
│   │   │   ├── plan-334dfb17-8f82-4af5-87dc-dedb4af1c93c.yaml
│   │   │   ├── plan-34397897-051c-470b-8622-af0df156a17d.yaml
│   │   │   ├── plan-343dadb1-a545-4f00-9f7b-ae4b099cbcc4.yaml
│   │   │   ├── plan-34bc146b-9356-4d01-8782-5439d07d205b.yaml
│   │   │   ├── plan-35b5e755-2511-4543-9924-746c57e093d7.yaml
│   │   │   ├── plan-35db3a77-d3e6-473c-baf5-0ee27fb319aa.yaml
│   │   │   ├── plan-3615f4e6-042e-4039-a657-be39b8faf20d.yaml
│   │   │   ├── plan-36555444-cede-41bb-addc-b8a38635a029.yaml
│   │   │   ├── plan-36704451-c3a4-403d-b379-969db2fb876c.yaml
│   │   │   ├── plan-368571e8-f00a-440f-b6c9-6670e535d472.yaml
│   │   │   ├── plan-369a0059-4b7d-44f7-8d3b-543c5e8533b2.yaml
│   │   │   ├── plan-36ea718f-e352-439b-8cd1-87c0d856b881.yaml
│   │   │   ├── plan-371a97a5-5c4d-40bf-90d1-a24982e7e8c5.yaml
│   │   │   ├── plan-376f96de-7062-44ff-bca1-ce268c250f82.yaml
│   │   │   ├── plan-37736b98-5d99-4572-8fa8-93926d0d7b74.yaml
│   │   │   ├── plan-377dc598-e8b5-489d-87c4-3523eec6c3b2.yaml
│   │   │   ├── plan-37947bd0-9364-4bc2-8b40-c83fe26612ca.yaml
│   │   │   ├── plan-379c47c8-b733-467b-80bb-ea15cfe11cf7.yaml
│   │   │   ├── plan-37d1266d-f11f-4d2e-9e5f-5ee6856f8999.yaml
│   │   │   ├── plan-38bff15b-9d3b-44eb-84e5-271da87feec8.yaml
│   │   │   ├── plan-390f2c3f-be41-4513-a16d-6bbc0b0f8166.yaml
│   │   │   ├── plan-39a9b5cb-e658-49c1-9ef8-e47ca0059221.yaml
│   │   │   ├── plan-3a00ceb9-5fdf-43be-a28c-f43963b97e2b.yaml
│   │   │   ├── plan-3a32a39d-0207-4748-827a-dfb7ef762f9f.yaml
│   │   │   ├── plan-3b6de128-21e4-4ddb-9486-0251ee105f18.yaml
│   │   │   ├── plan-3c22b2de-d66d-4a51-a319-ca09fdea5467.yaml
│   │   │   ├── plan-3c4d0d29-b682-4583-b400-b73444210025.yaml
│   │   │   ├── plan-3c814737-a319-4768-ad4f-08596173cfe4.yaml
│   │   │   ├── plan-3d09f7c1-f113-46d4-9dcc-f57161560408.yaml
│   │   │   ├── plan-3d50b594-e89a-46ba-9b90-0004093cf471.yaml
│   │   │   ├── plan-3edfa969-6a21-4eeb-9985-b134a6f3ac70.yaml
│   │   │   ├── plan-3f4210c9-c872-4fd7-aa7e-6960716031e5.yaml
│   │   │   ├── plan-3f850eff-97ce-4bd6-9574-0ce243521a70.yaml
│   │   │   ├── plan-401924bd-813e-426d-861d-756bb507b7ce.yaml
│   │   │   ├── plan-403ca2fb-15c7-444f-8bdd-f51c76db86fa.yaml
│   │   │   ├── plan-40eeb8a7-dd5f-4788-947a-f8b47d57c170.yaml
│   │   │   ├── plan-41248d6d-e153-4bec-b926-26419a545134.yaml
│   │   │   ├── plan-425f1497-ddd3-4019-9a47-4870b7e5cf7d.yaml
│   │   │   ├── plan-426d0670-edb3-4f50-9694-bb00aae296f0.yaml
│   │   │   ├── plan-43b1a456-0ea6-44d7-bd67-051f46744b3e.yaml
│   │   │   ├── plan-43e770ee-3765-4da9-b02e-a71500ebd26c.yaml
│   │   │   ├── plan-4412ab14-16eb-4391-b07b-14d79af771e1.yaml
│   │   │   ├── plan-44948f32-6cae-4748-97d3-9d0f4bb7dbf4.yaml
│   │   │   ├── plan-457a4dc1-5baf-4529-80fc-f982a32939a9.yaml
│   │   │   ├── plan-46291f07-84a5-4d43-98a5-f7c8c16b22ac.yaml
│   │   │   ├── plan-466897e2-a857-4b12-b4f5-d251a5c8e00b.yaml
│   │   │   ├── plan-468a69ce-e830-4d44-84d1-25ed8a3e4803.yaml
│   │   │   ├── plan-473b7aee-f78b-4250-adff-5bf02f34aec9.yaml
│   │   │   ├── plan-47e04fdf-002c-49f4-ad31-fa7dd426cca9.yaml
│   │   │   ├── plan-480c4765-edd6-4a39-89bc-5f940ff3251f.yaml
│   │   │   ├── plan-481ab49f-9ba1-4bb8-bd87-80a61f6cdb6e.yaml
│   │   │   ├── plan-48646e37-4579-406f-af11-28a79f0b420c.yaml
│   │   │   ├── plan-486c37a0-d363-4361-9a22-1ccb8edc5c30.yaml
│   │   │   ├── plan-491d20a5-8eac-42e9-867b-8c3b9156887d.yaml
│   │   │   ├── plan-49bead0b-9659-4fa5-aa07-015070f8b3a3.yaml
│   │   │   ├── plan-49cdf531-069b-41a8-884d-ce550c3f6af6.yaml
│   │   │   ├── plan-49d2b7b3-af50-4359-9021-0a441f7a495a.yaml
│   │   │   ├── plan-49dfde85-1a23-41c2-b928-c81ff311f5c7.yaml
│   │   │   ├── plan-4ad8b468-01a3-4335-a7f5-f2b7c4c9b0c5.yaml
│   │   │   ├── plan-4b884a76-a580-4491-82df-76ffaa588303.yaml
│   │   │   ├── plan-4bc78b71-6ac5-4b0c-b2af-307afec71414.yaml
│   │   │   ├── plan-4be5b1b9-89dd-4cc6-a300-06c22910d4e7.yaml
│   │   │   ├── plan-4bf23281-4622-4ece-b9ea-bbfce9ebb70a.yaml
│   │   │   ├── plan-4c476e97-560d-4b9c-a923-fee270c7ef50.yaml
│   │   │   ├── plan-4cfb37e3-12f5-4b9c-9d89-1f83e611b139.yaml
│   │   │   ├── plan-4d16786b-45db-4c87-bd75-61626c5f3e62.yaml
│   │   │   ├── plan-4d2e04e9-e0e2-40de-8193-87f9d43c0b0d.yaml
│   │   │   ├── plan-4d41d3ba-f60d-42a3-92c8-8b54a867206d.yaml
│   │   │   ├── plan-4d796a04-3963-46e8-8ff6-b1d62f88ddac.yaml
│   │   │   ├── plan-4ddc3664-7fa9-4f3f-88f6-f3a85177f347.yaml
│   │   │   ├── plan-4e5e200b-b299-42c3-97e5-4a3579db7a33.yaml
│   │   │   ├── plan-4e7db08f-2bb2-40ca-bbcd-624b7fa4f27f.yaml
│   │   │   ├── plan-4e9fe787-a2de-4c54-bfa0-1f3ef9621ed0.yaml
│   │   │   ├── plan-4ea21134-4585-4a28-8298-65c852e81fa2.yaml
│   │   │   ├── plan-4fab8ae9-5145-42ac-9883-3264621669a2.yaml
│   │   │   ├── plan-500b861c-612b-49b0-9808-571f23a6bebb.yaml
│   │   │   ├── plan-50564805-36c9-40bd-b6ce-972ac1c22ad5.yaml
│   │   │   ├── plan-50d0915f-a5ae-42ba-8f20-942dd7c9cec0.yaml
│   │   │   ├── plan-50e83bb0-8913-4cd8-bb29-90071e32485c.yaml
│   │   │   ├── plan-5129bbe6-bc60-446e-870a-836ad49e6fdd.yaml
│   │   │   ├── plan-51624e4e-52c3-4f51-8257-9bd70fe4812f.yaml
│   │   │   ├── plan-51f68676-9ac5-4e24-a04a-a4585f5f5f72.yaml
│   │   │   ├── plan-52003a1d-ed9e-4a69-bfcf-fccfbf98ac4f.yaml
│   │   │   ├── plan-52cdd21a-d3ba-4e42-8838-c7c7845808fc.yaml
│   │   │   ├── plan-534f60d4-3729-47e5-b7b7-12ca7c2b3b07.yaml
│   │   │   ├── plan-53a662d8-3eb7-42a3-9ad0-4e43296cf577.yaml
│   │   │   ├── plan-545f5851-ca1d-490e-9a70-b39741ea4564.yaml
│   │   │   ├── plan-54752401-fbc6-4ffe-b840-08eade6c0260.yaml
│   │   │   ├── plan-54a5081c-874a-4ad5-9fac-e9830abb1622.yaml
│   │   │   ├── plan-54d23254-aac6-4cd8-a06f-74f4bf5f663f.yaml
│   │   │   ├── plan-54f4f08b-17d9-4623-88f0-05ae59ea0340.yaml
│   │   │   ├── plan-5514579b-816d-42b4-bed6-2102cba824d5.yaml
│   │   │   ├── plan-55398bbc-742f-46f5-b9a5-269be688602b.yaml
│   │   │   ├── plan-55b936e2-c74d-42a1-bbcb-929cbbf9b6e1.yaml
│   │   │   ├── plan-575b92fe-a08c-44bf-9495-336a7d6aec9e.yaml
│   │   │   ├── plan-580282fc-451c-45a6-a968-17493e1bd9c7.yaml
│   │   │   ├── plan-58b1a09a-2b92-4887-8f18-f2aeb6896e20.yaml
│   │   │   ├── plan-59488049-b440-4449-bd48-1e9f072d0fbd.yaml
│   │   │   ├── plan-59cd7c22-cd3b-4a44-a20f-3ae2c07332ba.yaml
│   │   │   ├── plan-59ec115c-dcf4-4d9b-8b4c-4d044725cd62.yaml
│   │   │   ├── plan-59f41901-7c62-44d0-8d4f-7189d54c1422.yaml
│   │   │   ├── plan-5ab03982-f7a4-4e43-92da-49e950513e4e.yaml
│   │   │   ├── plan-5ac0e92a-6fdb-424f-9b54-0431b65a75ee.yaml
│   │   │   ├── plan-5af969ef-7cc6-492f-991b-3c7139f185c0.yaml
│   │   │   ├── plan-5b4bf1bd-fbfa-4bf5-88cf-eb5e29ba56e6.yaml
│   │   │   ├── plan-5bc324da-32f0-4d74-a7d0-3b2c5547e3f7.yaml
│   │   │   ├── plan-5bf105c1-0b9f-46da-85e6-ca67ab1c2a3e.yaml
│   │   │   ├── plan-5c9a70b9-8041-4232-bf75-4b7175fd49d5.yaml
│   │   │   ├── plan-5d08bd1b-9674-4707-ae52-f9a0010b4a78.yaml
│   │   │   ├── plan-5d921d60-e468-4989-9db1-83574c5cb242.yaml
│   │   │   ├── plan-5de65d60-4197-498e-87fa-da76424d2afb.yaml
│   │   │   ├── plan-5e876d6e-0a64-4307-8074-25cf2caaca2b.yaml
│   │   │   ├── plan-5eed4775-8013-44da-aefd-4978a3d11036.yaml
│   │   │   ├── plan-5f86e4db-5c0b-4d03-a5a1-d20854d02356.yaml
│   │   │   ├── plan-5f8e7990-f9e8-4a15-9eb8-ffdf249ff357.yaml
│   │   │   ├── plan-6070a5ef-bccb-44f0-b9fe-c478e6edd44d.yaml
│   │   │   ├── plan-60910489-667b-468b-8893-e4c33219079b.yaml
│   │   │   ├── plan-60936efc-a0b4-4cfa-8041-c2f36c27c7ae.yaml
│   │   │   ├── plan-60ec1ba1-7cd5-4bdc-9e1a-643d96429211.yaml
│   │   │   ├── plan-612ed4e3-53f4-480d-8b0f-cd3952a3e491.yaml
│   │   │   ├── plan-615b0bf6-fee3-4787-abdc-3543ab971d69.yaml
│   │   │   ├── plan-62a5bd2c-5dfe-4b64-a911-f2e5c87f7103.yaml
│   │   │   ├── plan-62e5c870-f70b-4cb8-9dde-256be1dfbaa5.yaml
│   │   │   ├── plan-62e7632f-901a-46e4-a091-d8fe6b3695b4.yaml
│   │   │   ├── plan-6375c31d-738e-423e-89d5-472df5ffcb6d.yaml
│   │   │   ├── plan-6379feb3-90b8-475c-a55a-fd33fa3a8793.yaml
│   │   │   ├── plan-643233c2-3baf-46aa-978a-ff3b52763da9.yaml
│   │   │   ├── plan-64af24fe-a5bf-4ec3-aa22-f079c519fc1d.yaml
│   │   │   ├── plan-65551899-dd45-43d2-9d1a-7926023d2346.yaml
│   │   │   ├── plan-66fa9ef7-0262-457a-8392-3b87f48d84b9.yaml
│   │   │   ├── plan-670e8308-9ebe-4987-b52b-05522c2cb914.yaml
│   │   │   ├── plan-6780b0e8-c66e-4054-b5fc-0bc947dca693.yaml
│   │   │   ├── plan-6832e455-3220-4299-9cd1-2549ec5196c5.yaml
│   │   │   ├── plan-683347f8-23ed-45d2-ab04-e5b52ab53c9a.yaml
│   │   │   ├── plan-69232ea9-119a-4e7a-ba7f-a8f6d47f8f01.yaml
│   │   │   ├── plan-69a5d652-e4e1-411b-aff5-dbd4eb480704.yaml
│   │   │   ├── plan-6a0f7370-d186-41ce-b907-9278987c81ea.yaml
│   │   │   ├── plan-6a1092c9-8343-4ccc-a320-6a54bd39b53f.yaml
│   │   │   ├── plan-6a4c3a42-2960-4b89-af7f-fbac7ec4446f.yaml
│   │   │   ├── plan-6b9030cd-ede4-4dd5-8011-51b383e18340.yaml
│   │   │   ├── plan-6be64b37-4d67-4c66-a8fb-afc189f50b61.yaml
│   │   │   ├── plan-6d6ace55-93fb-4ea4-be4e-50918989ba0c.yaml
│   │   │   ├── plan-6e07d794-f2a5-4dfd-a994-67e502ddd4bf.yaml
│   │   │   ├── plan-6e40dfa4-c30a-4c22-8b9f-f4fb190ef9dd.yaml
│   │   │   ├── plan-6e41c064-a284-4d50-b6c4-7eaea3e458c1.yaml
│   │   │   ├── plan-6e43445a-0b16-495d-999b-6b68a9633e61.yaml
│   │   │   ├── plan-6e8705a4-e59b-44ad-9616-4e72ef180486.yaml
│   │   │   ├── plan-6e94f9de-110f-427a-b608-0d9463f55278.yaml
│   │   │   ├── plan-6f00901e-82b7-4265-abed-f2f642199225.yaml
│   │   │   ├── plan-6fa59680-98da-4353-bea5-f906153ae9c7.yaml
│   │   │   ├── plan-6fd3d21d-902e-4893-b085-18f94177eb8d.yaml
│   │   │   ├── plan-70dd1f7a-e5fa-4cb8-9256-f7bac081f74b.yaml
│   │   │   ├── plan-71d2ea62-cc26-4e81-bb10-6da0c7a7c274.yaml
│   │   │   ├── plan-728109c9-8939-4ca9-bdcf-827f23a3de60.yaml
│   │   │   ├── plan-72d1343a-6005-4da0-bda5-101cfe1b5f22.yaml
│   │   │   ├── plan-7324a436-1e79-4406-ad0b-9673e1e8feb4.yaml
│   │   │   ├── plan-734e64c8-2ec6-4b12-bbbc-dc87a1e59c2f.yaml
│   │   │   ├── plan-736477b5-e101-45c9-bda0-3494f21926ab.yaml
│   │   │   ├── plan-7390f75f-6c45-4350-a476-83672165a2d4.yaml
│   │   │   ├── plan-73afb55b-00b2-48f5-a8d8-316d2acac94f.yaml
│   │   │   ├── plan-7495e854-f13d-45a7-a66e-91a80ffb92c0.yaml
│   │   │   ├── plan-74960919-6e88-4276-990d-4e172d4a2364.yaml
│   │   │   ├── plan-74b1ff80-fc57-469f-9955-e8fc2538604a.yaml
│   │   │   ├── plan-74d19d34-27d8-425e-a82d-5dc23c6ad169.yaml
│   │   │   ├── plan-760115c0-bf2d-4986-8e3e-3e92292bea86.yaml
│   │   │   ├── plan-7747f95d-00e6-48d3-b409-28f42c541cfa.yaml
│   │   │   ├── plan-7764adb6-ff27-4550-9e9e-eef0a74d3bf3.yaml
│   │   │   ├── plan-776ba14d-1a59-422e-a314-64ad68fa6179.yaml
│   │   │   ├── plan-778e796e-c231-4013-a497-c10c56a5b45e.yaml
│   │   │   ├── plan-77b25752-f214-4645-8b5a-628e000249c3.yaml
│   │   │   ├── plan-782fca3d-8905-4ec9-a0d3-88b15cc085b3.yaml
│   │   │   ├── plan-783965c3-5b82-4675-a276-5d401c08f77a.yaml
│   │   │   ├── plan-790c4d3c-f065-4ad1-9a0f-ed1776b62a3c.yaml
│   │   │   ├── plan-796e8642-3300-4180-a38d-0ab02214549a.yaml
│   │   │   ├── plan-79e6dde7-93bb-4fe9-98bb-a67bee3c00ad.yaml
│   │   │   ├── plan-7a164a42-71bc-4abb-a691-b4c4e2f69f21.yaml
│   │   │   ├── plan-7a52dfe7-8ce5-4df6-b84f-e793881509e0.yaml
│   │   │   ├── plan-7a7aa9d0-6b24-4c1f-822d-07a4931ee525.yaml
│   │   │   ├── plan-7a86ea63-adab-4d77-a466-afe43b2e1509.yaml
│   │   │   ├── plan-7a8a14b3-1382-4e02-b922-18227d5742b2.yaml
│   │   │   ├── plan-7ae565dc-3fab-4595-bb6f-7a1277235fcd.yaml
│   │   │   ├── plan-7af5ad97-9272-4ee6-a46d-03b2b1401d4f.yaml
│   │   │   ├── plan-7af919ed-c92d-4f96-84f6-786708bb190f.yaml
│   │   │   ├── plan-7b1739e3-1cef-4476-b54d-e2f685ed40a2.yaml
│   │   │   ├── plan-7b39ff38-1014-4ec9-9c32-ef0afefc9149.yaml
│   │   │   ├── plan-7d37e8e3-88d8-4c18-8c7d-f533e019e6aa.yaml
│   │   │   ├── plan-7d755926-63a2-4d88-bdf8-0ae9354b1018.yaml
│   │   │   ├── plan-7dadc800-9af6-4ec7-8d2f-2f4eccf3f280.yaml
│   │   │   ├── plan-7e4c4a74-db91-4b40-b673-b3031b549f47.yaml
│   │   │   ├── plan-7e502be7-66fc-45c4-83ac-beebcac8fc83.yaml
│   │   │   ├── plan-7f129ebe-3575-488c-878e-ba08e44103e3.yaml
│   │   │   ├── plan-7fb6fe5e-301e-4530-b316-ba683c2e90d7.yaml
│   │   │   ├── plan-7fea15f2-727b-4c67-9388-30999af2cb8c.yaml
│   │   │   ├── plan-814e44d9-2229-400a-8606-fb2d1bc44a22.yaml
│   │   │   ├── plan-815c1faa-a5ac-4ec7-9f10-0980e532487d.yaml
│   │   │   ├── plan-815f2243-add3-46d3-aecc-ee17ad7fc350.yaml
│   │   │   ├── plan-8192d8b5-e5a6-49a3-9132-73c782414b25.yaml
│   │   │   ├── plan-821358e9-f01c-453c-931e-ad51b802dadd.yaml
│   │   │   ├── plan-82b0a06d-e532-468c-88bf-e451529ba4cd.yaml
│   │   │   ├── plan-83780fc6-5c8a-4540-87be-b8b2d3dae369.yaml
│   │   │   ├── plan-839e754e-bd1d-447d-8131-37600bf007eb.yaml
│   │   │   ├── plan-83a2e660-21e5-42e2-ab11-c20a6bec917d.yaml
│   │   │   ├── plan-8491af99-7b78-4332-bd1e-d098d27b76b1.yaml
│   │   │   ├── plan-84fc7dab-07a3-4b10-9f64-33167af96891.yaml
│   │   │   ├── plan-850b38c2-e5df-47b0-8930-8d3162df0244.yaml
│   │   │   ├── plan-85d718c7-4d5a-4984-8013-383a5bd25e94.yaml
│   │   │   ├── plan-865cb5b7-b855-4108-86ed-d84f65cb8118.yaml
│   │   │   ├── plan-86660ffb-12c9-4d45-b90b-732cfffdc5f7.yaml
│   │   │   ├── plan-86b2c17c-9a47-41f9-8529-0eb0ba25f7c6.yaml
│   │   │   ├── plan-86f27921-da61-432f-8bfd-4f7d4eaac98c.yaml
│   │   │   ├── plan-870eaf46-0a50-46c1-895b-7cc1a6511ce7.yaml
│   │   │   ├── plan-880811a9-7371-41d7-8f39-e1d70a2666b0.yaml
│   │   │   ├── plan-8812da59-3bef-40d3-a6ae-21914f356d2e.yaml
│   │   │   ├── plan-883f919c-9bf0-42f7-969f-c84fbaae03d9.yaml
│   │   │   ├── plan-8844cdeb-e8f5-4ad6-a707-55d387fabb21.yaml
│   │   │   ├── plan-88d17c09-d476-4859-aac9-7b8e3d40fed8.yaml
│   │   │   ├── plan-8912d88a-1612-4b8c-a3c2-878f3453dc65.yaml
│   │   │   ├── plan-8975c460-2d83-4364-bf55-e1aa1d35886a.yaml
│   │   │   ├── plan-89847136-7d2c-4adb-8c09-5c44426776bc.yaml
│   │   │   ├── plan-89aeaabc-425e-4b8b-aa9f-643988c8f5ff.yaml
│   │   │   ├── plan-89bad11a-5c3d-41dd-8d49-437e884a9b0f.yaml
│   │   │   ├── plan-8a0d1ccc-79cd-40c9-9191-58b387f6470c.yaml
│   │   │   ├── plan-8a56b1b4-2d0c-4fd8-a3d7-772b8488700b.yaml
│   │   │   ├── plan-8a6dc8f4-bfcc-41fa-a37e-d67f3c661ac1.yaml
│   │   │   ├── plan-8ab8b81d-4991-46d7-911d-00725d2c905c.yaml
│   │   │   ├── plan-8b010004-6ece-43fd-9359-ad87bbbe60dd.yaml
│   │   │   ├── plan-8b1b2d3d-a534-4b7a-b4be-6e5794e347d1.yaml
│   │   │   ├── plan-8b394bc1-d7db-4201-a53f-ea2516c50e4c.yaml
│   │   │   ├── plan-8bdcb6f9-e277-4a55-83a4-f171bc19852d.yaml
│   │   │   ├── plan-8c17fe7d-90b5-4d36-b8fd-1525f817d6b0.yaml
│   │   │   ├── plan-8c94c1a9-e3ee-4c29-984a-3d056c85926f.yaml
│   │   │   ├── plan-8cfeab67-ebba-4ed8-8c7b-023a5ca8b34d.yaml
│   │   │   ├── plan-8e476e49-9aad-4183-b85f-a99ece6d9817.yaml
│   │   │   ├── plan-8ecbba06-9f79-4985-b19c-36d036bdb6c9.yaml
│   │   │   ├── plan-8ee9cefc-c4d5-4819-a90b-fae1699dfe33.yaml
│   │   │   ├── plan-8ef0b835-3648-4bda-aba4-8d20d7bc7970.yaml
│   │   │   ├── plan-8f91b2f3-431d-4315-9b46-5ef2761801df.yaml
│   │   │   ├── plan-8f939071-e8b6-4b2d-bef6-72700748ad7a.yaml
│   │   │   ├── plan-901442ed-2282-451c-a27c-9fc016cc099b.yaml
│   │   │   ├── plan-90fa5d05-75e6-4e3f-95fc-6ce3532d22c5.yaml
│   │   │   ├── plan-912581c5-10b3-4035-944e-77d195492246.yaml
│   │   │   ├── plan-9133814f-0950-49dc-9a24-1337d5f06cf2.yaml
│   │   │   ├── plan-924cfa22-80d7-4f2e-b2ab-dcc7895f3d1c.yaml
│   │   │   ├── plan-929e50af-1afb-4294-b43c-7f0098535f9d.yaml
│   │   │   ├── plan-935d2c65-f58e-4b21-9cb2-dbee1ed95dbb.yaml
│   │   │   ├── plan-937c7d54-5cbc-45a5-bada-253a4f9f3b6f.yaml
│   │   │   ├── plan-938d9c9f-a4de-4009-a629-6ec9a9c64844.yaml
│   │   │   ├── plan-93972080-412f-43e6-892a-c4415e45147e.yaml
│   │   │   ├── plan-93d8188b-decd-4659-8582-a74ce9c1202d.yaml
│   │   │   ├── plan-93e7755f-5314-4589-8b0f-1efa9e1f3c0b.yaml
│   │   │   ├── plan-94cf0640-2950-45d9-bd70-8034c3d8e353.yaml
│   │   │   ├── plan-96865090-ae92-4247-ba2d-69ac1019fcbd.yaml
│   │   │   ├── plan-96f4dcaf-acb3-4139-94ba-d88b787cc4ad.yaml
│   │   │   ├── plan-9738f140-8e3e-449e-8756-fe290c051c00.yaml
│   │   │   ├── plan-973d4ae6-0b0a-44a6-8a43-89f3c4f40153.yaml
│   │   │   ├── plan-97634348-34dd-404d-bfd1-854ba25be5f2.yaml
│   │   │   ├── plan-978d52fe-3ada-479d-b188-4039c51b4850.yaml
│   │   │   ├── plan-980745c4-1904-4ffc-a918-9e121bb427bb.yaml
│   │   │   ├── plan-9853af44-0c31-4520-9825-754a929f89e6.yaml
│   │   │   ├── plan-986ca828-4520-442d-be34-b18990cb324d.yaml
│   │   │   ├── plan-98ae36aa-f20d-4c27-b8bd-cd466ea9cb4f.yaml
│   │   │   ├── plan-98feb32a-11a0-4bf1-b868-4bc32105803d.yaml
│   │   │   ├── plan-99846489-643f-4b1d-b3d7-8120b59bf9ae.yaml
│   │   │   ├── plan-9a32f6ea-1bcd-4275-a4ed-32a9a057a490.yaml
│   │   │   ├── plan-9a874749-d198-45c2-91f1-b1857008da71.yaml
│   │   │   ├── plan-9ae2d1f3-fb44-4601-ac2d-2d663ce3e897.yaml
│   │   │   ├── plan-9ae77b42-a415-43d8-8a91-c75cfbc7ba1c.yaml
│   │   │   ├── plan-9ae79e56-7775-4541-b7a2-70509424d034.yaml
│   │   │   ├── plan-9b7443fd-5786-4ef5-b8d6-76e9ea822099.yaml
│   │   │   ├── plan-9c0c00c3-fa61-4a39-a401-05fba71ebb90.yaml
│   │   │   ├── plan-9c6efb98-49dd-4a78-a85c-fc722271ddf2.yaml
│   │   │   ├── plan-9de345ea-83f1-4663-986e-bd29d4382fbd.yaml
│   │   │   ├── plan-9e701679-1ca8-4441-a9c9-9c0e16c3bdda.yaml
│   │   │   ├── plan-9f7d3176-6073-4aad-a123-3c8d1be2c335.yaml
│   │   │   ├── plan-9fc40944-30dc-4552-9534-4fbc92500994.yaml
│   │   │   ├── plan-a146b965-f3eb-42fd-8873-22c2e39f3961.yaml
│   │   │   ├── plan-a17db126-b412-4231-8c6a-d040475562c8.yaml
│   │   │   ├── plan-a17f7c15-4c8e-4803-996c-5ffc75d585fc.yaml
│   │   │   ├── plan-a1c85ce6-944e-4156-8ea8-61175aef098b.yaml
│   │   │   ├── plan-a27e3e2b-3c47-4d61-afeb-5d6695c4ea93.yaml
│   │   │   ├── plan-a31a7f07-eb5c-4718-a8a6-301ea1129b53.yaml
│   │   │   ├── plan-a38e44f6-04bd-4b53-bdf4-d3ae2b71aa60.yaml
│   │   │   ├── plan-a44c2d1d-1d6e-4d6c-a431-e6a29bd77549.yaml
│   │   │   ├── plan-a47e0305-01ca-443a-957e-9d9a9e18d5a9.yaml
│   │   │   ├── plan-a481f359-f80f-4f9e-a79a-25b3f4784bcf.yaml
│   │   │   ├── plan-a4cb9916-a000-4218-991e-9022e1c852ad.yaml
│   │   │   ├── plan-a5a0b12f-c27d-4c4b-8191-03735fd7cb4c.yaml
│   │   │   ├── plan-a5e7ffe3-1b9a-4dde-90ee-1c276258a69f.yaml
│   │   │   ├── plan-a6038285-7516-4f20-bc10-d0094724cb6f.yaml
│   │   │   ├── plan-a60e3707-fff4-4c5b-b7bc-6ed897bf50d2.yaml
│   │   │   ├── plan-a71f2097-599f-4576-96f7-a0963c95195a.yaml
│   │   │   ├── plan-a72df362-e540-49cd-b77c-11f30eb65fee.yaml
│   │   │   ├── plan-a7a30bce-fb20-40b2-9888-e1c85d206fe9.yaml
│   │   │   ├── plan-a7bf6076-2439-458f-b992-a492d9ad36c3.yaml
│   │   │   ├── plan-a7e5b8b4-2c30-4ed8-9a59-68fb20d42004.yaml
│   │   │   ├── plan-a82c1935-17e4-439f-ba50-44885d2e0b0e.yaml
│   │   │   ├── plan-a877facb-e3be-444a-a31f-45f9e0e60550.yaml
│   │   │   ├── plan-a89dd4df-bdb3-465a-bff0-89ffbf060289.yaml
│   │   │   ├── plan-a93dc424-336d-453c-b9e2-7efb5b7f8f7c.yaml
│   │   │   ├── plan-a96251e1-7c07-406e-ab5a-b2aefc0af14e.yaml
│   │   │   ├── plan-a973be69-8645-45e0-80e8-c934096157a4.yaml
│   │   │   ├── plan-a9d1f5aa-acf9-4931-bed6-16ed9f8db43f.yaml
│   │   │   ├── plan-aa3e47ad-0406-4f13-b292-1115ecd9f48c.yaml
│   │   │   ├── plan-aa4ca5b5-99be-4ea1-a0e4-06c381946538.yaml
│   │   │   ├── plan-ab98b29b-f977-4eb1-a83c-cf83b2dddebd.yaml
│   │   │   ├── plan-ab9a4f80-9880-48b2-a051-73e9c504a3dc.yaml
│   │   │   ├── plan-abc1ee36-740c-458c-87e0-c0b922079e8e.yaml
│   │   │   ├── plan-ac2d105b-af2d-4793-bad5-0a12776ea8e2.yaml
│   │   │   ├── plan-ac4cb9b6-d0cd-494a-b345-b411e6f9e2ed.yaml
│   │   │   ├── plan-acb87e23-1489-4cca-9383-b837ad3d259f.yaml
│   │   │   ├── plan-acc13757-2f74-448c-98e7-9fea8d27a782.yaml
│   │   │   ├── plan-ace91ca1-bfe1-484b-b579-ae2b2361d023.yaml
│   │   │   ├── plan-ad74ee12-f47e-4344-9579-fb8c0fbd2d4a.yaml
│   │   │   ├── plan-ad891451-f959-4c0e-b22f-c4881a2da14c.yaml
│   │   │   ├── plan-adf5bf56-e9b6-4508-aa25-749b1732ff62.yaml
│   │   │   ├── plan-aea66c15-8664-49d5-a8c5-22b685733ba8.yaml
│   │   │   ├── plan-af0a73b2-0ca0-440a-9125-9b811c8f14c0.yaml
│   │   │   ├── plan-afa03d19-b925-4fc9-9378-742270ba03a5.yaml
│   │   │   ├── plan-afcbf48c-4ece-4da0-9b9d-15f3c5841e77.yaml
│   │   │   ├── plan-b0bb2d07-248f-40c0-884a-8edb1db691f8.yaml
│   │   │   ├── plan-b0dc6fba-40c7-4b6f-ad9e-1cbe5c0cb146.yaml
│   │   │   ├── plan-b0fffb32-dc91-4d26-b0bb-54051256fea1.yaml
│   │   │   ├── plan-b1337c7f-fdfe-421c-95db-4bec6362628d.yaml
│   │   │   ├── plan-b193de45-35c6-4010-a2e7-1ce71feaaab7.yaml
│   │   │   ├── plan-b2b05756-83df-4650-b665-fd759ae3b88f.yaml
│   │   │   ├── plan-b2e41e58-b4a4-4c85-946e-be7c6f56fdf5.yaml
│   │   │   ├── plan-b2e9d093-ee91-48b4-9c21-09f0a59baf42.yaml
│   │   │   ├── plan-b2f1fa99-a96b-4e2f-a24f-e83dd962aebb.yaml
│   │   │   ├── plan-b33bad41-4289-4ae4-a88c-16d6851b88c4.yaml
│   │   │   ├── plan-b3928032-10b2-4041-8df8-06cc9c768d16.yaml
│   │   │   ├── plan-b3a4e5b9-02ab-4f96-ae45-bc35cda18020.yaml
│   │   │   ├── plan-b4292ca3-bf67-4f88-9f3e-9a849a1e6e80.yaml
│   │   │   ├── plan-b42fa74b-905f-47ea-8cc0-fa3ecbc6aedf.yaml
│   │   │   ├── plan-b4cfe99a-921e-4892-84f7-77a4c63fbc11.yaml
│   │   │   ├── plan-b4d69989-a64a-4895-9780-4880d9429027.yaml
│   │   │   ├── plan-b58d21ed-c6d8-46c4-a45a-bcf26dc069c0.yaml
│   │   │   ├── plan-b5be3223-76f2-484c-9fc0-403d915c19d7.yaml
│   │   │   ├── plan-b6fcccb8-1677-45c3-9932-46d881355c46.yaml
│   │   │   ├── plan-b79a4e2c-139c-4560-bb2e-5d5e23d7fe35.yaml
│   │   │   ├── plan-b7d8a6b2-7c7a-45a7-80d1-90c245394f82.yaml
│   │   │   ├── plan-b8b00ef5-3459-4773-8452-4b85a9e71691.yaml
│   │   │   ├── plan-b90d0574-27ca-4ed7-b14b-85985eb5a25a.yaml
│   │   │   ├── plan-b9527217-0c54-4f7b-b151-9af18b02118b.yaml
│   │   │   ├── plan-b9644fb7-9347-4b25-b2ca-30cc487f78f4.yaml
│   │   │   ├── plan-b9ae5f1b-2fec-420a-9a0f-c12968fb2d37.yaml
│   │   │   ├── plan-b9c70b75-365c-44c3-ada4-346077042f83.yaml
│   │   │   ├── plan-ba1b5066-cf0f-4652-bc9f-ee0f0360ac44.yaml
│   │   │   ├── plan-ba480470-653b-4525-8ff6-46a09497c916.yaml
│   │   │   ├── plan-ba68443e-865d-4b86-870c-ebe076868d01.yaml
│   │   │   ├── plan-bb33c581-e891-444e-a3b1-2711e7ac99c1.yaml
│   │   │   ├── plan-bb614341-cb1f-49fc-9e08-955bba7f96b6.yaml
│   │   │   ├── plan-bc877336-4dee-4647-bc83-daf66e56ad12.yaml
│   │   │   ├── plan-bcce2541-b081-4c17-ac23-dc5e33d71b59.yaml
│   │   │   ├── plan-bd4ef4bd-ce78-4743-9547-1620afdd7ca5.yaml
│   │   │   ├── plan-be3c6e3c-1d82-416a-bee5-345aa9af44f4.yaml
│   │   │   ├── plan-bea70386-0b42-4b8b-a47d-c456b163a922.yaml
│   │   │   ├── plan-bf02a538-958c-4336-8bd0-527968d55b51.yaml
│   │   │   ├── plan-bf07bfea-fcd7-4f7f-805d-bdfc28d8f399.yaml
│   │   │   ├── plan-bf0a25e7-869a-4ba6-ba60-47e445cf6b58.yaml
│   │   │   ├── plan-bf1c0730-81e2-4f9a-92d4-0e8460c464ca.yaml
│   │   │   ├── plan-bf21e825-1023-4339-800a-1f5733c47885.yaml
│   │   │   ├── plan-bf8998ad-25f9-4adf-b160-45faec18597b.yaml
│   │   │   ├── plan-bf9bf43a-293f-4cbb-84b9-b9f089a437ad.yaml
│   │   │   ├── plan-bfab54c0-fb13-4c8a-be4a-83de6059734e.yaml
│   │   │   ├── plan-bfb1682f-768c-479c-ab92-a90df59435c7.yaml
│   │   │   ├── plan-c0ca366c-54e3-4cb0-a523-bd43727d8e46.yaml
│   │   │   ├── plan-c0d11103-1de7-4ff4-9307-df9e4874075a.yaml
│   │   │   ├── plan-c0e7872e-451c-4757-8c25-582786b1375d.yaml
│   │   │   ├── plan-c25abbd3-2ffa-487a-b8fe-7d4b1c83d3b2.yaml
│   │   │   ├── plan-c284b47e-c1b6-4ae4-a53e-e797f277bc52.yaml
│   │   │   ├── plan-c2c245e8-08a1-43ab-ab15-1aa9f8a94b5e.yaml
│   │   │   ├── plan-c2e302e3-9560-44aa-a7c7-ce50fc93e916.yaml
│   │   │   ├── plan-c2fbcd47-4978-43f9-8016-d664f761eec4.yaml
│   │   │   ├── plan-c3939bc4-e3e5-4601-baf9-033f5315d3d9.yaml
│   │   │   ├── plan-c3d5ecc6-d6cb-4b1d-8c19-e1a41283efed.yaml
│   │   │   ├── plan-c3eddd01-7730-4966-8829-6549c6781978.yaml
│   │   │   ├── plan-c3fa4cc3-4e33-4a98-8d28-a68b0684e8dd.yaml
│   │   │   ├── plan-c3fe811a-56d0-4d1c-9bf9-574a33106f37.yaml
│   │   │   ├── plan-c4402743-effc-4adf-a006-389bd12695a2.yaml
│   │   │   ├── plan-c467668d-0502-41f9-920e-8a17671bad65.yaml
│   │   │   ├── plan-c5da7edf-a724-4ad3-a448-03abc9b7f498.yaml
│   │   │   ├── plan-c5f8263e-27b3-4381-889a-c64fc7e053b3.yaml
│   │   │   ├── plan-c61d892c-52a0-4ef1-826b-a81b925776f6.yaml
│   │   │   ├── plan-c6ee6c2c-c330-4579-b7f9-01dee647cda3.yaml
│   │   │   ├── plan-c76cdd2a-e8f3-40dc-bba5-9482792a0772.yaml
│   │   │   ├── plan-c76e2998-5860-45e9-959b-f966f633c0ce.yaml
│   │   │   ├── plan-c8093d0e-2ea8-4e14-af0d-3b70f6a00b70.yaml
│   │   │   ├── plan-c83f2ae9-89d2-4f2d-b6e4-f3571492536c.yaml
│   │   │   ├── plan-c970d38c-eee3-455e-ab6b-f46caa999bc2.yaml
│   │   │   ├── plan-c9feaf2e-ecf6-448b-9e7d-25b368e1fe44.yaml
│   │   │   ├── plan-ca789c9b-93ae-448e-953f-9fd574e33226.yaml
│   │   │   ├── plan-cb9d5c1a-cec0-42ea-b847-0b0818480ff0.yaml
│   │   │   ├── plan-cbf54805-d9d3-4df5-87d3-71addf5dfad4.yaml
│   │   │   ├── plan-cc44a49b-0a83-4d1e-b4b7-89ec241b8073.yaml
│   │   │   ├── plan-cc7479a8-2f12-4d3c-9020-1eb4beb8c92d.yaml
│   │   │   ├── plan-cc9af087-7e68-4a4f-988c-f1fac1d5983f.yaml
│   │   │   ├── plan-cd59edc9-0a3c-4a8d-9194-73a07ab319da.yaml
│   │   │   ├── plan-ce54f9d7-2772-4e89-8238-a954d0c0a452.yaml
│   │   │   ├── plan-ce6825a6-a9d5-4f5d-82fd-8cfd2b181bb6.yaml
│   │   │   ├── plan-cf07ea05-84cd-4377-84e6-f7acd43da0ed.yaml
│   │   │   ├── plan-cfceed8e-3f51-4b33-88c0-af37bc48cfb7.yaml
│   │   │   ├── plan-d0485c61-953f-4c1d-a94b-71944d7d8095.yaml
│   │   │   ├── plan-d0d11045-cb99-4436-8ead-fa9edb2113e2.yaml
│   │   │   ├── plan-d195c0a1-db0a-41f6-b9c3-9a28df005189.yaml
│   │   │   ├── plan-d196ae1b-22e8-4880-aa05-c96dd6db48de.yaml
│   │   │   ├── plan-d267d807-5af4-4a75-98d1-2589e73e9658.yaml
│   │   │   ├── plan-d2d7d3ff-b71f-4190-8fce-c4a633900c07.yaml
│   │   │   ├── plan-d391e665-1f2c-4f65-8d25-3a8b6137a46f.yaml
│   │   │   ├── plan-d3b1f55c-84d7-423a-a3ee-f3935db018a0.yaml
│   │   │   ├── plan-d3c006a3-6eea-40bf-ad7e-d3337ef8d374.yaml
│   │   │   ├── plan-d3fce24b-b8f8-4fae-8aa4-37bd092d95a0.yaml
│   │   │   ├── plan-d430a858-c887-4d86-a24f-a41aec607ad8.yaml
│   │   │   ├── plan-d442eed5-49ca-4a1a-acd2-3fc6c77bb682.yaml
│   │   │   ├── plan-d47c84e5-68ba-4718-8b3b-1e98b2ed4edb.yaml
│   │   │   ├── plan-d4eb408f-d4b7-4435-b15d-fb66fbbcedc0.yaml
│   │   │   ├── plan-d55b803d-c772-4f0a-aaba-ec9136aaa709.yaml
│   │   │   ├── plan-d5c794c9-cf1d-4b57-8d36-50b257085629.yaml
│   │   │   ├── plan-d60e41e9-6b5a-4637-84ae-d4946af6999c.yaml
│   │   │   ├── plan-d6be976d-2f15-4d96-b619-fd9e06fd6b65.yaml
│   │   │   ├── plan-d7309940-805b-451a-8eee-819a3362cd11.yaml
│   │   │   ├── plan-d82ab5e8-c6e0-4096-a4a7-f823f8b61186.yaml
│   │   │   ├── plan-d8d5c584-cba2-4a9d-aa56-b9446bf9d7b6.yaml
│   │   │   ├── plan-d9807129-18ba-4d0b-ab0a-3f1a47679ca1.yaml
│   │   │   ├── plan-da24bc1d-4a58-4884-b08d-707d9bc70a49.yaml
│   │   │   ├── plan-da38c3c1-53a8-4ebc-a688-b6916fe4a688.yaml
│   │   │   ├── plan-daaaa7c2-872d-4ecc-afc7-2e0a64701203.yaml
│   │   │   ├── plan-dacc1099-690e-4547-acb4-affa390bab03.yaml
│   │   │   ├── plan-db301414-8069-46d8-bfa4-708f25b3c198.yaml
│   │   │   ├── plan-db304aee-2d45-4929-8fe0-9a4e8c5f596b.yaml
│   │   │   ├── plan-dd4ed3dc-befb-4e01-b30e-8f2a3f831bad.yaml
│   │   │   ├── plan-ddd5f4ee-9e0d-498d-bd14-867e6246bbbb.yaml
│   │   │   ├── plan-de05c1e5-0ca2-4308-b343-1e243ffe1b2b.yaml
│   │   │   ├── plan-df2d3b66-905d-4574-8506-bb39cefb1fd4.yaml
│   │   │   ├── plan-df62035f-c286-4523-bfd2-78ee6cfb74d7.yaml
│   │   │   ├── plan-e086c509-41d6-4984-bd38-10399667b4b9.yaml
│   │   │   ├── plan-e0ad445f-6d8e-4190-bc68-d2b0ef7a1bef.yaml
│   │   │   ├── plan-e0f35a9e-e367-4749-9828-688e37447702.yaml
│   │   │   ├── plan-e13411ec-291e-4588-86e4-b7a7009bf31b.yaml
│   │   │   ├── plan-e177219e-728e-4f30-8a22-07ad1e1773c9.yaml
│   │   │   ├── plan-e241f9c1-03d5-46e8-bbef-17300056a736.yaml
│   │   │   ├── plan-e283c8f9-fa4a-4db2-8551-b46b422524b6.yaml
│   │   │   ├── plan-e2e6df4f-eab9-40d4-9db7-8d2b27f3b0ee.yaml
│   │   │   ├── plan-e2fcf63b-4e77-495e-b687-663fe7508600.yaml
│   │   │   ├── plan-e3857f4a-ee4d-4544-95ff-cf0b510dc153.yaml
│   │   │   ├── plan-e3b1f84f-2fe7-47ef-b6d5-0e7fbf35675e.yaml
│   │   │   ├── plan-e463e919-2967-464e-af7f-1433abab1d05.yaml
│   │   │   ├── plan-e4eb5254-2113-4e8e-be5f-c028960c1f9a.yaml
│   │   │   ├── plan-e5a4156e-48ee-4e13-9457-06719ff15097.yaml
│   │   │   ├── plan-e637e489-f5f8-4ddf-9b1a-4f2ca6063a4e.yaml
│   │   │   ├── plan-e67c3181-c53e-4de1-a2f8-414a2a73f3dd.yaml
│   │   │   ├── plan-e6dfdc4a-5d1f-4388-a465-541e4e30323d.yaml
│   │   │   ├── plan-e731d7c6-f8d2-4921-be06-7f6a74857f7f.yaml
│   │   │   ├── plan-e758c06f-8e42-4f79-862f-8b4d94294685.yaml
│   │   │   ├── plan-e77cd198-328b-4f80-b2a0-c7e68e0ae21b.yaml
│   │   │   ├── plan-e85dc9d0-725c-4f9e-b34d-8fc06881f97d.yaml
│   │   │   ├── plan-e93fac51-c6b4-422b-8611-ed87384bb297.yaml
│   │   │   ├── plan-e94c533c-db8e-4d38-b30b-9a1f6f53f403.yaml
│   │   │   ├── plan-e9b78132-6169-4da8-bf29-7f1f55a8f4a6.yaml
│   │   │   ├── plan-eaca1dbd-06a6-42ca-aa29-f68920dbae3c.yaml
│   │   │   ├── plan-eb38f7b2-a41d-43a5-b554-90696dd9fbbc.yaml
│   │   │   ├── plan-ec2ce5a6-9574-486e-84f9-58a02db348c1.yaml
│   │   │   ├── plan-ec95427e-1c92-4a38-993f-598a347087bc.yaml
│   │   │   ├── plan-ecefa02d-9760-4a7d-9b32-7c67a135dd1c.yaml
│   │   │   ├── plan-ed0ace59-2bd8-4c65-ab55-7f3ab9209c6b.yaml
│   │   │   ├── plan-ed5c9392-a83a-46e4-b380-0da65bb44697.yaml
│   │   │   ├── plan-edf43eed-06b2-4a41-8804-1e3fcf510b44.yaml
│   │   │   ├── plan-ee794c6d-3910-4d8f-bfa5-322f38df2bab.yaml
│   │   │   ├── plan-eeeecab7-27e2-4159-b5d4-7e8a084a20d7.yaml
│   │   │   ├── plan-f008d337-c562-41a5-b05b-b55c9bd4f6a2.yaml
│   │   │   ├── plan-f0b23a21-7f5d-44f8-a513-e0c1634d1935.yaml
│   │   │   ├── plan-f0cc32a8-e914-4b98-ad4e-c54b35766912.yaml
│   │   │   ├── plan-f0d097cd-71ff-49a5-a701-28c4ecfe47be.yaml
│   │   │   ├── plan-f1b51a0f-0433-4954-9a21-352ec5217270.yaml
│   │   │   ├── plan-f1e064e7-4140-4152-960f-2176842299b9.yaml
│   │   │   ├── plan-f1f2e141-42c2-4afe-b908-4ed61352215b.yaml
│   │   │   ├── plan-f27e5e2b-ec8e-43d7-bb64-c56f22851885.yaml
│   │   │   ├── plan-f28dc88f-8e0f-4546-8a31-22d2d02a42c9.yaml
│   │   │   ├── plan-f2c73e16-ed2e-4e74-afdd-077c2752fd3e.yaml
│   │   │   ├── plan-f36f3d17-08db-4d0e-ad5b-e8b0a6243789.yaml
│   │   │   ├── plan-f378dbb5-d423-4323-86a3-dc5a7b2d8b12.yaml
│   │   │   ├── plan-f3917a83-8d4f-4582-a50c-4f62959caea3.yaml
│   │   │   ├── plan-f3a1b666-aae3-4775-82ab-9f8e7e083fc4.yaml
│   │   │   ├── plan-f40b0a52-4699-49a0-9bc9-c15e76af13a8.yaml
│   │   │   ├── plan-f40d170d-8df0-43bc-b454-0c636d96fb4f.yaml
│   │   │   ├── plan-f4727d99-cb05-473d-a529-d1bb9c9d168b.yaml
│   │   │   ├── plan-f48db4db-7632-4d46-a9d7-a0a4c6c561b1.yaml
│   │   │   ├── plan-f4e4f66f-ba60-4b3c-a7fa-3730c1d56993.yaml
│   │   │   ├── plan-f59d1042-53ff-4b5a-9aac-1cf4e9099ca4.yaml
│   │   │   ├── plan-f5d83198-9ef7-4380-939d-0e7951c4feb4.yaml
│   │   │   ├── plan-f605df78-270f-45dd-9cef-eecaa7a73380.yaml
│   │   │   ├── plan-f652201a-db42-4bd4-9436-ae41e73fd828.yaml
│   │   │   ├── plan-f7923267-faf3-4f6b-9fa4-9fb034ffa3aa.yaml
│   │   │   ├── plan-f7add2eb-9495-4c7b-aea8-7d81dfcbdbf3.yaml
│   │   │   ├── plan-f7dd0c8a-3073-46ad-9a18-4697bfbff360.yaml
│   │   │   ├── plan-f83147b0-77c7-46a8-b777-1d2b0e28095d.yaml
│   │   │   ├── plan-f88d3339-4844-4253-8b6a-7ab66d5fdcae.yaml
│   │   │   ├── plan-f8d94736-2b1a-4ff3-ac32-532d53df8c73.yaml
│   │   │   ├── plan-fa1ee8e0-701d-41a2-8452-c63992c4bb06.yaml
│   │   │   ├── plan-fc534554-4b45-431b-b200-23567a630f6e.yaml
│   │   │   ├── plan-fd563fa5-04cf-44cb-8883-b771bd7dc3fa.yaml
│   │   │   ├── plan-fe309a00-21b3-489a-a6fc-5ef545d03b13.yaml
│   │   │   ├── plan-fe390c9c-4d77-437e-9640-751ed2174309.yaml
│   │   │   ├── plan-fe7035ab-e82b-4bd8-992f-6cf628de9235.yaml
│   │   │   ├── plan-feea848b-2ade-4a42-886c-fdc15e6ebc1d.yaml
│   │   │   ├── plan-ff2ec8e3-1ad0-433b-8cf7-df2cd796226f.yaml
│   │   │   └── plan-ff669ae7-9ed2-4151-a236-d95ba4fce270.yaml
│   │   ├── pricing.yaml
│   │   ├── rbac
│   │   │   ├── field-level.yaml
│   │   │   ├── permissions.yaml
│   │   │   └── roles.yaml
│   │   ├── retention
│   │   │   └── policies.yaml
│   │   ├── security
│   │   │   └── dlp-policies.yaml
│   │   ├── signing
│   │   │   └── dev_signing_public.pem
│   │   ├── tenants
│   │   │   ├── README.md
│   │   │   └── default.yaml
│   │   └── vector_store.yaml
│   ├── docker
│   │   ├── docker-compose-demo.yml
│   │   ├── docker-compose.test.yml
│   │   └── docker-compose.yml
│   ├── infra
│   │   ├── README.md
│   │   ├── kubernetes
│   │   │   ├── README.md
│   │   │   ├── db-backup-cronjob.yaml
│   │   │   ├── db-backup-scripts.yaml
│   │   │   ├── db-backup-secret.yaml
│   │   │   ├── deployment.yaml
│   │   │   ├── helm-charts
│   │   │   │   ├── README.md
│   │   │   │   ├── observability
│   │   │   │   │   ├── Chart.yaml
│   │   │   │   │   ├── templates
│   │   │   │   │   │   ├── configmap.yaml
│   │   │   │   │   │   ├── deployment.yaml
│   │   │   │   │   │   └── service.yaml
│   │   │   │   │   └── values.yaml
│   │   │   │   └── ppm-platform
│   │   │   │       ├── Chart.yaml
│   │   │   │       ├── values-template.yaml
│   │   │   │       └── values.yaml
│   │   │   ├── manifests
│   │   │   │   ├── README.md
│   │   │   │   ├── backup-jobs.yaml
│   │   │   │   ├── cert-manager-issuer.yaml
│   │   │   │   ├── istio-mtls.yaml
│   │   │   │   ├── namespace.yaml
│   │   │   │   ├── network-policies.yaml
│   │   │   │   ├── pod-security.yaml
│   │   │   │   └── resource-quotas.yaml
│   │   │   ├── secret-provider-class.yaml
│   │   │   ├── secret-rotation-cronjob.yaml
│   │   │   ├── secret-rotation-scripts.yaml
│   │   │   ├── secrets.yaml.example
│   │   │   └── service-account.yaml
│   │   ├── observability
│   │   │   ├── README.md
│   │   │   ├── alerts
│   │   │   │   ├── README.md
│   │   │   │   └── ppm-alerts.yaml
│   │   │   ├── dashboards
│   │   │   │   ├── README.md
│   │   │   │   ├── ppm-error-budget.json
│   │   │   │   ├── ppm-platform.json
│   │   │   │   └── ppm-slo.json
│   │   │   ├── otel
│   │   │   │   ├── README.md
│   │   │   │   ├── collector.yaml
│   │   │   │   └── helm
│   │   │   │       ├── Chart.yaml
│   │   │   │       ├── templates
│   │   │   │       │   ├── configmap.yaml
│   │   │   │       │   ├── deployment.yaml
│   │   │   │       │   ├── secretproviderclass.yaml
│   │   │   │       │   ├── service.yaml
│   │   │   │       │   └── serviceaccount.yaml
│   │   │   │       └── values.yaml
│   │   │   └── slo
│   │   │       └── ppm-slo.yaml
│   │   ├── policies
│   │   │   ├── README.md
│   │   │   ├── dlp
│   │   │   │   ├── README.md
│   │   │   │   └── bundles
│   │   │   │       ├── credentials.rego
│   │   │   │       ├── default-dlp-policy-bundle.yaml
│   │   │   │       └── pii.rego
│   │   │   ├── network
│   │   │   │   ├── README.md
│   │   │   │   └── bundles
│   │   │   │       └── default-network-policy-bundle.yaml
│   │   │   ├── schema
│   │   │   │   └── policy-bundle.schema.json
│   │   │   └── security
│   │   │       ├── README.md
│   │   │       └── bundles
│   │   │           └── default-security-policy-bundle.yaml
│   │   ├── tenancy
│   │   │   ├── deprovision_tenant.sh
│   │   │   └── provision_tenant.sh
│   │   └── terraform
│   │       ├── README.md
│   │       ├── dr
│   │       │   ├── README.md
│   │       │   ├── failover.sh
│   │       │   └── restore.sh
│   │       ├── envs
│   │       │   ├── README.md
│   │       │   ├── demo
│   │       │   │   ├── main.tf
│   │       │   │   ├── outputs.tf
│   │       │   │   ├── terraform.tfvars.example
│   │       │   │   ├── variables.tf
│   │       │   │   └── versions.tf
│   │       │   ├── dev
│   │       │   │   ├── README.md
│   │       │   │   ├── main.tf
│   │       │   │   └── terraform.tfvars
│   │       │   ├── prod
│   │       │   │   ├── README.md
│   │       │   │   ├── backend.tfvars
│   │       │   │   └── terraform.tfvars
│   │       │   ├── stage
│   │       │   │   ├── README.md
│   │       │   │   └── terraform.tfvars
│   │       │   └── test
│   │       │       └── README.md
│   │       ├── main.tf
│   │       └── modules
│   │           ├── README.md
│   │           ├── aks
│   │           │   ├── main.tf
│   │           │   ├── outputs.tf
│   │           │   └── variables.tf
│   │           ├── cost-analysis
│   │           │   ├── README.md
│   │           │   ├── main.tf
│   │           │   ├── outputs.tf
│   │           │   └── variables.tf
│   │           ├── keyvault
│   │           │   ├── README.md
│   │           │   ├── main.tf
│   │           │   ├── outputs.tf
│   │           │   └── variables.tf
│   │           ├── monitoring
│   │           │   ├── main.tf
│   │           │   ├── outputs.tf
│   │           │   └── variables.tf
│   │           ├── networking
│   │           │   ├── main.tf
│   │           │   ├── outputs.tf
│   │           │   └── variables.tf
│   │           └── postgresql
│   │               ├── README.md
│   │               ├── main.tf
│   │               ├── outputs.tf
│   │               └── variables.tf
│   ├── requirements
│   │   ├── requirements-demo.txt
│   │   ├── requirements-dev.in
│   │   ├── requirements-dev.txt
│   │   ├── requirements.in
│   │   └── requirements.txt
│   ├── schemas
│   │   ├── README.md
│   │   ├── approval_policies.schema.json
│   │   ├── business-case-settings.schema.json
│   │   ├── intent-router.schema.json
│   │   └── intent-routing.schema.json
│   ├── scripts
│   │   ├── README.md
│   │   ├── build_template_dependency_map.py
│   │   ├── check-docs-migration-guard.py
│   │   ├── check-legacy-ui-references.py
│   │   ├── check-links.py
│   │   ├── check-migrations.py
│   │   ├── check-placeholders.py
│   │   ├── check-schema-example-updates.py
│   │   ├── check-templates.py
│   │   ├── check-ui-emojis.sh
│   │   ├── check-ui-icons.sh
│   │   ├── check_api_versioning.py
│   │   ├── check_placeholders.py
│   │   ├── compare_benchmarks.py
│   │   ├── connector-certification.py
│   │   ├── db_backup.sh
│   │   ├── demo_preflight.py
│   │   ├── export_audit_evidence.py
│   │   ├── fix_docs_formatting.py
│   │   ├── full_platform_demo_run.py
│   │   ├── full_platform_demo_smoke.py
│   │   ├── generate-sbom.py
│   │   ├── generate_agent_metadata.py
│   │   ├── generate_demo_data.py
│   │   ├── init-db.sql
│   │   ├── load-test.py
│   │   ├── load_demo_data.py
│   │   ├── quickstart_smoke.py
│   │   ├── reset_demo_data.sh
│   │   ├── rotate_secrets.sh
│   │   ├── schema_registry.py
│   │   ├── schema_tool.py
│   │   ├── sign-artifact.py
│   │   ├── smoke_test_staging.py
│   │   ├── test_migration_rollback.py
│   │   ├── ui_coverage_check.py
│   │   ├── validate-analytics-jobs.py
│   │   ├── validate-connector-sandbox.py
│   │   ├── validate-examples.py
│   │   ├── validate-github-workflows.py
│   │   ├── validate-helm-charts.py
│   │   ├── validate-intent-routing.py
│   │   ├── validate-manifests.py
│   │   ├── validate-mcp-manifests.py
│   │   ├── validate-policies.py
│   │   ├── validate-schemas.py
│   │   ├── validate-workflows.py
│   │   ├── validate_config.py
│   │   ├── validate_demo_fixtures.py
│   │   ├── verify-production-readiness.sh
│   │   ├── verify-signature.py
│   │   └── verify_manifest.py
│   ├── smoke_workspace_wiring.py
│   └── tools
│       ├── README.md
│       ├── __init__.py
│       ├── agent_runner.py
│       ├── agent_runner_core.py
│       ├── check_config_parity.py
│       ├── check_connector_maturity.py
│       ├── check_observability_compliance.py
│       ├── check_root_layout.py
│       ├── check_secret_source_policy.py
│       ├── check_security_middleware.py
│       ├── codegen
│       │   ├── README.md
│       │   ├── __init__.py
│       │   ├── codegen_config.yaml
│       │   ├── generate_docs.py
│       │   └── run.py
│       ├── collect_maturity_score.py
│       ├── component_runner.py
│       ├── config_validator.py
│       ├── connector_runner.py
│       ├── env_validate.py
│       ├── format
│       │   ├── README.md
│       │   ├── __init__.py
│       │   ├── format_config.yaml
│       │   └── run.py
│       ├── lint
│       │   ├── README.md
│       │   ├── __init__.py
│       │   ├── lint_config.yaml
│       │   └── run.py
│       ├── load_testing
│       │   ├── __init__.py
│       │   └── runner.py
│       ├── local-dev
│       │   ├── README.md
│       │   ├── dev_down.sh
│       │   ├── dev_up.sh
│       │   └── docker-compose.override.example.yml
│       ├── observability_compliance_checks.py
│       ├── release_gate.py
│       ├── run_bandit.py
│       ├── run_dast.py
│       ├── runtime_paths.py
│       └── security_baseline_checks.py
├── packages
│   ├── README.md
│   ├── agent-sdk
│   │   ├── README.md
│   │   └── src
│   │       ├── __init__.py
│   │       ├── context.py
│   │       ├── custom_agent.py
│   │       ├── manifest.py
│   │       ├── sandbox.py
│   │       └── testing.py
│   ├── canvas-engine
│   │   ├── .eslintrc.cjs
│   │   ├── README.md
│   │   ├── docs
│   │   │   └── document-canvas-editor-migration.md
│   │   ├── package.json
│   │   ├── src
│   │   │   ├── components
│   │   │   │   ├── ApprovalCanvas
│   │   │   │   │   ├── ApprovalCanvas.module.css
│   │   │   │   │   ├── ApprovalCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── BacklogCanvas
│   │   │   │   │   ├── BacklogCanvas.module.css
│   │   │   │   │   ├── BacklogCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── BoardCanvas
│   │   │   │   │   ├── BoardCanvas.module.css
│   │   │   │   │   ├── BoardCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── CanvasHost
│   │   │   │   │   ├── CanvasHost.module.css
│   │   │   │   │   ├── CanvasHost.tsx
│   │   │   │   │   ├── TabBar.module.css
│   │   │   │   │   ├── TabBar.tsx
│   │   │   │   │   ├── Toolbar.module.css
│   │   │   │   │   ├── Toolbar.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── DashboardCanvas
│   │   │   │   │   ├── DashboardCanvas.module.css
│   │   │   │   │   ├── DashboardCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── DependencyMapCanvas
│   │   │   │   │   ├── DependencyMapCanvas.module.css
│   │   │   │   │   ├── DependencyMapCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── DocumentCanvas
│   │   │   │   │   ├── DocumentCanvas.editor.test.tsx
│   │   │   │   │   ├── DocumentCanvas.module.css
│   │   │   │   │   ├── DocumentCanvas.security.test.tsx
│   │   │   │   │   ├── DocumentCanvas.tsx
│   │   │   │   │   ├── index.ts
│   │   │   │   │   └── richTextAdapter.ts
│   │   │   │   ├── FinancialCanvas
│   │   │   │   │   ├── FinancialCanvas.module.css
│   │   │   │   │   ├── FinancialCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── GanttCanvas
│   │   │   │   │   ├── GanttCanvas.module.css
│   │   │   │   │   ├── GanttCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── GridCanvas
│   │   │   │   │   ├── GridCanvas.module.css
│   │   │   │   │   ├── GridCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── RoadmapCanvas
│   │   │   │   │   ├── RoadmapCanvas.module.css
│   │   │   │   │   ├── RoadmapCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── SpreadsheetCanvas
│   │   │   │   │   ├── SpreadsheetCanvas.module.css
│   │   │   │   │   ├── SpreadsheetCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── StructuredTreeCanvas
│   │   │   │   │   ├── StructuredTreeCanvas.module.css
│   │   │   │   │   ├── StructuredTreeCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── TimelineCanvas
│   │   │   │   │   ├── TimelineCanvas.module.css
│   │   │   │   │   ├── TimelineCanvas.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   └── index.ts
│   │   │   ├── global.d.ts
│   │   │   ├── hooks
│   │   │   │   ├── index.ts
│   │   │   │   └── useCanvasHost.ts
│   │   │   ├── index.ts
│   │   │   ├── security
│   │   │   │   ├── SANITIZATION_POLICY.md
│   │   │   │   ├── htmlSanitizer.test.ts
│   │   │   │   ├── htmlSanitizer.ts
│   │   │   │   └── index.ts
│   │   │   ├── test
│   │   │   │   └── setup.ts
│   │   │   └── types
│   │   │       ├── artifact.test.ts
│   │   │       ├── artifact.ts
│   │   │       ├── canvas.test.ts
│   │   │       ├── canvas.ts
│   │   │       └── index.ts
│   │   ├── tsconfig.json
│   │   └── vitest.config.ts
│   ├── common
│   │   ├── README.md
│   │   └── src
│   │       └── common
│   │           ├── __init__.py
│   │           ├── bootstrap.py
│   │           ├── env_validation.py
│   │           ├── exceptions.py
│   │           └── resilience.py
│   ├── connectors
│   │   ├── __init__.py
│   │   └── base_connector.py
│   ├── contracts
│   │   ├── README.md
│   │   └── src
│   │       ├── api
│   │       │   ├── __init__.py
│   │       │   └── governance.py
│   │       ├── auth
│   │       │   └── __init__.py
│   │       ├── data
│   │       │   └── __init__.py
│   │       ├── events
│   │       │   ├── __init__.py
│   │       │   └── definitions.py
│   │       └── models
│   │           └── __init__.py
│   ├── crypto
│   │   ├── README.md
│   │   └── src
│   │       └── crypto
│   │           ├── __init__.py
│   │           ├── encryption.py
│   │           ├── hashing.py
│   │           ├── key_derivation.py
│   │           └── signatures.py
│   ├── data-quality
│   │   ├── README.md
│   │   └── src
│   │       └── data_quality
│   │           ├── __init__.py
│   │           ├── helpers.py
│   │           ├── remediation.py
│   │           ├── rules.py
│   │           └── schema_validation.py
│   ├── design-tokens
│   │   ├── README.md
│   │   ├── package.json
│   │   ├── tokens.css
│   │   ├── tokens.json
│   │   └── tokens.ts
│   ├── event-bus
│   │   ├── README.md
│   │   └── src
│   │       └── event_bus
│   │           ├── __init__.py
│   │           ├── models.py
│   │           └── service_bus.py
│   ├── feature-flags
│   │   ├── README.md
│   │   └── src
│   │       └── feature_flags
│   │           ├── __init__.py
│   │           └── manager.py
│   ├── feedback
│   │   ├── __init__.py
│   │   └── feedback_models.py
│   ├── llm
│   │   ├── README.md
│   │   ├── prompt_sanitizer.py
│   │   ├── src
│   │   │   ├── llm
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py
│   │   │   │   ├── router.py
│   │   │   │   └── types.py
│   │   │   ├── model_registry.py
│   │   │   ├── providers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── anthropic_provider.py
│   │   │   │   ├── azure_openai_provider.py
│   │   │   │   ├── google_provider.py
│   │   │   │   └── openai_provider.py
│   │   │   └── router.py
│   │   └── tests
│   │       ├── test_azure_openai_provider.py
│   │       ├── test_gateway.py
│   │       └── test_model_registry_router.py
│   ├── memory_client.py
│   ├── methodology-engine
│   │   ├── README.md
│   │   └── src
│   │       ├── __init__.py
│   │       └── methodology_engine.py
│   ├── observability
│   │   ├── README.md
│   │   └── src
│   │       ├── observability
│   │       │   ├── __init__.py
│   │       │   ├── logging.py
│   │       │   ├── metrics.py
│   │       │   ├── telemetry.py
│   │       │   └── tracing.py
│   │       └── opentelemetry
│   │           ├── __init__.py
│   │           ├── _logs.py
│   │           ├── exporter
│   │           │   ├── __init__.py
│   │           │   └── otlp
│   │           │       ├── __init__.py
│   │           │       └── proto
│   │           │           ├── __init__.py
│   │           │           └── http
│   │           │               ├── __init__.py
│   │           │               ├── _log_exporter.py
│   │           │               ├── metric_exporter.py
│   │           │               └── trace_exporter.py
│   │           ├── metrics.py
│   │           ├── propagate.py
│   │           ├── sdk
│   │           │   ├── __init__.py
│   │           │   ├── _logs
│   │           │   │   ├── __init__.py
│   │           │   │   └── export
│   │           │   │       └── __init__.py
│   │           │   ├── metrics
│   │           │   │   ├── __init__.py
│   │           │   │   └── export
│   │           │   │       └── __init__.py
│   │           │   ├── resources.py
│   │           │   └── trace
│   │           │       ├── __init__.py
│   │           │       └── export
│   │           │           └── __init__.py
│   │           └── trace
│   │               ├── __init__.py
│   │               └── propagation
│   │                   ├── __init__.py
│   │                   └── tracecontext.py
│   ├── policy
│   │   ├── README.md
│   │   └── src
│   │       ├── __init__.py
│   │       └── policy.py
│   ├── security
│   │   ├── README.md
│   │   └── src
│   │       └── security
│   │           ├── __init__.py
│   │           ├── api_governance.py
│   │           ├── audit_log.py
│   │           ├── auth.py
│   │           ├── config.py
│   │           ├── crypto.py
│   │           ├── dlp.py
│   │           ├── errors.py
│   │           ├── headers.py
│   │           ├── iam.py
│   │           ├── keyvault.py
│   │           ├── lineage.py
│   │           ├── prompt_safety.py
│   │           └── secrets.py
│   ├── testing
│   │   ├── README.md
│   │   └── src
│   │       └── testing
│   │           ├── __init__.py
│   │           ├── assertions.py
│   │           ├── fixtures.py
│   │           └── mock_builders.py
│   ├── ui-kit
│   │   ├── README.md
│   │   ├── design-system
│   │   │   ├── README.md
│   │   │   ├── icons
│   │   │   │   ├── README.md
│   │   │   │   └── icon-map.json
│   │   │   ├── stories
│   │   │   │   ├── Button.stories.tsx
│   │   │   │   ├── EmptyState.stories.tsx
│   │   │   │   └── TokenPalette.stories.tsx
│   │   │   └── tokens
│   │   │       ├── design-system-tokens.json
│   │   │       ├── tokens.css
│   │   │       └── tokens.ts
│   │   ├── package.json
│   │   └── src
│   │       └── __init__.py
│   ├── vector_store
│   │   ├── __init__.py
│   │   └── faiss_store.py
│   ├── version.py
│   └── workflow
│       ├── README.md
│       └── src
│           └── workflow
│               ├── __init__.py
│               ├── aggregation.py
│               ├── celery_app.py
│               ├── dispatcher.py
│               ├── executor.py
│               └── tasks.py
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── pyproject.toml
├── requirements.txt
├── services
│   ├── README.md
│   ├── __init__.py
│   ├── agent-config
│   │   ├── README.md
│   │   └── src
│   │       ├── __init__.py
│   │       ├── agent_config_service.py
│   │       └── main.py
│   ├── agent-runtime
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── main.py
│   │   ├── src
│   │   │   ├── README.md
│   │   │   ├── config
│   │   │   │   └── intent-routing.yaml
│   │   │   ├── main.py
│   │   │   └── runtime.py
│   │   └── tests
│   │       ├── test_agent_runtime_service.py
│   │       ├── test_connector_action_client.py
│   │       └── test_runtime_event_bus.py
│   ├── audit-log
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── contracts
│   │   │   └── openapi.yaml
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   ├── secretproviderclass.yaml
│   │   │   │   ├── service.yaml
│   │   │   │   └── serviceaccount.yaml
│   │   │   └── values.yaml
│   │   ├── main.py
│   │   ├── src
│   │   │   ├── audit_storage.py
│   │   │   ├── main.py
│   │   │   └── retention_job.py
│   │   ├── storage
│   │   │   └── README.md
│   │   └── tests
│   │       ├── test_audit_log.py
│   │       └── test_retention_job.py
│   ├── auth-service
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── main.py
│   │   ├── src
│   │   │   ├── auth.py
│   │   │   └── main.py
│   │   └── tests
│   │       └── test_auth_service.py
│   ├── data-lineage-service
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   ├── service.yaml
│   │   │   │   └── serviceaccount.yaml
│   │   │   └── values.yaml
│   │   ├── main.py
│   │   ├── src
│   │   │   ├── main.py
│   │   │   ├── quality.py
│   │   │   ├── retention_scheduler.py
│   │   │   └── storage.py
│   │   └── tests
│   │       └── test_lineage_service.py
│   ├── data-service
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   ├── service.yaml
│   │   │   │   └── serviceaccount.yaml
│   │   │   └── values.yaml
│   │   ├── main.py
│   │   ├── src
│   │   │   ├── main.py
│   │   │   ├── retention_scheduler.py
│   │   │   ├── schema_compatibility.py
│   │   │   └── storage.py
│   │   └── tests
│   │       ├── test_data_service.py
│   │       └── test_schema_governance.py
│   ├── data-sync-service
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── contracts
│   │   │   └── openapi.yaml
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── main.py
│   │   ├── rules
│   │   │   ├── README.md
│   │   │   └── default-sync.yaml
│   │   ├── src
│   │   │   ├── conflict_store.py
│   │   │   ├── data_sync_queue.py
│   │   │   ├── data_sync_status.py
│   │   │   ├── jira_client.py
│   │   │   ├── jira_tasks_sync.py
│   │   │   ├── lineage_client.py
│   │   │   ├── main.py
│   │   │   ├── propagation.py
│   │   │   ├── sync_log_store.py
│   │   │   ├── sync_registry.py
│   │   │   └── task_store.py
│   │   └── tests
│   │       ├── test_data_sync.py
│   │       └── test_data_sync_service.py
│   ├── feedback_service.py
│   ├── identity-access
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── contracts
│   │   │   └── openapi.yaml
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── main.py
│   │   ├── src
│   │   │   ├── main.py
│   │   │   ├── saml.py
│   │   │   ├── scim_models.py
│   │   │   └── scim_store.py
│   │   ├── storage
│   │   │   └── scim.db
│   │   └── tests
│   │       ├── test_identity_access.py
│   │       └── test_scim.py
│   ├── memory_service
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── memory_service.py
│   ├── notification-service
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── contracts
│   │   │   └── openapi.yaml
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── main.py
│   │   ├── src
│   │   │   └── main.py
│   │   ├── templates
│   │   │   ├── README.md
│   │   │   ├── agent-run-status.txt
│   │   │   ├── intake-triage-summary.txt
│   │   │   ├── portfolio-intake.txt
│   │   │   └── welcome.txt
│   │   └── tests
│   │       └── test_notification_service.py
│   ├── policy-engine
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── contracts
│   │   │   └── openapi.yaml
│   │   ├── helm
│   │   │   ├── Chart.yaml
│   │   │   ├── README.md
│   │   │   ├── templates
│   │   │   │   ├── _helpers.tpl
│   │   │   │   ├── certificate.yaml
│   │   │   │   ├── configmap.yaml
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── hpa.yaml
│   │   │   │   ├── ingress.yaml
│   │   │   │   ├── pdb.yaml
│   │   │   │   └── service.yaml
│   │   │   └── values.yaml
│   │   ├── main.py
│   │   ├── policies
│   │   │   ├── README.md
│   │   │   ├── bundles
│   │   │   │   └── default-policy-bundle.yaml
│   │   │   └── schema
│   │   │       └── policy-bundle.schema.json
│   │   ├── src
│   │   │   ├── main.py
│   │   │   └── policy_config.py
│   │   └── tests
│   │       └── test_policy_engine.py
│   ├── realtime-coedit-service
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── main.py
│   │   ├── src
│   │   │   ├── annotation_routes.py
│   │   │   ├── annotations.py
│   │   │   ├── main.py
│   │   │   └── storage.py
│   │   └── tests
│   │       └── test_realtime_coedit_service.py
│   ├── scope_baseline
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── scope_baseline_service.py
│   └── telemetry-service
│       ├── .dockerignore
│       ├── Dockerfile
│       ├── README.md
│       ├── contracts
│       │   └── openapi.yaml
│       ├── helm
│       │   ├── Chart.yaml
│       │   ├── README.md
│       │   ├── files
│       │   │   └── collector.yaml
│       │   ├── templates
│       │   │   ├── _helpers.tpl
│       │   │   ├── certificate.yaml
│       │   │   ├── collector-config.yaml
│       │   │   ├── configmap.yaml
│       │   │   ├── deployment.yaml
│       │   │   ├── hpa.yaml
│       │   │   ├── ingress.yaml
│       │   │   ├── pdb.yaml
│       │   │   └── service.yaml
│       │   └── values.yaml
│       ├── main.py
│       ├── pipelines
│       │   └── README.md
│       ├── src
│       │   ├── main.py
│       │   └── otel.py
│       └── tests
│           ├── test_telemetry.py
│           └── test_telemetry_service.py
├── tests
│   ├── README.md
│   ├── agents
│   │   ├── test_analytics_insights_agent.py
│   │   ├── test_approval_workflow_agent.py
│   │   ├── test_business_case.py
│   │   ├── test_business_case_investment_agent.py
│   │   ├── test_change_configuration_agent.py
│   │   ├── test_compliance_regulatory_agent.py
│   │   ├── test_continuous_improvement.py
│   │   ├── test_data_sync_agent.py
│   │   ├── test_delegation.py
│   │   ├── test_demand_intake_agent.py
│   │   ├── test_demo_mode.py
│   │   ├── test_distributed_workflow_engine.py
│   │   ├── test_financial_management_agent.py
│   │   ├── test_intent_router.py
│   │   ├── test_intent_router_agent.py
│   │   ├── test_knowledge_document.py
│   │   ├── test_knowledge_management_agent.py
│   │   ├── test_portfolio_strategy_agent.py
│   │   ├── test_process_mining_agent.py
│   │   ├── test_program_management_agent.py
│   │   ├── test_project_definition.py
│   │   ├── test_project_definition_agent.py
│   │   ├── test_project_lifecycle_agent.py
│   │   ├── test_quality_management_agent.py
│   │   ├── test_release_deployment_agent.py
│   │   ├── test_resource_capacity_agent.py
│   │   ├── test_response_orchestration.py
│   │   ├── test_response_orchestration_agent.py
│   │   ├── test_risk_adjusted_planning.py
│   │   ├── test_risk_management_agent.py
│   │   ├── test_schedule_planning_agent.py
│   │   ├── test_stakeholder_comm_agent.py
│   │   ├── test_stakeholder_communications_agent.py
│   │   ├── test_system_health_agent.py
│   │   ├── test_vendor_procurement_agent.py
│   │   ├── test_web_search.py
│   │   └── test_workflow_engine_agent.py
│   ├── apps
│   │   ├── test_agents_route_errors.py
│   │   ├── test_api_gateway_health.py
│   │   ├── test_certifications_api.py
│   │   ├── test_document_session_store_concurrency.py
│   │   ├── test_methodology_relationship_defaults.py
│   │   ├── test_orchestration_service.py
│   │   ├── test_web_governance_api.py
│   │   └── test_web_legacy_route_redirects.py
│   ├── config
│   │   ├── test_config_validator.py
│   │   └── test_connector_maturity_policy.py
│   ├── conftest.py
│   ├── connectors
│   │   ├── __init__.py
│   │   ├── connector_test_harness.py
│   │   ├── test_base_connector.py
│   │   ├── test_connector_implementations.py
│   │   ├── test_connector_sync_routes.py
│   │   ├── test_connector_webhooks.py
│   │   ├── test_iot_connector.py
│   │   ├── test_mcp_client.py
│   │   ├── test_priority_connector_harness.py
│   │   └── test_regulatory_compliance_connector.py
│   ├── contract
│   │   ├── README.md
│   │   ├── api-gateway-openapi.json
│   │   ├── test_api_contract.py
│   │   └── test_service_api_governance.py
│   ├── data
│   │   └── test_demo_data.py
│   ├── demo
│   │   ├── test_demo_fixtures_present.py
│   │   └── test_ui_data_completeness.py
│   ├── docs
│   │   └── test_realtime_coedit.py
│   ├── e2e
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── test_acceptance_scenarios.py
│   │   ├── test_connector_webhooks.py
│   │   ├── test_user_journey.py
│   │   ├── test_web_canvas_flow.py
│   │   └── test_web_login.py
│   ├── feedback
│   │   └── test_feedback.py
│   ├── helpers
│   │   └── service_bus.py
│   ├── integration
│   │   ├── README.md
│   │   ├── conftest.py
│   │   ├── connectors
│   │   │   ├── test_azure_devops_connector.py
│   │   │   ├── test_jira_connector.py
│   │   │   ├── test_planview_connector.py
│   │   │   ├── test_servicenow_connector.py
│   │   │   └── test_sync_job.py
│   │   ├── test_ai_models.py
│   │   ├── test_analytics.py
│   │   ├── test_analytics_kpi_engine.py
│   │   ├── test_circuit_breaker.py
│   │   ├── test_connector_framework.py
│   │   ├── test_data_lineage_service.py
│   │   ├── test_data_migrations.py
│   │   ├── test_data_service_clients.py
│   │   ├── test_end_to_end_workflow.py
│   │   ├── test_event_bus.py
│   │   ├── test_mcp_connector_routing.py
│   │   ├── test_mcp_sync_flows.py
│   │   ├── test_mock_connectors.py
│   │   ├── test_multi_agent_flows.py
│   │   ├── test_orchestration_service_orchestrator_persistence_suite.py
│   │   ├── test_orchestration_workflow_integration.py
│   │   ├── test_orchestrator_persistence.py
│   │   ├── test_orchestrator_readiness_integration.py
│   │   ├── test_persistence.py
│   │   ├── test_plan_approval.py
│   │   ├── test_portfolio_program_agent_integration.py
│   │   ├── test_service_bus_event_bus_integration.py
│   │   ├── test_workflow_agent_execution.py
│   │   ├── test_workflow_celery_execution.py
│   │   ├── test_workflow_compensation.py
│   │   ├── test_workflow_definition_validation.py
│   │   ├── test_workflow_definitions_suite.py
│   │   ├── test_workflow_engine_runtime.py
│   │   ├── test_workflow_parallel_and_loop.py
│   │   ├── test_workflow_retry.py
│   │   ├── test_workflow_runtime_suite.py
│   │   └── test_workflow_storage_suite.py
│   ├── llm
│   │   ├── test_prompt_sanitizer.py
│   │   └── test_prompt_sanitizer_enhanced.py
│   ├── load
│   │   ├── README.md
│   │   ├── multi_agent_scenarios.py
│   │   ├── sla_targets.json
│   │   ├── test_connectors_latency_sla.py
│   │   └── test_load_sla.py
│   ├── memory
│   │   └── test_memory_service.py
│   ├── notification
│   │   └── test_localization.py
│   ├── observability
│   │   ├── test_business_workflow_metrics.py
│   │   ├── test_correlation.py
│   │   ├── test_cost_tracking.py
│   │   └── test_observability_compliance.py
│   ├── ops
│   │   ├── fixtures
│   │   │   └── check_placeholders
│   │   │       ├── invalid
│   │   │       │   ├── apps
│   │   │       │   │   └── demo-app
│   │   │       │   │       └── README.md
│   │   │       │   └── services
│   │   │       │       └── demo-service
│   │   │       │           └── README.md
│   │   │       └── valid
│   │   │           ├── apps
│   │   │           │   └── demo-app
│   │   │           │       └── README.md
│   │   │           └── services
│   │   │               └── demo-service
│   │   │                   └── README.md
│   │   ├── test_check_placeholders.py
│   │   ├── test_observability_compliance.py
│   │   └── tools
│   │       └── test_check_root_layout.py
│   ├── orchestrator
│   │   └── test_human_review.py
│   ├── packages
│   │   ├── common
│   │   │   ├── test_exceptions_package.py
│   │   │   └── test_resilience_package.py
│   │   └── security
│   │       ├── conftest.py
│   │       ├── test_auth_package.py
│   │       ├── test_crypto_package.py
│   │       ├── test_dlp_package.py
│   │       └── test_prompt_safety_package.py
│   ├── performance
│   │   ├── README.md
│   │   ├── baselines.json
│   │   ├── config.yaml
│   │   ├── locustfile.py
│   │   ├── mock_server.py
│   │   ├── quick_config.yaml
│   │   ├── report_summary.py
│   │   ├── run_locust.py
│   │   └── test_event_bus_load.py
│   ├── policies
│   │   ├── test_dlp_rego.py
│   │   ├── test_rbac_abac_policies.py
│   │   └── validate_policies_test.py
│   ├── prompts
│   │   └── test_prompt_registry.py
│   ├── runtime
│   │   ├── test_eval_harness.py
│   │   ├── test_orchestrator.py
│   │   ├── test_service_bus_event_bus.py
│   │   └── test_template_workflow.py
│   ├── security
│   │   ├── README.md
│   │   ├── test_agent_config_rbac.py
│   │   ├── test_auth_cache.py
│   │   ├── test_auth_rbac.py
│   │   ├── test_compliance.py
│   │   ├── test_dast_integration.py
│   │   ├── test_dlp_and_encryption.py
│   │   ├── test_downstream_auth.py
│   │   ├── test_field_level_masking.py
│   │   ├── test_field_masking.py
│   │   ├── test_jwt_delegation.py
│   │   ├── test_key_rotation.py
│   │   ├── test_lineage_masking.py
│   │   ├── test_oidc_cache.py
│   │   ├── test_policy_engine_integration.py
│   │   ├── test_rate_limit_cors.py
│   │   ├── test_retention_config.py
│   │   ├── test_secret_resolution.py
│   │   ├── test_secret_resolution_and_rbac.py
│   │   ├── test_security_baseline_compliance.py
│   │   └── test_security_headers.py
│   ├── services
│   │   ├── test_agent_config_service.py
│   │   └── test_scope_baseline_service.py
│   ├── test_api.py
│   ├── test_approval_workflow.py
│   ├── test_artifact_validation.py
│   ├── test_backup_runbook.py
│   ├── test_base_agent.py
│   ├── test_data_quality_pipeline.py
│   ├── test_data_quality_rules.py
│   ├── test_event_contracts.py
│   ├── test_intent_router.py
│   ├── test_mcp_connector_exception_handling.py
│   ├── test_operational_runbooks.py
│   ├── test_resilience_middleware.py
│   ├── test_schema_registry_tooling.py
│   ├── test_schema_validation.py
│   ├── test_security_review_fixes.py
│   ├── tools
│   │   ├── test_agent_metadata_generation.py
│   │   ├── test_component_discovery.py
│   │   └── test_runtime_paths.py
│   ├── unit
│   │   ├── _route_test_helpers.py
│   │   ├── test_annotations.py
│   │   ├── test_briefing_renderer.py
│   │   ├── test_briefing_service.py
│   │   ├── test_capacity_planning.py
│   │   ├── test_cross_feature_integration.py
│   │   ├── test_execution_events.py
│   │   ├── test_health_aggregator.py
│   │   ├── test_intake_intelligence.py
│   │   ├── test_intake_to_project.py
│   │   ├── test_knowledge_graph_service.py
│   │   ├── test_llm_helpers.py
│   │   ├── test_nl_workflow.py
│   │   ├── test_predictive.py
│   │   ├── test_project_setup.py
│   │   └── test_security_posture.py
│   └── vector_store
│       └── test_faiss_store.py
├── tools
│   ├── __init__.py
│   ├── component_runner.py
│   └── runtime_paths.py
└── vendor
    ├── __init__.py
    ├── celery
    │   └── __init__.py
    ├── jinja2
    │   └── __init__.py
    ├── jsonschema
    │   └── __init__.py
    ├── multipart
    │   ├── __init__.py
    │   └── multipart.py
    ├── numpy
    │   └── __init__.py
    ├── slowapi
    │   ├── __init__.py
    │   ├── errors.py
    │   ├── middleware.py
    │   └── util.py
    ├── sqlalchemy
    │   ├── __init__.py
    │   ├── engine
    │   │   └── __init__.py
    │   ├── exc.py
    │   ├── ext
    │   │   ├── __init__.py
    │   │   └── asyncio
    │   │       └── __init__.py
    │   ├── orm
    │   │   └── __init__.py
    │   └── sql
    │       └── __init__.py
    └── stubs
        ├── __init__.py
        ├── email_validator.py
        ├── events.py
        ├── prompt_registry.py
        ├── pydantic_settings.py
        ├── redis
        │   ├── __init__.py
        │   └── asyncio.py
        ├── requests.py
        └── runtime_flags.py
```
