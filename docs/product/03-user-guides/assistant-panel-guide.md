# Assistant Panel Guide

**Purpose:** User-facing guide for interacting with the AI assistant panel, including the prompt library, interaction patterns, and how the orchestrator processes requests.
**Audience:** End users, project managers, PMO practitioners, and platform operators.
**Owner:** Product Design / AI Engineering
**Last reviewed:** 2026-03-01
**Related docs:** [Personas and UX Guidelines](../01-product-definition/personas-and-ux-guidelines.md) · [Web Console Walkthroughs](web-console-walkthroughs.md)

---

## Overview

The assistant panel is the right-hand panel of the platform's three-panel workspace. It provides a conversational interface where users interact with the platform in natural language. The assistant maintains the context of the current project, methodology stage, and activity, so its responses are always relevant and specific.

The panel includes a structured **prompt library** that provides reusable, context-aware prompts for common project management tasks. Prompts are stored in the browser (local storage) and surfaced in the UI as "Next actions" chips that align with the current project stage.

---

## Prompt Library Structure

Each prompt entry includes:

- **id** — A unique slug (e.g., `init_charter`, `plan_wbs`, `risk_identification`).
- **label** — A short description shown in the assistant panel.
- **description** — The full prompt sent to the LLM.
- **tags** — Categories and methodology phases (e.g., `initiation`, `planning`, `risk`, `procurement`).

---

## How Prompts Are Categorised

Prompts are filtered by the current methodology stage to keep suggestions relevant:

- **Initiation** prompts show during initiation activities.
- **Planning** prompts show during planning activities.
- **Execution & Monitoring** prompts show during execution or monitoring activities.
- **Procurement/Vendor** and **Compliance** prompts show when their tags apply, with general prompts (such as risk identification and vendor evaluation) always available.

---

## Using Prompts in the Assistant Panel

1. Open the assistant panel and review the "Next actions" prompt chips.
2. Use the search box to filter prompts by keyword, tag, or description.
3. Click a prompt chip to insert its full description into the chat input.
4. Submit the message to send the prompt to the orchestrator.

You can also type any free-form request. The orchestrator will route your query to the appropriate domain agents regardless of whether you use a library prompt.

---

## Managing Custom Prompts

1. Go to **Configuration > Prompt Library** to create new prompts (label, description, tags).
2. Edit or delete existing prompts from the manager or directly in the assistant panel.
3. Updates are saved locally so the latest prompt content appears in the assistant panel immediately.

---

## How the Orchestrator Processes Your Request

When you submit a message through the assistant panel:

1. The **Intent Router** agent analyses your query and identifies which domain agents are needed.
2. The **Response Orchestration** agent coordinates the relevant domain agents in the correct sequence.
3. For prompts that require external research (such as vendor evaluation or compliance scans), the orchestrator calls the search service to gather relevant context.
4. The orchestrated response is assembled and presented back to you in the assistant panel.

For technical architecture details of the orchestration system, see [Agent Orchestration Architecture](../../architecture/agent-orchestration.md).
