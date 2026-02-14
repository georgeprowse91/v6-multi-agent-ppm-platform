import type { MethodologyMap, ProjectMethodology } from './types';

const mkStage = (id: string, name: string, order: number, prereq?: string) => ({
  id,
  name,
  status: 'not_started' as const,
  prerequisites: prereq ? [prereq] : [],
  order,
  activities: [],
});

export const predictiveMethodology: MethodologyMap = {
  id: 'predictive',
  name: 'Predictive',
  description: 'Sequential phases with stage-gate governance.',
  type: 'waterfall',
  version: '2.0',
  stages: [
    mkStage('0.1-demand-intake-triage', 'Demand Intake & Triage', 1),
    mkStage('0.2-portfolio-assessment-prioritisation', 'Portfolio Assessment & Prioritisation', 2, '0.1-demand-intake-triage'),
    mkStage('0.3-initiation', 'Initiation', 3, '0.2-portfolio-assessment-prioritisation'),
    mkStage('0.4-planning', 'Planning', 4, '0.3-initiation'),
    mkStage('0.5-execution', 'Execution', 5, '0.4-planning'),
    mkStage('0.6-monitoring-controlling', 'Monitoring & Controlling', 6, '0.5-execution'),
    mkStage('0.7-closure', 'Closure', 7, '0.6-monitoring-controlling'),
  ],
};

export const adaptiveMethodology: MethodologyMap = {
  id: 'adaptive',
  name: 'Adaptive',
  description: 'Agile lifecycle with repeatable sprint cycle.',
  type: 'agile',
  version: '2.0',
  stages: [
    mkStage('0.1-demand-intake-triage', 'Demand Intake & Triage', 1),
    mkStage('0.2-portfolio-assessment-prioritisation', 'Portfolio Assessment & Prioritisation', 2, '0.1-demand-intake-triage'),
    mkStage('0.3-adaptive-initiation', 'Adaptive Initiation', 3, '0.2-portfolio-assessment-prioritisation'),
    mkStage('0.4-discovery-definition', 'Discovery & Definition', 4, '0.3-adaptive-initiation'),
    mkStage('0.5-iteration-sprint-delivery', 'Iteration/Sprint Delivery', 5, '0.4-discovery-definition'),
    mkStage('0.6-release-planning-deployment', 'Release Planning & Deployment', 6, '0.5-iteration-sprint-delivery'),
    mkStage('0.7-product-ops-lifecycle', 'Product Ops & Lifecycle', 7, '0.6-release-planning-deployment'),
    mkStage('0.8-governance-monitoring-controls', 'Governance, Monitoring & Controls', 8, '0.7-product-ops-lifecycle'),
    mkStage('0.9-closure-transition', 'Closure/Transition', 9, '0.8-governance-monitoring-controls'),
  ],
};

export const hybridMethodology: MethodologyMap = {
  id: 'hybrid',
  name: 'Hybrid',
  description: 'Hybrid stage-gated + iterative lifecycle.',
  type: 'hybrid',
  version: '2.0',
  stages: [
    mkStage('0.1-demand-intake-triage', 'Demand Intake & Triage', 1),
    mkStage('0.2-portfolio-assessment-prioritisation', 'Portfolio Assessment & Prioritisation', 2, '0.1-demand-intake-triage'),
    mkStage('0.3-mobilisation-governance-setup', 'Mobilisation & Governance Setup', 3, '0.2-portfolio-assessment-prioritisation'),
    mkStage('0.4-high-level-definition-baselines', 'High-Level Definition & Baselines', 4, '0.3-mobilisation-governance-setup'),
    mkStage('0.5-discovery-detailed-planning-release', 'Discovery & Detailed Planning by Release', 5, '0.4-high-level-definition-baselines'),
    mkStage('0.6-iterative-build-test-sprints', 'Iterative Build & Test (Sprints)', 6, '0.5-discovery-detailed-planning-release'),
    mkStage('0.7-stage-gate-assurance-control', 'Stage-Gate Assurance & Control (Parallel)', 7),
    mkStage('0.8-release-readiness-deployment-transition', 'Release Readiness, Deployment & Transition', 8, '0.6-iterative-build-test-sprints'),
    mkStage('0.9-closure-benefits-realisation', 'Closure & Benefits Realisation', 9, '0.8-release-readiness-deployment-transition'),
  ],
};

export const methodologyTemplates: MethodologyMap[] = [predictiveMethodology, adaptiveMethodology, hybridMethodology];

export const projectApolloMethodology: ProjectMethodology = {
  projectId: 'project-apollo',
  projectName: 'Project Apollo',
  methodology: predictiveMethodology,
  currentActivityId: null,
  expandedStageIds: ['0.1-demand-intake-triage'],
};
