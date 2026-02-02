import type { PromptDefinition } from '@/types/prompt';

export const defaultPrompts: PromptDefinition[] = [
  {
    id: 'init_charter',
    label: 'Generate project charter',
    description:
      'You are a PMP-certified project manager. Using the high-level objectives, write a complete project charter including objectives, scope boundaries, stakeholders, high-level risks, assumptions, and success criteria.',
    tags: ['initiation'],
  },
  {
    id: 'stakeholder_register',
    label: 'Draft stakeholder register',
    description:
      'Create a stakeholder register for the project. Identify primary stakeholders, their roles, influence level, interests, and preferred communication channels.',
    tags: ['initiation'],
  },
  {
    id: 'business_case_summary',
    label: 'Summarize business case',
    description:
      'Summarize the business case by outlining the problem statement, expected benefits, strategic alignment, and high-level costs and risks.',
    tags: ['initiation'],
  },
  {
    id: 'requirements_decomposition',
    label: 'Decompose scope into requirements',
    description:
      'Break the high-level project scope into detailed, testable requirements. Group requirements by feature area and call out assumptions or dependencies.',
    tags: ['planning', 'scope'],
  },
  {
    id: 'plan_wbs',
    label: 'Generate work breakdown structure',
    description:
      'Create a detailed work breakdown structure (WBS) from the project scope. Include major deliverables, sub-deliverables, and work packages with clear ownership suggestions.',
    tags: ['planning', 'scope'],
  },
  {
    id: 'risk_identification',
    label: 'Identify project risks',
    description:
      'Develop a risk register by identifying potential risks, their causes, probability, impact, and recommended mitigation strategies.',
    tags: ['planning', 'risk', 'general'],
  },
  {
    id: 'schedule_development',
    label: 'Draft project schedule',
    description:
      'Produce a high-level project schedule with key milestones, dependencies, and estimated durations. Highlight the critical path if applicable.',
    tags: ['planning', 'schedule'],
  },
  {
    id: 'resource_planning',
    label: 'Define resource plan',
    description:
      'Create a resource plan that outlines required roles, skill sets, estimated effort, and resource allocation by phase.',
    tags: ['planning', 'resources'],
  },
  {
    id: 'status_report',
    label: 'Update status report',
    description:
      'Generate a concise status report covering progress against milestones, key accomplishments, upcoming work, issues, and decisions needed.',
    tags: ['execution', 'monitoring'],
  },
  {
    id: 'meeting_notes_summary',
    label: 'Summarize meeting notes',
    description:
      'Summarize the latest meeting notes into key decisions, action items, owners, and due dates. Flag any escalations or risks mentioned.',
    tags: ['execution', 'monitoring', 'communication'],
  },
  {
    id: 'risk_update_events',
    label: 'Identify new risks from events',
    description:
      'Review recent project events and identify any new risks or issues. Update the risk register with triggers and recommended responses.',
    tags: ['monitoring', 'risk'],
  },
  {
    id: 'backlog_adjustment',
    label: 'Adjust delivery backlog',
    description:
      'Assess the current backlog and propose adjustments based on recent progress, priority shifts, and capacity constraints. Provide an updated backlog order.',
    tags: ['execution', 'monitoring', 'agile'],
  },
  {
    id: 'vendor_research',
    label: 'Research potential vendors',
    description:
      "Research potential vendors that could meet the project requirements. Summarize each vendor's capabilities, differentiators, and notable risks.",
    tags: ['procurement', 'vendor'],
  },
  {
    id: 'rfp_template',
    label: 'Build RFP template',
    description:
      'Draft an RFP template that includes project background, scope, technical requirements, evaluation criteria, and submission timelines.',
    tags: ['procurement'],
  },
  {
    id: 'vendor_evaluation',
    label: 'Evaluate vendors with scoring',
    description:
      'Create a vendor evaluation matrix with weighted scoring criteria. Apply it to shortlisted vendors and recommend the top options.',
    tags: ['procurement', 'vendor', 'general'],
  },
  {
    id: 'compliance_updates',
    label: 'Scan regulatory updates',
    description:
      'Identify recent regulatory or compliance changes relevant to the project domain. Summarize impacts and recommended actions.',
    tags: ['compliance'],
  },
  {
    id: 'compliance_checklist',
    label: 'Generate compliance checklist',
    description:
      'Produce a compliance checklist that maps applicable regulations to required controls, evidence, and owners.',
    tags: ['compliance'],
  },
];

export default defaultPrompts;
