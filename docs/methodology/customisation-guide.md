# Methodology Customisation Guide

This guide explains how to tailor project methodologies to your organisation's needs using the PPM platform's methodology management system.

## Overview

The platform ships with three built-in methodology templates:
- **Predictive** (Waterfall-style with defined stages and gates)
- **Adaptive** (Agile/iterative with backlogs and sprints)
- **Hybrid** (Blends predictive governance with adaptive delivery)

Organisations can customise these templates, create entirely new methodologies, and enforce policies that control which methodologies teams may use.

## Architecture

### Storage Model

Methodology definitions are stored per-tenant with immutable versioning:

| Layer | Description |
|-------|-------------|
| **Built-in templates** | Defined in `docs/methodology/*/map.yaml` files; always available as read-only baselines |
| **Tenant storage** | Customised definitions stored per tenant in `storage/methodology_definitions_{tenant_id}.json` |
| **Canonical schema** | `data/schemas/methodology.schema.json` defines the canonical entity shape |
| **Database** | `methodology_definitions` and `methodology_policies` tables (migration `0011`) |

Each save creates a new version number. Published versions cannot be modified; a new draft version must be created instead.

### Version Lifecycle

```
draft --> published --> deprecated --> archived
```

- **draft**: Work in progress; not available for new workspace creation unless policy allows it
- **published**: Available for project workspace setup
- **deprecated**: Still usable by existing workspaces but hidden from new workspace creation
- **archived**: Fully retired; not usable

## Customising a Methodology

### Using the Methodology Editor

1. Navigate to **Admin > Methodology Editor** (`/admin/methodology`)
2. Select the methodology to customise from the dropdown
3. Modify stages:
   - **Add stages**: Click "Add stage" to append a new stage
   - **Remove stages**: Click the remove button next to a stage
   - **Reorder stages**: Drag stages to change their sequence
4. Modify activities within each stage:
   - Set activity name, description, and prerequisites
   - Choose the recommended canvas tab (document, timeline, dashboard, etc.)
   - Set prerequisite activities that must complete first
5. Configure gates and gate criteria:
   - Define pass/fail criteria for stage transitions
   - Add evidence requirements and automated checks
6. Click **Save** to persist your changes

### Publishing

After customising, navigate to **Admin > Methodology Settings** (`/admin/methodology/settings`) and click **Publish** on the methodology. Only published methodologies are available for new workspace creation (unless the organisation policy allows draft methodologies).

## Organisation Policy

### Setting Policies

Navigate to **Admin > Methodology Settings** (`/admin/methodology/settings`) to configure:

1. **Restrict Methodologies**: Enable to limit which methodologies can be used
2. **Default Methodology**: Set the default for new workspaces
3. **Enforce Published Only**: Require methodologies to be published before use
4. **Department Overrides**: Set per-department methodology restrictions

### Policy Enforcement

When a user creates a new project workspace and selects a methodology, the Workspace Setup Agent validates the selection against the organisation policy:

- If the selected methodology is not in the allowed list, the request is rejected
- If a department-level override exists, its restrictions take precedence
- If "enforce published only" is enabled, draft methodologies cannot be selected

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/methodology/policy` | GET | Retrieve current organisation policy |
| `/api/methodology/policy` | POST | Update organisation policy |
| `/api/methodology/validate` | GET | Validate a methodology selection |
| `/api/methodology/tenant/list` | GET | List all methodologies for the tenant |
| `/api/methodology/tenant/{id}` | GET | Get a specific methodology |
| `/api/methodology/tenant/{id}/publish` | POST | Publish a methodology |
| `/api/methodology/tenant/{id}/deprecate` | POST | Deprecate a methodology |
| `/api/methodology/tenant/{id}/impact` | GET | Check change impact |

## Change Impact Analysis

Before editing or deprecating a methodology, use the **Check Impact** button on the Methodology Settings page to see which active workspaces are currently using it. The impact analysis scans workspace state files to identify:

- Number of affected workspaces
- Project IDs and current status of each affected workspace

Changes to a methodology definition do not retroactively affect existing workspaces. Workspaces continue using the methodology version that was active when they were created until they explicitly re-sync.

## Data Service Integration

Methodology definitions are also available through the canonical Data Service:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/methodologies` | GET | List methodology entities |
| `/v1/methodologies` | POST | Create/update a methodology entity |
| `/v1/methodologies/{id}` | GET | Retrieve a methodology entity |
| `/v1/methodologies/{id}/publish` | POST | Publish a methodology entity |
| `/v1/methodologies/policy` | POST | Set methodology policy |
| `/v1/methodologies/policy/{tenant_id}` | GET | Get methodology policy |

## Creating a Custom Methodology

To create a methodology from scratch:

1. Navigate to the Methodology Editor
2. Start from one of the built-in templates
3. Customise the stages, activities, gates, and criteria
4. Save to create version 1 as a draft
5. Review and publish via the Settings page
6. Set organisation policy to allow the new methodology

### map.yaml Structure

For advanced users, methodologies can also be defined via YAML files placed in `docs/methodology/{methodology-id}/map.yaml`:

```yaml
id: my-custom-methodology
name: My Custom Methodology
description: A tailored approach for our organisation
type: custom
version: "1.0"
nodes:
  - id: stage-1
    title: Discovery
    wbs: "0.1"
    type: stage
    order: 1
    children:
      - id: activity-1-1
        title: Stakeholder Interviews
        wbs: "0.1.1"
        type: activity
        order: 1
      - id: activity-1-2
        title: Requirements Workshop
        wbs: "0.1.2"
        type: activity
        order: 2
  - id: stage-2
    title: Design
    wbs: "0.2"
    type: stage
    order: 2
    children: []
```

## Permissions

Methodology management requires the `methodology.edit` permission, which is typically assigned to:
- PMO Administrators
- Organisation Administrators
- CIO/CTO roles

Standard project managers and team members can view and use published methodologies but cannot edit definitions or policies.
