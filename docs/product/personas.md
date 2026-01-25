# UI/UX Design Guidelines

## Introduction

The user interface of the multi‑agent PPM platform brings together complex agent interactions, methodology guidance and data visualisation into a seamless experience. This document outlines the key design patterns, component specifications and visual standards that ensure a consistent, intuitive and accessible user experience across web and mobile. It expands upon the layout described in the architecture document—where the methodology map, interactive canvas, left navigation and right contextual panels are central to the experience.

## Layout & Navigation

### Primary Regions

**Left Navigation Pane:** displays the hierarchical methodology map (phases for Waterfall or sprints for Agile) and provides quick access to major modules (Dashboard, Portfolio, Programs, Projects, Reports, Settings). The map highlights the current phase and upcoming stages, enabling users to see their progress. Collapsible sections allow users to focus on specific areas.

**Central Canvas:** the main workspace where users interact with agents and data. The canvas dynamically changes based on the selected phase or agent: for example, WBS tree with drag‑and‑drop for project definition, schedule Gantt chart, or business‑case form. Users can add, resize or reorder cards representing tasks, risks, approvals, or dashboards. The canvas supports multi‑select actions (e.g., bulk updates) and context menus.

**Right Contextual Panel:** shows details for the currently selected card or entity and hosts the conversational assistant. It surfaces hints, recommended actions, analytics and cross‑references, enabling users to interact with agents via chat or quick‑action buttons.

**Header:** includes global search, notifications, user profile, and environment selection (e.g., development, production). Breadcrumbs indicate the current location.

### Navigation Patterns

**Methodology Navigation:** clicking on a stage in the methodology map updates the canvas and context panel to reflect relevant work. Stage gates require specific criteria before proceeding; the UI displays gate status (Not started, In progress, Complete) with tooltips explaining required artefacts.

**Universal Search:** accessible via the header, it allows users to search across projects, tasks, documents and agents. Results are grouped by entity type and include quick actions (open, edit, assign).

**Contextual Commands:** right‑click menus and action bars provide contextual commands (edit, duplicate, delete) relative to the selected card or entity.

## Visual Style & Branding

**Colour Palette:** adopt a neutral base with accent colours aligned to the client’s brand. Use consistent colours for statuses (e.g., green for complete, amber for warning, red for overdue). Avoid using red and green together to support colour‑blind accessibility.

**Typography:** use a sans‑serif font for clarity and readability. Apply hierarchy through size, weight and colour. Headings should be bolder and larger than body text.

**Spacing & Alignment:** apply consistent margins and padding (8pt grid) to create balanced layouts. Use alignment guides to ensure elements line up across panels.

**Iconography:** use vector icons sparingly to represent common actions (add, edit, delete, filter). Icons should be simple and recognisable; avoid icons in the first two slides for presentations as per the slides guidelines.

**Responsiveness:** design layouts that adapt to different screen sizes (desktop, tablet, mobile). Collapse the left navigation into a hamburger menu on narrow screens; ensure cards rearrange into vertical stacks.

**Accessibility:** follow WCAG 2.1 guidelines: provide sufficient colour contrast, support keyboard navigation, include ARIA labels, and ensure interactive elements are reachable via tab order.

## Component Specifications

### Cards

Cards are the primary visual container for discrete pieces of information (e.g., project summary, risk, approval request). Each card includes:

**Title & Status:** clearly visible at the top, showing the entity name and current status with a coloured tag.

**Key Metrics:** display relevant metrics (e.g., budget vs actual, due date, assigned owner) using icons or small charts. Use sparklines to show trends.

**Actions:** contextual buttons (e.g., View details, Approve, Raise risk) appear on hover or in a menu. Avoid cluttering the card with too many buttons.

**Badges & Indicators:** small badges show count of comments, attachments or notifications.

### Tables & Lists

Use tables to display structured data such as resource allocations, financial transactions or risk registers. Tables include column sorting, filters, pagination and inline editing. Sticky headers improve readability. Provide bulk action capability (select multiple rows, apply action).

### Gantt & Timeline Views

The Schedule & Planning module uses interactive Gantt charts to visualise tasks, milestones, dependencies and progress. Features include drag‑and‑drop adjustments, critical path highlighting, grouping by resource or phase, zoom controls and baseline overlays. In agile mode, timeline view can switch to a sprint board with columns for backlog, in progress and done.

### Forms & Wizards

For data entry (business cases, resource requests, compliance forms), use multi‑step wizards that guide users through sections with progress indicators. Validate fields in real time and provide contextual help. Use dynamic fields that appear based on prior selections.

### Dashboards & Reports

Provide preconfigured dashboards for key personas (executives, PMO, project managers) with interactive charts and KPIs. Allow users to customise layouts, add or remove widgets and save personal views. Charts should support hover details, drill‑downs and export to Excel/PDF.

## Interaction with Agents

The UI integrates with agents seamlessly:

**Conversational Assistant:** accessible via the context panel or a floating button, the assistant accepts natural‑language queries. It suggests clarifying questions, summarises results, and triggers multi‑agent workflows (e.g., generate business case, optimise portfolio). The conversation history remains visible for context.

**Agent Notifications:** agents can send proactive notifications (approval requests, risk alerts, data quality issues). The notification centre lists messages with links to the relevant card or page. Unread counts and filtering ensure important items are not missed.

**Inline Recommendations:** certain agents provide inline guidance (e.g., risk agent highlighting high‑risk tasks in red, quality agent recommending additional tests). Recommendations include tooltips explaining why an action is suggested and allow users to accept or dismiss them.

## Style Guide

This guide ensures consistency across all pages and modules. Use it as the foundation for building custom components.

## Wireframes & Mockups

Sample wireframes and mockups accompany this document (see ui_ux_design_artefacts.md and the associated images). They illustrate the layout and interactions described above for dashboards, canvas views, timelines and assistant panels. Use these as a baseline and customise colours, typography and imagery to align with your organisation’s brand.

## Conclusion

A cohesive and accessible UI/UX is essential for user adoption and productivity. By adhering to the layouts, design principles and components defined in this document, the platform can deliver a consistent, intuitive experience that guides users through complex project and portfolio management processes.


---


**Table 1**

| Element | Specification |

| --- | --- |

| Primary Font | Open Sans (fallback: Arial, sans‑serif) |

| Base Font Size | 14 pt for body text |

| Heading Levels | H1: 24 pt, H2: 20 pt, H3: 16 pt |

| Accent Colour | #0066CC (hyperlinks, call‑to‑action) |

| Neutral Colour | #F5F5F5 background, #333333 text |

| Border Radius | 4 px for cards, inputs and buttons |

| Shadow | subtle drop shadow (2 px y, 4 px blur) |
