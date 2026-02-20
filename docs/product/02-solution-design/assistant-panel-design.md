# Assistant Panel Design

**Purpose:** Define the prompt model, library structure, and interaction behaviour of the AI assistant panel embedded in the platform workspace.
**Audience:** Front-end engineers, UX designers, product management, and AI/ML engineers building agent integrations.
**Owner:** Product Design / AI Engineering
**Last reviewed:** 2026-02-20
**Related docs:** [platform-architecture-overview.md](platform-architecture-overview.md) · [agent-system-design.md](agent-system-design.md) · [../01-product-definition/personas-and-ux-guidelines.md](../01-product-definition/personas-and-ux-guidelines.md)

> **Migration note:** Moved from `assistant-panel.md` on 2026-02-20. The prompt model and panel behaviour now live in the solution design domain.

---

# Assistant Panel Prompt Library

## Overview
The assistant panel includes a structured prompt library that provides reusable, context-aware prompts for common project management tasks. Prompts are stored in the browser (local storage) and surfaced in the UI as “Next actions” chips that align with the current project stage. Prompt definitions are forwarded to the orchestration service so downstream agents receive the prompt ID, description, and tags when a user selects a library prompt.

## Prompt library structure
Each prompt entry includes:

- `id`: A unique slug (e.g., `init_charter`, `plan_wbs`, `risk_identification`).
- `label`: A short description shown in the assistant panel.
- `description`: The full prompt sent to the LLM.
- `tags`: Categories and methodology phases (e.g., `initiation`, `planning`, `risk`, `procurement`).

## How prompts are categorized
Prompts are filtered by the current methodology stage to keep suggestions relevant:

- **Initiation** prompts show during initiation activities.
- **Planning** prompts show during planning activities.
- **Execution & Monitoring** prompts show during execution or monitoring activities.
- **Procurement/Vendor** and **Compliance** prompts show when their tags apply, with general prompts (such as risk identification and vendor evaluation) always available.

## Managing prompts
1. Go to **Configuration → Prompt Library** to create new prompts (label, description, tags).
2. Edit or delete existing prompts from the manager or directly in the assistant panel.
3. Updates are saved locally so the latest prompt content appears in the assistant panel immediately.

## Using prompts in the assistant panel
1. Open the assistant panel and review the “Next actions” prompt chips.
2. Use the search box to filter prompts by keyword, tag, or description.
3. Click a prompt chip to insert its full description into the chat input.
4. Submit the message to send the prompt to the orchestrator.

## Orchestrator integration
When a prompt is submitted, the orchestrator includes the prompt `id`, `description`, and `tags` in the payload sent to the relevant domain agent. For prompts that require external research (such as vendor evaluation or compliance scans), the orchestrator calls the existing search service to gather relevant information and includes a summarized research context in the agent request.
