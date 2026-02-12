# Tailoring Guidance Schema

This standard defines how canonical templates express section-level tailoring metadata so teams can adapt content based on project context while preserving governance expectations.

## 1) Section criticality

Each section in a canonical template must include `required_level` with one of the following values:

- `mandatory`: Must be completed in all cases.
- `recommended`: Expected by default; omission must be justified by tailoring context.
- `optional`: Include only when triggered by applicability conditions or local team need.

## 2) Tailoring dimensions

Tailoring decisions should evaluate these dimensions together:

- **Project size**
  - `small`: single team, short duration, limited dependencies.
  - `medium`: multiple workstreams, moderate dependencies, formal checkpoints.
  - `large`: multi-team/program-level effort, significant cross-functional dependencies.
- **Risk**
  - `low`: limited impact if delayed/defective, low compliance or security sensitivity.
  - `high`: significant business, regulatory, safety, cybersecurity, or operational exposure.
- **Governance tier**
  - `tier-1`: lightweight local governance.
  - `tier-2`: departmental or portfolio governance with recurring review cadence.
  - `tier-3`: enterprise or regulatory governance with strict controls and evidence requirements.

## 3) Required schema fields

Each section entry in canonical template YAML must include:

- `required_level`: one of `mandatory`, `recommended`, `optional`.
- `tailoring_rules`: list of concrete rules describing how content depth changes by dimension.
- `applicability_conditions`: short statement describing when the section is in scope.

Example:

```yaml
- id: governance
  title: Governance
  type: narrative
  required_level: recommended
  tailoring_rules:
    - Minimum: identify decision owner and escalation path.
    - For medium/large projects or governance tier 2+, define cadence and forum structure.
  applicability_conditions: Required when governance tier is 2 or 3; optional for tier 1.
```

## 4) Decision rules

Apply the following order when tailoring:

1. **Honor mandatory sections first**
   - Mandatory sections are never removed.
2. **Check applicability conditions**
   - If conditions are met, include the section regardless of project size convenience.
3. **Scale depth by risk and governance**
   - High risk or tier-3 governance increases required specificity, evidence, and ownership detail.
4. **Simplify safely for small/low-risk work**
   - Keep intent intact, but permit concise narratives and reduced artifact detail for tier-1/low-risk contexts.
5. **Document deviations for recommended sections**
   - If omitted, record the rationale in tailoring notes or governance log.

## 5) Decision examples

- **Example A: Small + Low risk + Tier-1**
  - Keep all `mandatory` sections.
  - Include `recommended` sections in concise form unless clearly inapplicable.
  - `optional` sections included only when triggered.
- **Example B: Medium + High risk + Tier-2**
  - Keep all `mandatory` and all applicable `recommended` sections.
  - Expand risk, governance, and dependency narratives with owners and due dates.
- **Example C: Large + High risk + Tier-3**
  - Treat all `recommended` sections as effectively required unless formally waived.
  - Add explicit traceability, review cadence, control evidence, and escalation pathways.
