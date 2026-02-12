# Tailoring Playbook

This playbook provides worked examples for applying section-level tailoring metadata (`required_level`, `tailoring_rules`, `applicability_conditions`) across typical project profiles.

## How to use this playbook

1. Classify your initiative by **size**, **risk**, and **governance tier**.
2. Start with all `mandatory` sections.
3. Add `recommended` and `optional` sections according to `applicability_conditions`.
4. Use `tailoring_rules` to set the depth of content.
5. Record any justified omissions for auditability.

---

## Scenario 1: Small + Low Risk (Tier-1)

**Profile**
- Single team delivering an internal enhancement.
- Minimal external dependencies.
- Low operational/compliance impact.

**Tailoring approach**
- Include all `mandatory` sections with concise entries.
- Include `recommended` sections when applicable, but keep detail lightweight.
- Include `optional` sections only when a trigger exists (e.g., pending decision).

**Worked example (Status Report)**
- `overall-health-rag` (`mandatory`): include simple green/amber/red with one-line rationale.
- `budget-status` (`recommended`): include only if project has managed budget.
- `decisions-needed` (`optional`): include only if escalation needed this period.

---

## Scenario 2: Medium + Low Risk (Tier-2)

**Profile**
- Multiple teams/workstreams.
- Departmental governance cadence.
- Limited compliance exposure.

**Tailoring approach**
- Include all `mandatory` sections.
- Include nearly all `recommended` sections due to coordination needs.
- Increase specificity on dependencies, progress variance, and ownership.

**Worked example (Sprint Planning)**
- `dependencies` (`recommended`): list owner and due date for each external dependency.
- `definition-of-done-check` (`recommended`): reference standard quality checklist and test expectations.

---

## Scenario 3: Medium + High Risk (Tier-2/Tier-3)

**Profile**
- Business-critical release with security or regulatory sensitivity.
- Cross-team dependencies and formal oversight.

**Tailoring approach**
- Treat `recommended` sections as required unless formally waived.
- Expand all risk-bearing sections with mitigation owner, due date, and contingency triggers.
- Ensure traceability between objectives, scope, and acceptance criteria.

**Worked example (Project Charter)**
- `governance` (`recommended`): include decision forum cadence, approvers, and escalation SLA.
- `budget-summary` (`recommended`): include contingency, tolerance thresholds, and forecast assumptions.
- `risks-assumptions-dependencies` (`mandatory`): include top risks with owner and mitigation strategy.

---

## Scenario 4: Large + High Risk (Tier-3)

**Profile**
- Enterprise program spanning multiple domains/vendors.
- High operational, financial, or regulatory impact.
- Strict assurance and evidence requirements.

**Tailoring approach**
- Mandatory + applicable recommended sections are all expected.
- Optional sections are often activated by governance and audit triggers.
- Require high evidence quality: quantified metrics, control references, named owners, and deadlines.

**Worked example (Status Report + Charter)**
- `progress-vs-plan`: milestone-level variance with corrective action plan.
- `risks-issues`: ranked top risks/issues, owners, due dates, and status trend.
- `governance`: formal review calendar, decision rights matrix, and escalation path.

---

## Quick reference matrix

| Context | Mandatory sections | Recommended sections | Optional sections |
| --- | --- | --- | --- |
| Small + Low risk | Required | Include if applicable; concise depth | Trigger-based |
| Medium + Low risk | Required | Generally required for coordination | Trigger-based |
| Medium + High risk | Required | Expected by default; justify omissions | Often triggered |
| Large + High risk | Required | Treated as required unless waived | Frequently activated |

## Documentation expectations

For every tailored template instance, capture:
- Chosen size/risk/governance classification.
- Any omitted `recommended` section and rationale.
- Any activated `optional` section and its trigger.
- Reviewer/approver acknowledgement when tier-2 or tier-3 governance applies.
