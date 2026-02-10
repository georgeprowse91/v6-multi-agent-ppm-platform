# Data Retention Policy

## Purpose

Define retention and disposal requirements for key platform data types.

## Retention schedule

| Data type | Typical contents | Retention period | Disposal method |
| --- | --- | --- | --- |
| Audit events | policy decisions, access logs, control outcomes | 7 years | cryptographic erase + immutable store lifecycle expiry |
| Compliance evidence | control test artifacts, attestations | 5 years | secure deletion with deletion evidence |
| Risk and issue records | risk metadata, issue history | 3 years after closure | secure deletion + index purge |
| Operational telemetry | traces, metrics, service logs | 90 days (hot), 1 year (archive) | lifecycle purge |
| Personal data (transactional) | user-submitted PII in workflows | minimum required; default 1 year unless legal hold | secure deletion and backup expiry |

## Disposal controls

- Disposal jobs are automated and policy-driven.
- Deletion operations are logged for auditability.
- Legal hold supersedes standard retention until hold release.

## Governance

- Retention periods are reviewed at least quarterly.
- Regulatory and contractual obligations can increase retention windows.
