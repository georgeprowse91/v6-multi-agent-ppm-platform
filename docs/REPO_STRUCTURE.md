# Repository Structure

Complete file tree of `multi-agent-ppm-platform-v4` (build artefacts, `node_modules`, `__pycache__`, `.git`, `.next`, `dist`, `.venv`, runtime agent-storage data excluded).

> **Note on root-level Python shims:** Several files/directories at the repo root are lightweight stubs or vendored packages that shadow real third-party libraries (`email_validator.py`, `requests.py`, `pydantic_settings.py`, `jinja2/`, `jsonschema/`, `multipart/`, `numpy/`, `sqlalchemy/`). They allow the codebase to import those packages without a full install in constrained environments.

```
multi-agent-ppm-platform-v4/
├── .claude/
│   ├── hooks/
│   │   └── session-start.sh
│   └── settings.json
├── .devcontainer/
│   ├── Dockerfile
│   ├── dev.env
│   └── devcontainer.json
├── .github/
│   ├── CODEOWNERS
│   ├── README.md
│   ├── dependabot.yml
│   ├── renovate.json
│   ├── issue_template/
│   │   ├── bug_report.md
│   │   ├── config.yml
│   │   ├── documentation.md
│   │   ├── feature_request.md
│   │   └── security_issue.md
│   ├── pull_request_template.md
│   └── workflows/
│       ├── README.md
│       ├── cd.yml
│       ├── ci.yml
│       ├── connectors-live-smoke.yml
│       ├── container-scan.yml
│       ├── contract-tests.yml
│       ├── dependency-audit.yml
│       ├── e2e-tests.yml
│       ├── iac-scan.yml
│       ├── license-compliance.yml
│       ├── migration-check.yml
│       ├── performance-smoke.yml
│       ├── pr-labeler.yml
│       ├── pr.yml
│       ├── promotion.yml
│       ├── release-gate.yml
│       ├── release.yml
│       ├── sbom.yml
│       ├── secret-scan.yml
│       ├── security-scan.yml
│       ├── static.yml
│       └── storybook-visual-regression.yml
├── .dockerignore
├── .env.demo
├── .env.example
├── .gitattributes
├── .gitignore
├── .gitleaks.toml
├── .pre-commit-config.yaml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md
├── SECURITY.md
├── alembic.ini
├── docker-compose.yml
├── docker-compose.test.yml
├── mkdocs.yml
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── pyproject.toml
├── requirements.txt
├── requirements.in
├── requirements-dev.txt
├── requirements-dev.in
├── requirements-demo.txt
│                                            # Root-level Python shim / stub files
├── email_validator.py                       # Stub for email-validator library
├── events.py                                # Re-exports from packages/contracts/src/events
├── prompt_registry.py                       # Root PromptRegistry + enforce_redaction util
├── pydantic_settings.py                     # Stub for pydantic-settings (BaseSettings)
├── requests.py                              # Minimal requests compat layer (urllib-based)
├── runtime_flags.py                         # demo_mode_enabled() reads env + common.yaml
│                                            # Vendored / stub packages (shadow real installs)
├── jinja2/                                  # Stub __init__.py
├── jsonschema/                              # Stub __init__.py
├── multipart/                               # Stub __init__.py + multipart.py
├── numpy/                                   # Stub __init__.py
├── sqlalchemy/                              # Stub with engine/, ext/, orm/, sql/ sub-packages
│
├── agents/                                  # AI agent implementations
│   ├── AGENT_CATALOG.md
│   ├── README.md
│   ├── __init__.py
│   ├── common/                              # Shared agent utilities
│   │   ├── __init__.py
│   │   ├── connector_integration.py
│   │   ├── health_recommendations.py
│   │   ├── integration_services.py
│   │   ├── metrics_catalog.py
│   │   ├── scenario.py
│   │   └── web_search.py
│   │
│   ├── core-orchestration/                  # Agents 01–03
│   │   ├── README.md
│   │   ├── intent-router-agent/
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures/sample-response.json
│   │   │   ├── models/intent_classifier/README.md
│   │   │   ├── src/intent_router_agent.py
│   │   │   └── tests/README.md
│   │   ├── response-orchestration-agent/
│   │   │   ├── Dockerfile
│   │   │   ├── README.md
│   │   │   ├── demo-fixtures/sample-response.json
│   │   │   ├── src/
│   │   │   │   ├── plan_schema.py
│   │   │   │   └── response_orchestration_agent.py
│   │   │   └── tests/README.md
│   │   └── approval-workflow-agent/
│   │       ├── Dockerfile
│   │       ├── README.md
│   │       ├── demo-fixtures/sample-response.json
│   │       ├── src/
│   │       │   ├── approval_workflow_agent.py
│   │       │   └── templates/{en,fr}/approval_notification.md
│   │       └── tests/README.md
│   │
│   ├── portfolio-management/                # Agents 04–07
│   │   ├── README.md
│   │   ├── demand-intake-agent/
│   │   │   └── src/demand_intake_agent.py
│   │   ├── business-case-agent/
│   │   │   ├── BOUNDARY-NOTES.md
│   │   │   └── src/business_case_investment_agent.py
│   │   ├── portfolio-optimisation-agent/
│   │   │   └── src/portfolio_strategy_agent.py
│   │   └── program-management-agent/
│   │       └── src/program_management_agent.py
│   │
│   ├── delivery-management/                 # Agents 08–16
│   │   ├── README.md
│   │   ├── scope-definition-agent/
│   │   │   └── src/{project_definition_agent,scope_research,web_search}.py
│   │   ├── lifecycle-governance-agent/
│   │   │   └── src/{lifecycle_persistence,monitoring,notifications,
│   │   │            orchestration,persistence,project_lifecycle_agent,
│   │   │            readiness_model,summarization,sync_clients}.py
│   │   ├── schedule-planning-agent/
│   │   │   └── src/schedule_planning_agent.py
│   │   ├── resource-management-agent/
│   │   │   └── src/resource_capacity_agent.py
│   │   ├── financial-management-agent/
│   │   │   └── src/financial_management_agent.py
│   │   ├── vendor-procurement-agent/
│   │   │   ├── PROCUREMENT_WORKFLOW_BOUNDARIES.md
│   │   │   └── src/vendor_procurement_agent.py
│   │   ├── quality-management-agent/
│   │   │   └── src/quality_management_agent.py
│   │   ├── risk-management-agent/
│   │   │   └── src/{risk_management_agent,risk_management_api,
│   │   │            risk_nlp_training}.py
│   │   └── compliance-governance-agent/
│   │       ├── COMPLIANCE_CONTROL_CATALOG.md
│   │       └── src/compliance_regulatory_agent.py
│   │
│   ├── operations-management/               # Agents 17–25
│   │   ├── README.md
│   │   ├── change-control-agent/
│   │   │   └── src/change_configuration_agent.py
│   │   ├── release-deployment-agent/
│   │   │   └── src/release_deployment_agent.py
│   │   ├── knowledge-management-agent/
│   │   │   └── src/{knowledge_db,knowledge_management_agent}.py
│   │   ├── continuous-improvement-agent/
│   │   │   └── src/process_mining_agent.py
│   │   ├── stakeholder-communications-agent/
│   │   │   └── src/stakeholder_communications_agent.py
│   │   ├── analytics-insights-agent/
│   │   │   └── src/analytics_insights_agent.py
│   │   ├── data-synchronisation-agent/
│   │   │   └── src/data_sync_agent.py
│   │   ├── workflow-engine-agent/
│   │   │   ├── src/{workflow_engine_agent,workflow_spec,
│   │   │   │        workflow_state_store,workflow_task_queue}.py
│   │   │   └── workflows/schema/workflow_spec.schema.json
│   │   └── system-health-agent/
│   │       └── src/system_health_agent.py
│   │
│   └── runtime/                             # Agent runtime framework
│       ├── README.md
│       ├── __init__.py
│       ├── timeout_harness.py
│       ├── eval/
│       │   ├── manifest.yaml
│       │   ├── run_eval.py
│       │   └── fixtures/{definition,prompt,tools,flow-*.yaml}
│       ├── agents/runtime/prompts/
│       │   ├── README.md
│       │   ├── prompt_registry.py
│       │   ├── schema/prompt.schema.json
│       │   ├── examples/intent-router.prompt.yaml
│       │   ├── demand-intake-extraction.prompt.yaml
│       │   ├── intake-assistant-{attachments,business,sponsor,success}.prompt.yaml
│       │   └── project-intake-extraction.prompt.yaml
│       └── src/
│           ├── __init__.py
│           ├── agent_catalog.py
│           ├── audit.py
│           ├── base_agent.py
│           ├── data_service.py
│           ├── event_bus.py
│           ├── memory_store.py
│           ├── models.py
│           ├── notification_service.py
│           ├── orchestrator.py
│           ├── policy.py
│           └── state_store.py
│
├── apps/                                    # Deployable applications
│   ├── README.md
│   ├── admin-console/
│   │   ├── Dockerfile
│   │   ├── helm/{Chart.yaml,values.yaml,templates/…}
│   │   └── tests/README.md
│   ├── analytics-service/
│   │   ├── Dockerfile
│   │   ├── job_registry.py
│   │   ├── jobs/{manifests,schema}/
│   │   ├── helm/{Chart.yaml,values.yaml,templates/…}
│   │   ├── src/{config,health,kpi_engine,main,metrics_store,scheduler}.py
│   │   └── tests/test_scheduler.py
│   ├── api-gateway/
│   │   ├── Dockerfile
│   │   ├── helm/{Chart.yaml,values.yaml,templates/…}
│   │   ├── migrations/sql/{001_init_postgresql,001_init_sqlite}.sql
│   │   ├── openapi/README.md
│   │   └── src/api/
│   │       ├── main.py
│   │       ├── config.py  cors.py  circuit_breaker.py  limiter.py
│   │       ├── connector_loader.py  certification_storage.py
│   │       ├── document_session_store.py  leader_election.py
│   │       ├── secret_rotation.py  webhook_storage.py
│   │       ├── bootstrap/{components,connector_component,
│   │       │              document_session_component,
│   │       │              leader_election_component,
│   │       │              orchestrator_component,registry,
│   │       │              secret_rotation_component}.py
│   │       ├── middleware/security.py
│   │       ├── routes/{agent_config,agents,analytics,audit,
│   │       │           certifications,compliance_research,connectors,
│   │       │           documents,health,lineage,prompts,risk_research,
│   │       │           scope_research,vendor_management,
│   │       │           vendor_research,workflows}.py
│   │       └── schemas/certification.schema.json
│   ├── connector-hub/
│   │   └── Dockerfile
│   ├── demo_streamlit/
│   │   ├── app.py
│   │   ├── validate_demo.py
│   │   └── data/{assistant_outcome_variants,feature_flags_demo}.json
│   ├── document-service/
│   │   ├── Dockerfile
│   │   ├── document_policy_config.py
│   │   ├── helm/{Chart.yaml,values.yaml,templates/…}
│   │   ├── ops/config/bundles/default-policy-bundle.yaml
│   │   └── src/{config,document_policy,document_storage,main}.py
│   ├── mobile/                              # React Native app
│   │   ├── App.tsx
│   │   ├── app.json  babel.config.js  jest.config.js  tsconfig.json
│   │   └── src/
│   │       ├── api/client.ts
│   │       ├── components/{AppErrorBoundary,Card,LabelValueRow}.tsx
│   │       ├── context/AppContext.tsx
│   │       ├── i18n/locales/{de,en}.json
│   │       ├── integration/mobileFlows.integration.test.tsx
│   │       ├── screens/{Approvals,Assistant,Canvas,Connectors,
│   │       │            Dashboard,Login,Methodologies,
│   │       │            StatusUpdates,TenantSelection}Screen.tsx
│   │       ├── services/{notifications,secureSession,statusQueue,telemetry}.ts
│   │       └── theme.ts
│   ├── orchestration-service/
│   │   ├── Dockerfile
│   │   ├── helm/{Chart.yaml,values.yaml,templates/…}
│   │   ├── ops/config/bundles/default-policy-bundle.yaml
│   │   └── src/{config,leader_election,main,orchestrator,
│   │            persistence,workflow_client}.py
│   ├── web/                                 # Main web application (Python + React)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── helm/{Chart.yaml,values.yaml,templates/…}
│   │   ├── data/
│   │   │   ├── agents.json  demo_seed.json  llm_models.json  ppm.db  …
│   │   │   ├── demo/{demo_run_log,sor_fixtures}.json
│   │   │   ├── demo_conversations/{project_intake,resource_request,
│   │   │   │                       vendor_procurement}.json
│   │   │   ├── demo_dashboards/*.json
│   │   │   └── workflows/{change_request,intake_to_delivery}.json
│   │   ├── frontend/                        # Vite + React TypeScript SPA
│   │   │   ├── index.html  vite.config.ts  vitest.config.ts
│   │   │   ├── package.json  tsconfig.json  tsconfig.node.json
│   │   │   ├── .storybook/{main,preview,test-runner}.ts
│   │   │   ├── scripts/{check-design-tokens,check-raw-json-casts,
│   │   │   │            generate-css-module-types}.mjs
│   │   │   └── src/
│   │   │       ├── App.tsx  main.tsx
│   │   │       ├── auth/permissions.ts
│   │   │       ├── components/
│   │   │       │   ├── agentConfig/AgentGallery.tsx
│   │   │       │   ├── agentRuns/{AgentRunDetail,AgentRunList,ProgressBadge}.tsx
│   │   │       │   ├── assistant/{ActionChipButton,AssistantHeader,
│   │   │       │   │              AssistantPanel,ChatInput,ContextBar,
│   │   │       │   │              ConversationalCommandCard,MessageBubble,
│   │   │       │   │              MessageList,PromptPicker,QuickActions,
│   │   │       │   │              ScopeResearchCard,assistantMode,
│   │   │       │   │              entryQuickActions}.tsx|ts
│   │   │       │   ├── canvas/CanvasWorkspace.tsx
│   │   │       │   ├── config/ConfigForm.tsx
│   │   │       │   ├── connectors/{ConnectorGallery,SyncStatusPanel}.tsx
│   │   │       │   ├── dashboard/{KpiWidget,StatusIndicator}.tsx
│   │   │       │   ├── docs/CoeditEditor.tsx
│   │   │       │   ├── error/ErrorBoundary.tsx
│   │   │       │   ├── icon/{Icon,iconMap}.tsx|ts
│   │   │       │   ├── layout/{AppLayout,Header,LeftPanel,
│   │   │       │   │           MainCanvas,SearchOverlay}.tsx
│   │   │       │   ├── methodology/{ActivityDetailPanel,
│   │   │       │   │                MethodologyMapCanvas,
│   │   │       │   │                MethodologyNav,
│   │   │       │   │                MethodologyWorkspaceSurface}.tsx
│   │   │       │   ├── onboarding/OnboardingTour.tsx
│   │   │       │   ├── project/{AgentGallery,ProjectConfigSection,
│   │   │       │   │            ProjectConnectorGallery,ProjectMcpSidebar}.tsx
│   │   │       │   ├── templates/TemplateGallery.tsx
│   │   │       │   ├── theme/ThemeProvider.tsx
│   │   │       │   ├── tours/TourProvider.tsx
│   │   │       │   └── ui/{ConfirmDialog,EmptyState,ErrorBoundary,
│   │   │       │            FadeIn,FocusTrap,Skeleton}.tsx
│   │   │       ├── hooks/
│   │   │       │   ├── assistant/{useAssistantChat,useContextSync,
│   │   │       │   │              useIntakeAssistantAdapter,
│   │   │       │   │              useSuggestionEngine}.ts
│   │   │       │   ├── useRealtimeConsole.ts
│   │   │       │   └── useRequestState.ts
│   │   │       ├── i18n/locales/{de,en,pseudo}.json
│   │   │       ├── pages/
│   │   │       │   ├── AgentProfilePage  AgentRunsPage  AnalyticsDashboard
│   │   │       │   ├── ApprovalsPage  AuditLogPage  ConfigPage
│   │   │       │   ├── ConnectorDetailPage  ConnectorMarketplacePage
│   │   │       │   ├── DemoRunPage  DocumentSearchPage  EnterpriseUpliftPage
│   │   │       │   ├── ForbiddenPage  GlobalSearch  HomePage
│   │   │       │   ├── IntakeApprovalsPage  IntakeFormPage  IntakeStatusPage
│   │   │       │   ├── LessonsLearnedPage  LoginPage  MergeReviewPage
│   │   │       │   ├── MethodologyEditor  NotificationCenterPage
│   │   │       │   ├── PerformanceDashboardPage  ProjectConfigPage
│   │   │       │   ├── PromptManager  RoleManager  WorkflowDesigner
│   │   │       │   ├── WorkflowMonitoringPage  WorkspaceDirectoryPage
│   │   │       │   └── WorkspacePage  (each as .tsx + .module.css)
│   │   │       ├── routing/RouteGuards.tsx
│   │   │       ├── services/{apiClient,knowledgeApi,searchApi}.ts
│   │   │       ├── store/
│   │   │       │   ├── useAppStore.ts  useCanvasStore.ts
│   │   │       │   ├── agentConfig/useAgentConfigStore.ts
│   │   │       │   ├── assistant/{useAssistantStore,
│   │   │       │   │              useIntakeAssistantStore}.ts
│   │   │       │   ├── connectors/useConnectorStore.ts
│   │   │       │   ├── documents/coeditStore.ts
│   │   │       │   ├── methodology/useMethodologyStore.ts
│   │   │       │   ├── projectConnectors/useProjectConnectorStore.ts
│   │   │       │   ├── agents/runtime/prompts/usePromptStore.ts
│   │   │       │   └── realtime/useRealtimeStore.ts
│   │   │       ├── styles/{index,tokens}.css
│   │   │       ├── test/{accessibility,assistantResponses,prompts,
│   │   │       │         searchApi,setup,tokenContrast}.test.ts
│   │   │       ├── types/{agentRuns,css-modules,prompt}.ts
│   │   │       └── utils/{apiValidation,assistantResponses,prompts,schema}.ts
│   │   ├── scripts/{check_legacy_workspace_artifacts,generate_metadata}.py
│   │   ├── src/                             # FastAPI backend
│   │   │   ├── main.py  config.py  bootstrap.py  dependencies.py
│   │   │   ├── middleware.py  oidc_client.py  gating.py
│   │   │   ├── agent_registry.py  agent_settings_{models,store}.py
│   │   │   ├── analytics_proxy.py  connector_hub_proxy.py
│   │   │   ├── data_service_proxy.py  document_proxy.py
│   │   │   ├── lineage_proxy.py  orchestrator_proxy.py
│   │   │   ├── demo_{integrations,seed}.py
│   │   │   ├── intake_{models,store}.py
│   │   │   ├── knowledge_store.py  llm_preferences_store.py
│   │   │   ├── merge_review_{models,store}.py
│   │   │   ├── methodologies.py  methodology_node_runtime.py
│   │   │   ├── pipeline_{models,store}.py
│   │   │   ├── runtime_lifecycle_store.py  search_service.py
│   │   │   ├── spreadsheet_{models,store}.py
│   │   │   ├── template_{mappings,models,registry}.py
│   │   │   ├── canonical_template_registry.py
│   │   │   ├── timeline_{models,store}.py  tree_{models,store}.py
│   │   │   ├── workflow_{models,store}.py  workspace_state{,_store}.py
│   │   │   ├── routes/{analytics,assistant,connectors,
│   │   │   │           documents,workflow,workspace}.py
│   │   │   ├── services/{analytics,assistant,connectors,
│   │   │   │             documents,workflow,workspace}.py
│   │   │   └── web_services/{analytics,assistant,connectors,
│   │   │                     documents,workflow,workspace}.py
│   │   ├── static/{index.html,styles.css}
│   │   └── tests/
│   │       └── test_*.py  (38 test modules)
│   └── workflow-engine/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── workflow_registry.py
│       ├── helm/{Chart.yaml,values.yaml,templates/…}
│       ├── migrations/sql/{001_init_postgresql,001_init_sqlite}.sql
│       ├── src/{agent_client,circuit_breaker,config,main,workflow_audit,
│       │         workflow_definitions,workflow_runtime,workflow_storage}.py
│       ├── tests/{test_storage_policy,test_workflow_storage_concurrency}.py
│       └── workflows/
│           ├── schema/workflow.schema.json
│           └── definitions/
│               ├── change-request.workflow.yaml
│               ├── deployment-rollback.workflow.yaml
│               ├── intake-triage.workflow.yaml
│               ├── project-initiation.workflow.yaml
│               ├── publish-charter.workflow.yaml
│               ├── quality-audit.workflow.yaml
│               └── risk-mitigation.workflow.yaml
│
├── artifacts/                               # CI/CD generated artefacts
│   ├── dependencies/hygiene-summary.json
│   ├── docs/staleness-report.json
│   ├── dr/{backup-summary,restore-drill}.json
│   ├── incident/summary.json
│   ├── maturity/scorecard-latest.json
│   ├── observability/slo-summary.json
│   ├── ops/{alert-quality,drift-summary}.json
│   ├── performance/{capacity-summary,k6-summary}.json
│   ├── release-gate/quality-report-core.json
│   ├── security/{secret-scan-summary,vulnerability-summary}.json
│   └── tests/coverage-summary.json
│
├── config/                                  # Runtime configuration
│   ├── common.yaml
│   ├── data-synchronisation-agent/{pipelines,validation_rules}.yaml
│   ├── agents/{demo-participants,intent-routing}.yaml
│   ├── connectors/mock/{azure_devops,clarity,jira,planview,
│   │                    sap,servicenow,teams,workday}.yaml
│   ├── demo-workflows/{approval-gating,procurement,project-intake,
│   │                   resource-reallocation,risk-mitigation,
│   │                   vendor-onboarding}.workflow.yaml
│   ├── environments/prod.yaml
│   ├── feature-flags/flags.yaml
│   └── rbac/{field-level,roles}.yaml
│
├── constraints/
│   └── py313.txt
│
├── data/                                    # Seed & schema data
│   ├── README.md
│   ├── agent_storage/                       # Runtime agent storage (excluded)
│   ├── analytics_{events,kpi_history,lineage}.json
│   ├── approval_{notification_store,store}.json
│   ├── demo/
│   ├── fixtures/
│   ├── lineage/
│   ├── migrations/versions/
│   ├── agents/runtime/prompts/
│   ├── quality/
│   ├── schemas/examples/
│   └── seed/
│
├── packages/ui-kit/design-system/
│   ├── README.md
│   ├── icons/icon-map.json
│   ├── stories/{EmptyState,TokenPalette}.stories.tsx
│   └── tokens/tokens.ts
│
├── docs/
│   ├── README.md
│   ├── agents/{README,agent-catalog}.md
│   ├── api/
│   │   ├── {analytics,connector-hub,document,openapi,orchestration}-openapi.yaml
│   │   ├── graphql-schema.graphql
│   │   └── {auth,event-contracts,governance,webhooks}.md
│   ├── architecture/
│   │   ├── README.md  DESIGN_REVIEW.md  feedback.md
│   │   ├── adr/0000–0010 ADRs
│   │   ├── diagrams/{c4-component,c4-container,c4-context,data-lineage,
│   │   │             deployment-overview,seq-*.puml,service-topology.puml,
│   │   │             threat-model-flow.puml}
│   │   ├── grafana/{cost_dashboard,multi_agent_tracing}.json
│   │   ├── images/{grafana-ppm-platform,grafana-ppm-slo}.svg
│   │   └── {agent-orchestration,agent-runtime,ai-architecture,
│   │        connector-architecture,container-runtime-identity-policy,
│   │        data-architecture,data-model,deployment-architecture,
│   │        human-in-loop,logical-architecture,observability-architecture,
│   │        performance-architecture,physical-architecture,…}.md
│   ├── assets/ui/screenshots/
│   ├── change-management/
│   ├── compliance/
│   ├── connectors/generated/
│   ├── data/
│   ├── dependencies/
│   ├── generated/services/
│   ├── methodology/{adaptive,hybrid,predictive}/
│   ├── onboarding/
│   ├── product/
│   │   ├── 01-product-definition/
│   │   ├── 02-solution-design/{agent-system-design,assistant-panel-design,
│   │   │                       platform-architecture-overview}.md
│   │   │   └── connectors/iot-connector-spec.md
│   │   ├── 03-delivery-and-quality/{acceptance-and-test-strategy,
│   │   │                            compliance-evidence-process,
│   │   │                            implementation-and-change-plan}.md
│   │   └── 04-commercial-and-positioning/{competitive-positioning,
│   │                                      go-to-market-plan,
│   │                                      market-and-problem-analysis,
│   │                                      packaging-and-pricing,
│   │                                      sales-messaging-and-collateral}.md
│   ├── production-readiness/
│   │   ├── {checklist,evidence-pack,maturity-model,release-process,
│   │        security-baseline}.md
│   │   └── maturity-scorecards/{README,latest}.md
│   ├── runbooks/{backup-recovery,compose-profiles,credential-acquisition,
│   │            data-sync-failures,deployment,disaster-recovery,
│   │            incident-response,llm-degradation,monitoring-dashboards,
│   │            oncall,quickstart,…}.md
│   ├── templates/
│   │   ├── components/*.yaml
│   │   ├── core/{communication-plan,deployment-checklist,executive-dashboard,
│   │   │         product-backlog,project-charter,project-management-plan,
│   │   │         requirements,risk-register,sprint-planning,
│   │   │         sprint-retrospective,sprint-review,status-report}/
│   │   ├── extensions/{agile,compliance,compliance/privacy,devops,
│   │   │               hybrid,safe,waterfall}/
│   │   ├── guides/  mappings/  migration/
│   │   ├── schemas/examples/
│   │   └── standards/
│   ├── testing/
│   └── ui/
│
├── examples/
│   ├── connector-configs/
│   ├── demo-scenarios/
│   ├── methodology-maps/
│   ├── schema/
│   └── workflows/
│
├── ops/infra/
│   ├── kubernetes/
│   │   └── helm-charts/{observability,ppm-platform}/
│   ├── observability/otel/helm/templates/
│   ├── ops/config/dlp/bundles/
│   └── terraform/envs/demo/
│
├── integrations/
│   ├── apps/connector-hub/
│   │   ├── Dockerfile
│   │   ├── helm/{Chart.yaml,values.yaml,templates/…}
│   │   ├── registry/
│   │   ├── sandbox/{examples,fixtures,schema}/
│   │   ├── src/
│   │   └── tests/
│   ├── connectors/                          # 30+ connector implementations
│   │   ├── sdk/src/clients/
│   │   ├── registry/{schemas,signing/public-keys}/
│   │   ├── mock/{azure_devops,clarity,jira,planview,sap,servicenow,teams,workday}/
│   │   ├── integration/
│   │   ├── adp/           archer/        asana/
│   │   ├── azure_communication_services/  azure_devops/
│   │   ├── clarity/       clarity_mcp/   confluence/
│   │   ├── google_calendar/ google_drive/
│   │   ├── iot/           jira/          jira_mcp/
│   │   ├── logicgate/     m365/          mcp_client/
│   │   ├── monday/        ms_project_server/
│   │   ├── netsuite/      notification_hubs/
│   │   ├── oracle/        outlook/
│   │   ├── planview/      planview_mcp/
│   │   ├── salesforce/    sap/           sap_mcp/   sap_successfactors/
│   │   ├── servicenow/    sharepoint/    slack/     slack_mcp/
│   │   ├── smartsheet/    teams/         teams_mcp/
│   │   ├── twilio/        workday/       workday_mcp/
│   │   └── zoom/
│   │   (each: src/, mappings/, tests/[fixtures/])
│   └── services/integration/
│
├── ops/
│   ├── config/
│   │   ├── abac/  data-synchronisation-agent/  workflow-engine-agent/
│   │   ├── agents/schema/
│   │   ├── connectors/  data-classification/  environments/
│   │   ├── feature-flags/  iam/  plans/  rbac/
│   │   ├── retention/  security/  signing/  tenants/
│   ├── ops/infra/
│   │   ├── kubernetes/{helm-charts/ppm-platform,manifests}/
│   │   ├── observability/{alerts,dashboards,otel/helm/templates,slo}/
│   │   ├── ops/config/{dlp,network,schema,security}/bundles/
│   │   ├── tenancy/
│   │   └── terraform/
│   │       ├── dr/  envs/{dev,prod,stage,test}/
│   │       └── modules/{aks,cost-analysis,keyvault,monitoring,
│   │                    networking,postgresql}/
│   ├── schemas/
│   ├── scripts/
│   └── tools/{codegen,format,lint,load_testing,local-dev}/
│
├── packages/                                # Shared Python & TypeScript packages
│   ├── canvas-engine/                       # TypeScript canvas components
│   │   └── src/components/
│   │       ├── ApprovalCanvas   BacklogCanvas    BoardCanvas
│   │       ├── CanvasHost       DashboardCanvas  DependencyMapCanvas
│   │       ├── DocumentCanvas   FinancialCanvas  GanttCanvas
│   │       ├── GridCanvas       RoadmapCanvas    SpreadsheetCanvas
│   │       ├── StructuredTreeCanvas  TimelineCanvas
│   │       ├── hooks/  security/  test/  types/
│   ├── common/src/common/
│   ├── connectors/
│   ├── contracts/src/{api,auth,data,events,models}/
│   ├── crypto/
│   ├── data-quality/src/data_quality/
│   ├── design-tokens/
│   ├── event-bus/src/event_bus/
│   ├── feature-flags/src/feature_flags/
│   ├── feedback/
│   ├── llm/                                 # LLM provider abstraction
│   │   ├── scripts/
│   │   ├── src/{llm,providers}/
│   │   └── tests/
│   ├── methodology-engine/
│   ├── observability/src/{observability,opentelemetry/…}/
│   ├── policy/
│   ├── security/src/security/
│   ├── testing/
│   ├── ui-kit/
│   │   ├── packages/ui-kit/design-system/{icons,stories,tokens}/
│   │   └── src/
│   ├── vector_store/
│   └── workflow/src/workflow/
│
├── ops/config/
│   ├── abac/
│   └── rbac/
│
├── agents/runtime/prompts/
│   ├── approval-workflow/
│   ├── intent-router/
│   ├── knowledge-agent/
│   └── response-orchestration/
│
├── scripts/                                 # Repo-level helper scripts
│   ├── build_template_dependency_map.py
│   ├── check-docs-migration-guard.py
│   ├── check-legacy-ui-references.py
│   ├── check-placeholders.py
│   ├── check-schema-example-updates.py
│   ├── check-templates.py
│   ├── check-ui-emojis.sh
│   ├── check-ui-icons.sh
│   ├── check_api_versioning.py
│   ├── check_connector_maturity.py
│   ├── demo_preflight.py
│   ├── generate_agent_metadata.py
│   ├── generate_demo_data.py
│   ├── load_demo_data.py
│   ├── quickstart_smoke.py
│   ├── reset_demo_data.sh
│   ├── schema_registry.py
│   ├── schema_tool.py
│   ├── validate-manifests.py
│   ├── validate-mcp-manifests.py
│   ├── validate-schemas.py
│   └── validate_demo_fixtures.py
│
├── tools/                                   # Runtime tooling helpers
│   ├── __init__.py
│   ├── component_runner.py
│   └── runtime_paths.py
│
├── security/
│
├── services/                                # Microservices
│   ├── agent-config/src/
│   ├── agent-runtime/src/config/  tests/
│   ├── audit-log/
│   │   ├── contracts/  helm/templates/  src/  storage/  tests/
│   ├── auth-service/src/  tests/
│   ├── data-lineage-service/
│   │   ├── helm/templates/  src/  tests/
│   ├── data-service/
│   │   ├── helm/templates/  src/  tests/
│   ├── data-sync-service/
│   │   ├── contracts/  helm/templates/  rules/  src/  tests/
│   ├── identity-access/
│   │   ├── contracts/  helm/templates/  src/  storage/  tests/
│   ├── memory_service/
│   ├── notification-service/
│   │   ├── contracts/  helm/templates/  src/  templates/  tests/
│   ├── policy-engine/
│   │   ├── contracts/  helm/templates/  ops/config/{bundles,schema}/  src/  tests/
│   ├── realtime-coedit-service/src/  tests/
│   ├── scope_baseline/
│   └── telemetry-service/
│       ├── contracts/  helm/{files,templates}/  pipelines/  src/  tests/
│
└── tests/                                   # Cross-cutting test suites
    ├── agents/    apps/     config/   connectors/
    ├── contract/  data/     demo/     docs/
    ├── e2e/       feedback/ helpers/
    ├── integration/connectors/
    ├── llm/       load/     memory/   notification/
    ├── observability/  ops/
    │   └── fixtures/check_placeholders/{valid,invalid}/
    ├── orchestrator/   packages/{common,security}/
    ├── performance/    ops/config/  policy/  agents/runtime/prompts/
    ├── runtime/agents/runtime/prompts/  security/  services/
    ├── tools/     vector_store/
    └── (test modules for all layers)
```

## Top-level summary

| Path | Purpose |
|------|---------|
| `agents/` | 25 specialised AI agents grouped into core-orchestration, portfolio, delivery, and operations domains |
| `apps/` | Deployable services: web app, API gateway, analytics, document, orchestration, workflow-engine, mobile, admin console |
| `integrations/` | Connector hub + 30+ third-party connectors (Jira, SAP, Workday, Salesforce, ServiceNow, etc.) |
| `packages/` | Shared libraries: LLM abstraction, canvas engine, event bus, security, observability, contracts, UI kit |
| `services/` | Backend microservices: auth, audit log, data lineage, data sync, identity access, notification, policy engine, telemetry |
| `ops/` | Infrastructure-as-code (Terraform), Kubernetes Helm charts, observability config, RBAC/ABAC policies |
| `ops/infra/` | Additional Kubernetes Helm charts, OTel config, Terraform demo env, DLP policies |
| `config/` | Runtime configuration for agents, connectors, feature flags, RBAC, demo workflows |
| `docs/` | Architecture ADRs, API specs, runbooks, product docs, 100+ PM methodology templates |
| `tests/` | Cross-cutting test suites: e2e, integration, contract, load, security |
| `scripts/` | Repo-level scripts: schema validation, template checks, demo data generation, manifest validation |
| `tools/` | Runtime tooling helpers: component runner, path resolution |
| `agents/runtime/` | Agent runtime framework (base agent, orchestrator, state store, event bus, prompt registry) |
| `packages/ui-kit/design-system/` | Design tokens, icon map, Storybook stories |
| `agents/runtime/prompts/` | Versioned prompt files for each agent type |
| `ops/config/` | ABAC / RBAC policy bundles |
| `security/` | Security configuration and tooling |
| `examples/` | Connector configs, demo scenarios, methodology maps, workflow examples |
| `artifacts/` | CI/CD generated reports: coverage, vulnerability scan, release gate, SLO, k6, DR |
| `data/` | Seed data, schemas, migrations, lineage fixtures, prompts |
| `constraints/` | Python version constraint files (e.g. `py313.txt`) |
| `jinja2/` `jsonschema/` `multipart/` `numpy/` `sqlalchemy/` | Root-level vendored/stub packages — shadow real installs in constrained environments |
| `email_validator.py` `requests.py` `pydantic_settings.py` | Root-level Python compatibility shims |
| `runtime_flags.py` | `demo_mode_enabled()` helper — reads `DEMO_MODE` env var + `config/common.yaml` |
| `prompt_registry.py` | Root `PromptRegistry` class + `enforce_redaction()` PII utility |
| `events.py` | Re-exports event contract models from `packages/contracts/src/events` |
