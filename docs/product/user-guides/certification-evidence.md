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
- The API gateway exposes `/api/v1/certifications` for listing, creating, and updating records, plus `/api/v1/certifications/{connector_id}/documents` for evidence uploads.

## Operational checklist

- Schedule periodic reviews for upcoming expirations.
- Attach external audit artifacts whenever a certification status changes.
- Use the audit reference field to cross-link external compliance systems.
