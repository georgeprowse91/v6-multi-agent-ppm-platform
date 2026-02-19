# Agent 25 — System Health and Monitoring

**Category:** Operations Management
**Role:** Platform Reliability Guardian

---

## What This Agent Is

The System Health and Monitoring agent is responsible for the operational reliability of the platform itself. It monitors every service, every integration, every infrastructure component, and every performance metric — detecting problems before they affect users, raising alerts when thresholds are breached, managing incidents, and providing the operational visibility that the teams running the platform need to keep it performing at the level the business expects.

Every capability the platform offers depends on its component services working correctly. The System Health and Monitoring agent is the layer that ensures they do.

---

## What It Does

**It monitors service health.** The agent continuously checks the health endpoints of every platform service — the API gateway, orchestration service, workflow engine, document service, analytics service, identity and access service, and all others — at configured intervals. Each check records the response status, the response time, and whether the service is reporting healthy or degraded. Services that fail health checks are flagged immediately.

**It collects infrastructure metrics.** Beyond service-level health, the agent collects infrastructure metrics from the platform's compute and storage resources: CPU utilisation, memory utilisation, disk usage, network throughput, and queue depths. These metrics are ingested from Prometheus endpoints, parsed, and stored as time series for trend analysis and alerting.

**It collects application-level metrics.** In addition to infrastructure metrics, the agent monitors application performance: request latency (average and percentile), error rates, throughput, cache hit rates, agent execution times, and connector synchronisation success rates. These metrics provide a view of how the platform is performing from a user and business perspective, not just from an infrastructure perspective.

**It detects anomalies.** The agent uses statistical anomaly detection — analysing metric sequences to identify values that deviate significantly from historical norms — to surface unusual behaviour that might not trigger threshold-based alerts. An anomaly in request latency that does not breach the alert threshold may still indicate an emerging problem, and the anomaly detection capability surfaces it for investigation.

**It manages alerts.** When a metric breaches a configured threshold, the agent creates an alert with a severity level — critical, high, medium, or low — and routes it to the appropriate recipients. Alert routing integrates with PagerDuty and OpsGenie for on-call teams, ensuring that critical issues reach the right people through the right escalation path. Alerts for the same underlying problem are correlated rather than sent as a flood of individual notifications.

**It manages incidents.** When alerts indicate a significant service impact, the agent creates an incident record in ServiceNow — with the incident details, severity, affected services, and initial diagnostic information — and updates the incident as the situation evolves. Post-resolution, it generates a postmortem report summarising what happened, what the impact was, how it was resolved, and what changes should be made to prevent recurrence.

**It monitors SLOs.** Service Level Objectives (SLOs) define the performance targets that the platform is expected to meet — uptime, response time, error rate. The agent tracks actual performance against these targets continuously and raises a breach alert when performance is trending towards an SLO violation before the violation actually occurs, giving the operations team time to intervene.

**It triggers auto-scaling.** When resource metrics indicate that the platform is approaching capacity limits — CPU consistently high, queue depths growing, response times degrading — the agent can trigger auto-scaling webhooks to provision additional capacity. Scaling thresholds for CPU, memory, and queue depth are configurable, and scaling events are recorded with the metrics that triggered them.

**It generates Grafana dashboards.** The agent produces Grafana-compatible dashboard configurations that provide a comprehensive operational view of the platform — visualising service health, infrastructure metrics, application performance, alert history, and SLO tracking in a structured, navigable format accessible to the operations team.

**It performs pre-deployment environment checks.** Before a deployment is allowed to proceed, the agent evaluates the health of the target environment — checking that all services in that environment are healthy, that no active critical alerts exist, and that resource utilisation is within safe limits. If the environment is not in a suitable state for deployment, the check fails and the deployment is blocked until conditions are acceptable.

---

## How It Works

The agent integrates with Azure Monitor and Application Insights for metrics collection and alerting, and with Azure Log Analytics for log-based monitoring and querying. OpenTelemetry exporters send metrics to both Azure Monitor and Prometheus, providing flexibility in monitoring stack choice. Prometheus metric scraping handles infrastructure metrics. HTTP health probes check individual service health. The anomaly detection algorithm uses statistical analysis of metric time series — z-score and interquartile range analysis — to identify outliers without requiring a trained ML model.

A comprehensive test suite verifies Prometheus metrics parsing, application metrics collection, anomaly detection accuracy, alert threshold triggering, health status event publishing, environment health blocking, Grafana dashboard generation, and reporting summary generation.

---

## What It Uses

- Health endpoints of all platform services
- Prometheus metrics endpoints for infrastructure metrics
- Azure Monitor and Application Insights for metrics and logs
- Azure Log Analytics for query-based monitoring
- OpenTelemetry exporters for metrics distribution
- Azure Anomaly Detector service for advanced anomaly detection
- PagerDuty and OpsGenie webhooks for on-call alerting
- ServiceNow integration for incident creation and management
- Azure Logic Apps and Azure Automation for auto-scaling webhooks
- Azure Event Hub for health event publishing
- Grafana dashboard configuration generation

---

## What It Produces

- **Service health status**: real-time health assessment for every platform service
- **Infrastructure metrics**: time-series CPU, memory, disk, and network utilisation data
- **Application performance metrics**: latency, error rate, throughput, and agent execution times
- **Anomaly detections**: statistical outliers identified in metric time series
- **Alerts**: threshold-based notifications with severity levels and routing to on-call systems
- **Incident records**: structured ServiceNow incidents for significant service impacts
- **Postmortem reports**: post-resolution analysis of incidents with prevention recommendations
- **SLO compliance reports**: actual performance against defined service level targets
- **Grafana dashboards**: visual operational monitoring views for the operations team
- **Pre-deployment environment assessments**: go/no-go health checks before deployments
- **Scaling event records**: documentation of auto-scaling triggers and responses

---

## How It Appears in the Platform

The **Performance Dashboard** page in the platform provides the operations-facing view — showing service health status, key infrastructure metrics, active alerts, and SLO compliance. The Grafana dashboard provides a more detailed, interactive operations monitoring experience for the platform engineering team.

Alerts surface in the platform's **Notification Centre** and are pushed to the configured on-call channels (PagerDuty, OpsGenie). Incident status is visible through the platform's admin console.

The pre-deployment environment check integrates with **Agent 18 — Release and Deployment**, appearing as a readiness criterion in the deployment approval workflow. A failed environment health check blocks the deployment and displays the specific issues that need to be resolved.

---

## The Value It Adds

A sophisticated platform that goes offline, runs slowly, or loses data is worse than no platform at all — it destroys confidence and sets back adoption. The System Health and Monitoring agent is the operational safety net that prevents this outcome by detecting problems early, routing them to the right people, and providing the operational visibility needed to diagnose and resolve them quickly.

The SLO monitoring capability, in particular, shifts the operations posture from reactive (responding to outages after they occur) to proactive (detecting trends that indicate an SLO breach is coming before it happens). This is the operational equivalent of the predictive forecasting that the Analytics and Insights agent provides for portfolio management — and it delivers the same benefit: earlier awareness, more time to act, better outcomes.

---

## How It Connects to Other Agents

The System Health and Monitoring agent is the operational guardian for the entire platform, so it connects to every other agent indirectly through its health monitoring. Directly, it provides pre-deployment environment health checks to **Agent 18 — Release and Deployment**, publishes platform health data to **Agent 22 — Analytics and Insights** for operational reporting, and records incidents in ServiceNow alongside the compliance evidence managed by **Agent 16 — Compliance and Regulatory**. Operational metrics feed into the continuous improvement analysis managed by **Agent 20 — Continuous Improvement and Process Mining**.
