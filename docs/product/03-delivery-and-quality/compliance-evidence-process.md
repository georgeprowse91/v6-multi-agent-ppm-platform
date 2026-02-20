# Compliance Evidence Process

**Purpose:** Define the operational process for tracking connector certification evidence, managing audit artefacts, and maintaining compliance records in the platform.
**Audience:** Compliance officers, platform operators, integration engineers, and auditors.
**Owner:** Compliance Lead / Platform Operations
**Last reviewed:** 2026-02-20
**Related docs:** [acceptance-and-test-strategy.md](acceptance-and-test-strategy.md) · [../05-user-guides/web-console-walkthroughs.md](../05-user-guides/web-console-walkthroughs.md) · [../02-solution-design/connectors/iot-connector-spec.md](../02-solution-design/connectors/iot-connector-spec.md)

> **Migration note:** Consolidated from `user-guides/certification-evidence.md` on 2026-02-20. Operational evidence handling and compliance responsibilities are now managed as a controlled process document in the delivery-and-quality domain.

---

# Certification Evidence Tracking

The web console now includes a certification evidence workflow for connector coverage. Each connector can store a compliance status, certification dates, and attached audit documents (SOC reports, ISO certificates, or regulator attestations).

## What gets tracked

- **Compliance status**: certified, pending, expired, or not certified.
- **Certification dates**: issuance and expiration dates.
- **Audit reference**: external report IDs or links from auditors.
- **Evidence documents**: uploaded files stored alongside connector metadata.

## How to update evidence in the web console

1. Navigate to **Marketplace → Connectors**.
2. Select **Manage Evidence** on a connector card.
3. Update the compliance status, dates, and audit reference.
4. Upload evidence documents (PDFs, certificates, audit reports).
5. Save to persist the record.

## Storage and API integration

- Certification metadata is stored persistently in `data/connectors/certifications.json` (configurable via `CERTIFICATION_STORE_PATH`).
- Evidence documents are stored under `data/connectors/certification_documents/` (configurable via `CERTIFICATION_DOCUMENT_ROOT`).
- The API gateway exposes `/v1/certifications` for listing, creating, and updating records, plus `/v1/certifications/{connector_id}/documents` for evidence uploads.

## Operational checklist

- Schedule periodic reviews for upcoming expirations.
- Attach external audit artifacts whenever a certification status changes.
- Use the audit reference field to cross-link external compliance systems.
