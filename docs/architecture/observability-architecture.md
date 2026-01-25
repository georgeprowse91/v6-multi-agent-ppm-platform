# Observability & Monitoring

## Introduction

Operational excellence requires visibility into how the platform is performing and how users experience it. The Multi‑Agent PPM Platform implements a comprehensive observability strategy encompassing distributed tracing, centralised logging, metrics collection, dashboards and alerting. This document summarises the key components and practices.

## Observability Strategy

Observability is achieved by instrumenting every service and agent to generate traces, logs and metrics. Correlation IDs are propagated across calls, enabling end‑to‑end tracing. Logs are structured and centrally aggregated. Metrics capture both system health and business performance. Dashboards and alerts provide actionable insights for operators.

## Distributed Tracing

### Purpose

Distributed tracing tracks requests across multiple agents to understand end‑to‑end latency and identify bottlenecks. By capturing spans for each step, it reveals which components contribute most to latency and helps diagnose performance issues.

### Implementation

**Tracer Choice:** The platform uses Jaeger or Zipkin as the tracing backend. Agents include tracing libraries that automatically create spans and propagate trace and span identifiers in HTTP headers.

**Correlation IDs:** Every request is assigned a unique Trace ID. Child spans carry a Span ID. These IDs are propagated through all agent calls and logged alongside application logs.

**Sampling & Storage:** Traces are sampled at configurable rates (e.g., 10% of requests in production). Full traces are stored in the tracing backend for retention periods (e.g., 30 days) and can be queried via UI.

### Example Trace

The architecture document includes an example trace for the query “Show me Project Apollo health dashboard”:

The total request time was 650 ms, meeting the platform’s p95 target of <2 s for user queries. Trace analysis identifies slow agents (e.g., Financial Management at 280 ms) and highlights opportunities for optimisation.

## Centralised Logging

### Implementation

Logs from all 25 agents are forwarded to a central aggregator and stored in Elasticsearch (ELK stack) or Splunk. A standard log format includes timestamp, log level, agent name, trace ID, span ID, message and contextual metadata. Example:

{
  "timestamp": "2026-01-15T14:30:00.123Z",
  "level": "INFO",
  "agent": "financial_management",
  "trace_id": "trace_abc123",
  "span_id": "span_2.3",
  "message": "Budget query executed successfully",
  "context": {
    "project_id": "APOLLO-001",
    "user_id": "sarah.chen@company.com",
    "query_duration_ms": 45
  }
}

### Log Levels & Retention

**Log levels follow a standard hierarchy:** DEBUG (disabled in production), INFO (normal operations), WARN (potential issues), ERROR (failed operations) and CRITICAL (system failure). Retention policies differentiate by severity: DEBUG/INFO logs are kept for 30 days, WARN for 90 days, ERROR/CRITICAL for one year, and audit logs for ten years. Log data may be archived to cold storage after retention periods.

### Querying Logs

Operators can perform structured queries using fields and time ranges. Examples include:

**Find all errors in the last hour:** level:ERROR AND timestamp:[now-1h TO now].

**Identify slow queries:** query_duration_ms:>1000.

**Audit user activity:** user_id:"sarah.chen@company.com" AND timestamp:[now-24h TO now].

**Investigate failed API calls:** agent:financial_management AND message:"SAP API call failed".

## Metrics & Monitoring

### Implementation

The platform collects metrics via Prometheus and visualises them in Grafana. Agents expose endpoints for metrics in OpenMetrics format. Metrics are collected at regular intervals (e.g., every 15 seconds) and stored in time‑series databases.

### Types of Metrics

**Request Metrics:** Number of requests per second, request duration histograms (p50, p95, p99), error rate.

**Resource Metrics:** CPU utilisation, memory usage, disk I/O and network I/O for each agent.

**Business Metrics:** Counts of active projects, portfolio value, resource utilisation percentage, budget variance.

### Example Metrics

An excerpt of metrics exported by the Financial Management agent:

financial_agent_requests_total{method="GET",endpoint="/budget",status="200"} 1234
financial_agent_request_duration_seconds{method="GET",endpoint="/budget",quantile="0.95"} 0.28
financial_agent_errors_total{type="database_timeout"} 3
financial_agent_memory_usage_bytes 524288000
financial_agent_cpu_usage_percent 15.2

### Dashboards & Alerts

Grafana dashboards provide live visualisations of system health and business metrics. The System Health Dashboard summarises overall status, agent health (healthy, degraded, down), request rate, response times and error rates, with charts showing trends over time. The Business Metrics Dashboard (not shown in full in the extract) displays portfolio value, benefits realisation, project success rates and resource utilisation. Alerts are configured for thresholds (e.g., p95 response time > 2 s, error rate > 1%, resource utilisation > 90%).

## Alerting & Service Level Objectives

Service Level Objectives (SLOs) define performance targets (e.g., p95 request latency < 2 seconds, sync success rate > 99%, system availability > 99.9%). Alert rules trigger when SLOs are violated. Alerts are routed via messaging platforms (Slack, Teams) or incident management tools (PagerDuty, Opsgenie). Runbooks guide operators through troubleshooting steps, including examining traces, logs and metrics.

## Conclusion

The observability and monitoring architecture ensures that the Multi‑Agent PPM Platform operates reliably and transparently. By combining distributed tracing, centralised logging, comprehensive metrics, dashboards and proactive alerting, the platform provides real‑time insights and accelerates incident resolution. These capabilities enable continuous improvement and help maintain service levels as the platform scales.


---


**Table 1**

| Span | Component | Duration (ms) | Description |

| --- | --- | --- | --- |

| 1 | Intent Router Agent | 120 | Parses natural language and classifies intent. |

| 2 | Response Orchestration Agent | 450 | Plans the query and invokes domain agents. |

| 2.1 | Project Lifecycle Agent | 180 | Retrieves project status and health score. |

| 2.2 | Schedule & Planning Agent | 220 | Retrieves schedule status and calculates SPI. |

| 2.3 | Financial Management Agent | 280 | Retrieves budget status and calculates CPI. |

| 2.4 | Risk Management Agent | 150 | Retrieves risk data and counts high risks. |

| 3 | Response Orchestration (finish) | 80 | Aggregates responses and formats output. |
