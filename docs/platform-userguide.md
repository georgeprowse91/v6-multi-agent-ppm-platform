# Platform User Guide

This document provides end-user guidance for operating the Multi-Agent PPM Platform, including the AI assistant panel, prompt library, and web console walkthrough experience.

**Owner:** Product Design / Platform Operations
**Last reviewed:** 2026-03-01

---

## Contents

- [Assistant Panel](#assistant-panel)
- [Prompt Library](#prompt-library)
- [Using Prompts](#using-prompts)
- [Managing Custom Prompts](#managing-custom-prompts)
- [How the Orchestrator Processes Requests](#how-the-orchestrator-processes-requests)
- [Web Console Walkthroughs](#web-console-walkthroughs)

---

## Assistant Panel

The assistant panel is the right-hand panel of the platform's three-panel workspace. It provides a conversational interface where users interact with the platform in natural language. The assistant maintains the context of the current project, methodology stage, and activity, so its responses are always relevant and specific.

The panel includes a structured prompt library that provides reusable, context-aware prompts for common project management tasks. Prompts are stored in the browser (local storage) and surfaced in the UI as "Next actions" chips that align with the current project stage.

---

## Prompt Library

Each prompt entry includes:

- **id** -- A unique slug (e.g., `init_charter`, `plan_wbs`, `risk_identification`).
- **label** -- A short description shown in the assistant panel.
- **description** -- The full prompt sent to the LLM.
- **tags** -- Categories and methodology phases (e.g., `initiation`, `planning`, `risk`, `procurement`).

### How Prompts Are Categorised

Prompts are filtered by the current methodology stage to keep suggestions relevant:

- **Initiation** prompts show during initiation activities.
- **Planning** prompts show during planning activities.
- **Execution and Monitoring** prompts show during execution or monitoring activities.
- **Procurement/Vendor** and **Compliance** prompts show when their tags apply, with general prompts (such as risk identification and vendor evaluation) always available.

---

## Using Prompts

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

## How the Orchestrator Processes Requests

When you submit a message through the assistant panel:

1. The **Intent Router** agent analyses your query and identifies which domain agents are needed.
2. The **Response Orchestration** agent coordinates the relevant domain agents in the correct sequence.
3. For prompts that require external research (such as vendor evaluation or compliance scans), the orchestrator calls the search service to gather relevant context.
4. The orchestrated response is assembled and presented back to you in the assistant panel.

For technical architecture details of the orchestration system, see [Readme](architecture/README.md).

---

## Web Console Walkthroughs

The React web console includes a guided tour experience for new features and major UI updates. The walkthrough helps users find configuration, analytics, and assistant tools without relying on separate training materials.

### How Onboarding Works

- On first login (or when a new tour version is released), an onboarding modal appears.
- Selecting **Start walkthrough** launches the guided tour with step-by-step highlights.
- Users can defer the tour with **Maybe later** and replay it later from the Help menu.

### Replaying the Tour

1. Click **Help** in the top-right header.
2. Select **Start walkthrough** to replay the guided tour.

### What the Tour Covers

- Connector navigation and certification evidence tracking.
- Agent configuration pages.
- Workflow monitoring (analytics) surfaces.
- The AI assistant panel for context-aware support.

### Versioning Behaviour

Each tour release is versioned. If the UI introduces significant new functionality, the tour version is updated and the onboarding modal appears again, ensuring existing users see the latest walkthrough.

---

## Document Control

| Field | Details |
|---|---|
| Owner | Product Design / Platform Operations |
| Review cycle | Quarterly |
| Last reviewed | 2026-03-01 |
| Status | Active |
