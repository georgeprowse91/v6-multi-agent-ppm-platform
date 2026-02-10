# Consent Mechanism

## Objective

Ensure personal data is processed only when a valid legal basis exists and consent is captured where required.

## Consent lifecycle

1. **Collection**: explicit consent is requested at data capture points.
2. **Recording**: consent records include subject identifier, purpose, timestamp, and source.
3. **Enforcement**: policy checks must verify consent before processing personal data.
4. **Auditability**: each consent-dependent decision is logged in audit events.
5. **Revocation**: revoked consent blocks future processing and triggers downstream restrictions.

## Enforcement in platform services

- Policy controls reject personal-data operations when consent is missing.
- Data minimisation removes unneeded fields and masks sensitive fields.
- Agents handling sensitive workflows call compliance policy checks before action execution.

## Team procedure (training guidance)

- Review this mechanism during onboarding for engineering, product, and operations teams.
- Run periodic table-top scenarios for consent revocation and subject access workflows.
- Record attendance and updates in the compliance training tracker.
