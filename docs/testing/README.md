# Testing

> This section documents the quality assurance strategy for the Multi-Agent PPM platform: the full test plan covering objectives, test types, environments, success metrics, and governance; and the dependency matrix that maps test areas to the packages they require in CI and release-gate profiles.

## Contents

- [Acceptance and Test Strategy](#acceptance-and-test-strategy)
- [Test Dependency Matrix](#test-dependency-matrix)

---

## Acceptance and Test Strategy

**Owner:** QA Lead
**Last reviewed:** 2026-02-20
**Related docs:** [Implementation and Change Plan](../change-management/README.md#implementation-and-change-plan) · [Requirements Specification](../01-product-definition/requirements-specification.md) · [Agent System Design](../02-solution-design/agent-system-design.md)

> **Migration note:** Lifted and shifted from `acceptance-criteria.md` on 2026-02-20. This is the canonical quality gate definition for the platform.

### Testing objectives

**Verify functional correctness:** each feature, agent, and integration behaves as specified and fulfils its acceptance criteria.

**Ensure robust integrations:** connectors correctly interface with third-party systems (Planview, Jira, SAP, Workday, Slack, Teams), handling authentication, data mapping, and error conditions gracefully.

**Assess performance and scalability:** the platform supports target concurrency and response-time requirements, with headroom for peak loads and growth.

**Validate security and compliance:** access controls, data encryption, logging, and retention comply with the security architecture and governance plan.

**Deliver user satisfaction:** the UI is intuitive and responsive, and the conversational assistant and agents provide accurate guidance.

### Test types and representative cases

#### Unit tests

**Focus:** verify individual functions, classes, and methods in isolation for each microservice and agent.

- **Agent logic:** test decision paths in agent algorithms (e.g., Intent Router routing logic, Approval Workflow escalation logic) with varied inputs.
- **Data validation:** ensure schema validation and data transformations correctly handle edge cases, invalid inputs, and missing fields.
- **Error handling:** simulate exceptions (network failures, API timeouts) and verify that the code retries or raises appropriate errors.

**Success criteria:** at least 90% branch coverage for critical modules; no unit tests should be skipped or flaky.

#### Integration tests

**Focus:** validate interactions between components and external systems.

- **API contract tests:** verify that domain agents expose correct endpoints, methods, payloads, and response codes; use tools such as Postman and Pact.
- **Connector tests:** simulate calls to Planview, Jira, SAP, Workday, Slack, and Microsoft Teams. Use mock servers or sandbox environments to test authentication flows (OAuth, API tokens), data mapping, and error scenarios (e.g., rate limits, 404 responses).
- **Event flow tests:** publish events onto Kafka topics and verify downstream agents consume and process them correctly.
- **Database and cache integration:** test CRUD operations against the operational store and event store, ensuring ACID transactions and eventual consistency. Validate cache-aside logic: data is retrieved from cache when present and falls back to the API and storage when expired.

**Success criteria:** all integration tests pass against reference environments; error handling triggers retries, fallback, and logging as defined.

#### Performance and load tests

**Focus:** measure system response times, throughput, and resource consumption under varying load levels.

- **API throughput:** use load-testing tools (e.g., Locust, JMeter) to generate concurrent requests to high-traffic endpoints (e.g., schedule calculation, portfolio optimisation). Measure average and p95 response times.
- **Agent concurrency:** simulate multiple simultaneous conversations and agent workflows to test the orchestrator's ability to schedule and aggregate responses. Monitor CPU, memory, and message-queue depths.
- **Data pipeline throughput:** test event ingestion and ETL tasks at peak volumes. Ensure the analytics platform processes updates within SLAs (15-minute ETL cycle). Validate that caching reduces response times without stale-data issues.
- **Scalability tests:** scale microservices horizontally and verify that load balancers distribute traffic correctly. Inject failures (e.g., node shutdown, network partition) and confirm resilience via graceful degradation and circuit breakers.

**Success criteria:** response times remain within defined SLOs (API p95 < 500 ms), throughput scales linearly with additional instances, and no resource saturation or crashes occur.

#### Security and penetration tests

**Focus:** verify secure coding practices, proper authentication and authorisation, and protection of sensitive data.

- **Static and dynamic code analysis:** run automated scanners to detect common vulnerabilities (OWASP Top 10). Incorporate into the CI/CD pipeline.
- **Authentication flows:** test SSO with SAML and OAuth, mutual TLS between microservices, token expiration and revocation. Ensure RBAC and attribute-based access controls enforce least privilege. Attempt privilege escalation and injection attacks.
- **Data-level security:** verify row- and field-level security policies; test that users cannot access data outside their scope. Confirm encryption at rest and in transit (TLS 1.3, AES-256).
- **Secret management:** attempt to retrieve secrets outside the secret vault; verify rotation and revocation policies.

**Success criteria:** zero critical/high vulnerabilities remain unresolved; penetration tests confirm that data is secure and access controls prevent unauthorised actions.

#### User acceptance tests (UAT)

**Focus:** validate that the platform meets end-user needs and delivers a positive user experience.

- **Persona-based scenarios:** create test scripts for each persona (Executive Sponsor, PMO, Project Manager, Team Member, Finance Controller) covering tasks such as creating a project, submitting a demand, approving a change, adjusting a schedule, and monitoring risks.
- **End-to-end journeys:** test the complete lifecycle from demand intake through business-case creation, portfolio prioritisation, project execution, financial tracking, risk management, and post-implementation review. Validate that stage-gates prevent progression without mandatory artefacts.
- **Usability assessments:** conduct guided sessions with representative users; gather feedback on navigation, clarity of information, search functionality, and assistant helpfulness. Measure task completion time and error rate.

**Success criteria:** all critical acceptance criteria are met; user satisfaction scores exceed baseline; no blockers remain for launch.

### Test environments and tools

- **Environments:** maintain separate environments for development, test, staging, and production. Each environment replicates production configurations (microservices, databases, caching, message queues) and has its own telemetry (logging, metrics, tracing).
- **Automation:** implement continuous integration and continuous testing pipelines. Use GitHub Actions to run unit tests on commit, integration tests on merge, and performance tests on release candidates. Trigger security scans via SAST/DAST tools.
- **Data management:** use synthetic or anonymised data sets. Provision test datasets that cover edge cases (large portfolios, complex dependencies, extreme financial values). Mask sensitive information.
- **Monitoring and logs:** enable detailed logs and metrics in test environments. Use observability dashboards to monitor test execution and quickly diagnose issues.

### Success metrics and quality gates

| Metric | Target |
| --- | --- |
| Unit test coverage | ≥ 80% for business logic |
| Integration test coverage | All critical APIs |
| Defect density | < 0.2 high-severity defects per KLOC in release candidates |
| API response time (p95) | < 500 ms |
| Error rate | < 1% |
| Security findings | All critical/high vulnerabilities remediated or risk-accepted by security leadership |
| UAT sign-off | Formal sign-off from representatives of each persona |

### Test governance and reporting

- **Test planning:** maintain a living test plan and test case repository. Update test cases as requirements change and new features are developed.
- **Defect triage:** classify and prioritise defects based on severity and impact. Hold regular triage meetings with development and QA teams.
- **Reporting:** generate test execution reports summarising pass/fail counts, coverage, performance results, and outstanding issues. Share with stakeholders to inform go/no-go decisions.
- **Retrospectives:** after each major release, conduct lessons-learned sessions to improve test processes, tooling, and collaboration.

---

## Test Dependency Matrix

This matrix defines the dependency sets used by CI and local test runs. It clarifies which packages must be installed for each test area and explains the skip policy enforced in CI.

### CI profile: `all-optional`

The CI `test` job uses the `all-optional` profile. It installs:

- `requirements-dev.txt` (runtime and test tooling)
- Editable project install (`pip install -e .`)
- `email-validator` (optional import used by web governance tests)

This profile is expected to satisfy all dependency-based `pytest.importorskip(...)` and dependency guards in `tests/conftest.py`.

### Release-gate profile: `core`

Use this profile when running `make release-gate PROFILE=core` locally or in CI.

```bash
make install-release-gate-core
```

This target installs the editable package with development and test extras (`pip install -e .[dev,test]`) plus the following packages, which are treated as required for core gating:

- `slowapi`
- `cryptography`
- `sqlalchemy`
- `alembic`
- `celery`
- `email-validator`

**Why these dependencies are mandatory for the unit scope:** `release-gate` runs `make test-unit`, `make test-integration`, and `make test-security`. Those test sets include modules guarded by `pytest.importorskip(...)` or collection-time dependency checks for the packages above. Installing them prevents false negatives caused by missing-dependency skips in strict CI skip mode.

`tests/integration/connectors/*` still requires OpenTelemetry packages, but these tests are excluded by default unless `ENABLE_CONNECTOR_INTEGRATION_TESTS` is set.

**Pytest plugin alignment:** `pyproject.toml` configures pytest `timeout` options globally. Ensure pytest is invoked via the same interpreter environment used for installation (e.g., `python -m pytest`) so that `pytest-timeout` from the `test` extra is discoverable.

### Dependency sets by test area

| Test area | Representative paths | Required dependency set |
| --- | --- | --- |
| Core/unit baseline | `tests/agents/`, `tests/ops/config/`, `tests/runtime/` | `requirements-dev.txt` |
| API security/rate limiting | `tests/apps/test_api_gateway_health.py`, `tests/security/test_auth_rbac.py` | baseline + `slowapi` |
| Crypto/security integration | `tests/security/test_auth_cache.py`, `tests/integration/test_data_lineage_service.py` | baseline + `cryptography` |
| Data migration/runtime integration | `tests/integration/test_data_migrations.py`, `tests/integration/test_orchestrator_persistence.py` | baseline + `sqlalchemy`, `alembic` |
| Workflow execution | `tests/integration/test_workflow_celery_execution.py` | baseline + `celery` |
| Web governance validation | `tests/apps/test_web_governance_api.py` | baseline + `email-validator` |
| Connector telemetry integrations | `tests/integration/connectors/*` | baseline + `opentelemetry-*` |

### Skip policy in CI

CI enables strict skip validation with:

- `PYTEST_FAIL_ON_UNEXPECTED_SKIPS=1`
- `pytest --fail-on-unexpected-skips`

Skip reasons are classified by `tests/conftest.py` into:

- `intentional_platform` — must include platform wording such as `[platform]` or `requires linux`.
- `missing_dependency` — missing package or import.
- `unclassified` — any skip that does not match the above categories.

In strict mode, any `missing_dependency` or `unclassified` skip fails CI.
