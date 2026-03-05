# Change Management

> This section covers the organisational enablement needed to successfully adopt the Multi-Agent PPM platform: a consolidated delivery reference combining completed phases, milestones, resource plan, and the change-management programme; and a practical phased training plan designed for execution by delivery, PMO, and support teams.

## Contents

- [Implementation and Change Plan](#implementation-and-change-plan)
- [Training Plan](#training-plan)

---

## Implementation and Change Plan

**Owner:** Delivery Lead / Change Management Lead
**Last reviewed:** 2026-02-20
**Related docs:** [Acceptance and Test Strategy](../testing/README.md#acceptance-and-test-strategy) · [User Journeys and Stage Gates](../01-product-definition/user-journeys-and-stage-gates.md)

> **Migration note:** Consolidated from `success-metrics.md` (delivery phases, milestones, resource plan) and `solution-overview/change-management-training.md` (organisational enablement) on 2026-02-20.

---

### Part 1 — Delivery phases, milestones, and resource plan

This delivery summary captures the completed phases and milestones that enabled the multi-agent PPM platform to launch with enterprise authentication, RBAC, enhanced vendor procurement workflows, an IoT connector, and refreshed UX. The resource plan reflects the cross-functional staffing that supported delivery, and the ongoing success metrics ensure the platform continues to meet client needs in production.

#### Overview

The platform delivers a comprehensive AI-enabled project portfolio management solution. Given the complexity of orchestrating dozens of specialised agents and integrating with multiple enterprise systems, a phased delivery plan and clear resource plan were critical. Interoperability has been identified as crucial for adoption, and resilience is supported by Azure Monitor's multi-zone replication. The completed delivery phases reflect these priorities.

#### Completed phases and milestones

| Phase | Duration (Weeks) | Objectives and Key Deliverables | Milestones |
| --- | --- | --- | --- |
| 0. Initiation and Planning | 2–4 | Finalised vision and scope; defined success metrics and KPIs; developed business case and secured budget. Identified stakeholders, appointed product owner and project manager. Created high-level backlog of features and agents. | Project charter signed; backlog and release plan approved. |
| 1. Architecture and Design | 4–8 | Designed system architecture: multi-agent orchestration layer, data pipeline, connector framework, security model. Defined data model and schemas; created entity relationships and metadata definitions. Produced detailed agent specifications (25 agents). Designed UI/UX wireframes and style guides. Confirmed compliance requirements (encryption, RBAC). | Architecture design review complete; data model and agent specs baseline; design sign-off. |
| 2. Core Platform and Infrastructure Setup | 8–12 | Provisioned Azure environments (dev/test/stage/prod), including AKS clusters, storage, databases, monitoring, and logging infrastructure. Implemented foundational services: API gateway, identity and access management, orchestration engine skeleton, connector framework scaffold. Established CI/CD pipelines and infrastructure as code. Implemented security baseline (encryption, authentication, RBAC, MFA). | Infrastructure ready; orchestration engine and connector framework skeleton deployed; CI/CD pipeline operational; security controls validated. |
| 3. Agent Development and Integration (multiple sprints) | 12–24 | Developed agents in prioritised batches, starting with foundational agents (Intent Router, Response Orchestration, Demand and Intake, Schedule and Planning, Resource and Capacity, Financial Management) and integrating core systems (Planview, Jira, SAP/Workday). Built UI components for each agent including updated dashboards and navigation. Delivered advanced agents (Business Case, Portfolio Strategy, Program Management, Risk, Quality, Compliance, Vendor, Knowledge, Analytics) plus the IoT connector and vendor procurement enhancements. Completed unit and integration testing of each agent and connector. | Completion of each agent batch; connectors validated; UI components functional; integration test reports; demonstration of end-to-end workflows. |
| 4. Data Migration and Pilot | 4–8 | Analysed existing data sources; mapped fields to data model; prepared cleansing and transformation scripts. Executed data migration to staging environment; validated data quality and lineage. Deployed platform to pilot users. Conducted user training and gathered feedback. Refined configurations and fixed issues. | Pilot launch; data migration completed; pilot feedback report; updated backlog. |
| 5. UAT and Hardening | 4–6 | Performed user acceptance testing across all functionality. Executed performance tests, security tests, and failover drills. Fixed defects and finalised documentation. | UAT sign-off; performance and security tests passed; release candidate ready. |
| 6. Production Deployment and Rollout | 4–6 | Deployed platform to production environment; integrated with enterprise IdP, email, messaging, and financial systems. Executed cut-over plan and communicated go-live. Provided hyper-care support and monitored adoption metrics. Completed initial rollout to additional teams and business units in waves. | Go-live complete; early adoption metrics tracked; initial support issues resolved. |
| 7. Continuous Improvement and Support (ongoing) | Ongoing | Operate and monitor the platform. Release incremental enhancements and refine based on feedback. Conduct periodic DR drills and performance tuning. Provide training for new users and maintain change-management programmes. | Quarterly release cycles; adoption and performance reports; updated training materials. |

#### Dependencies and critical path (resolved)

- **Stakeholder alignment:** Executive and PMO leadership alignment secured budget approval and adoption sponsorship.
- **Third-party integrations:** Connectors for Planview, Jira, SAP, Workday, ServiceNow, and the IoT ingestion pipeline were delivered early to unblock agent functionality.
- **Data quality and migration:** The canonical data model was finalised before migration scripts were completed. Clean, consistent data remains critical to agent accuracy and ROI.
- **Security and compliance:** Encryption, authentication, RBAC, and audit logging were delivered before production deployment. Regulatory approvals cleared the go-live gate.
- **Resource availability:** Specialised roles (LLM engineers, integration engineers) were staffed early to avoid schedule risk.

#### Resource plan

**Team structure**

| Role | Scope |
| --- | --- |
| Product Owner / Sponsor (1 FTE) | Owns vision, prioritises backlog, liaises with stakeholders. |
| Project Manager / Scrum Master (1 FTE) | Coordinates schedule, manages risks, tracks progress and dependencies. |
| Solution Architect (1 FTE) | Oversees system architecture, data model, security design, and integration patterns. |
| Data Architect (0.5–1 FTE) | Designs data model and schemas, defines data lineage and quality processes. |
| LLM/AI Engineer (1 FTE) | Responsible for integrating and fine-tuning LLMs, building AI models for scheduling, risk prediction, etc. |
| Backend Engineers (3–5 FTE) | Develop microservices, agents, and APIs; implement orchestration logic. |
| Frontend/UX Engineers (2–3 FTE) | Build UI components, dashboards, and interactive canvases; work closely with designers. |
| Integration Engineers (2–3 FTE) | Develop connectors to external systems, handle data mapping, and manage API changes. |
| DevOps Engineers (1–2 FTE) | Set up CI/CD pipelines, infrastructure automation, monitoring, and scaling. |
| QA/Test Engineers (2–3 FTE) | Design test plans (unit, integration, performance, UAT), automate tests, and manage defects. |
| Security and Compliance Specialist (0.5–1 FTE) | Implements security controls, manages compliance, conducts vulnerability assessments. |
| Change Management and Training Lead (1 FTE) | Develops communication strategy, training programmes, and monitors adoption. |
| Support Analysts (2 FTE) | Provide Level 1/2 support during pilots and post-launch; triage incidents and gather user feedback. |

FTE numbers can scale up or down based on organisational size and outsourcing. During heavy development (Phase 3), additional backend and integration engineers may be needed; later phases require more support and training staff.

**Staffing by phase (indicative FTE):**

| Role | Phase 0–1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 | Phase 7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Product Owner | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| Project Manager | 0.5 | 1 | 1 | 1 | 1 | 1 | 0.5 |
| Solution Architect | 0.5 | 1 | 0.75 | 0.5 | 0.25 | 0.25 | 0.25 |
| Data Architect | 0.25 | 0.5 | 0.75 | 0.5 | 0.25 | 0.25 | 0.25 |
| LLM/AI Engineer | 0.25 | 0.5 | 1 | 1 | 0.75 | 0.5 | 0.5 |
| Backend Engineers | 0 | 2 | 4 | 3 | 2 | 1 | 1 |
| Frontend/UX Engineers | 0 | 1 | 2 | 2 | 1 | 1 | 1 |
| Integration Engineers | 0 | 1 | 2 | 2 | 1 | 1 | 0.5 |
| DevOps Engineers | 0 | 1 | 1.5 | 1 | 1 | 1 | 1 |
| QA/Test Engineers | 0 | 0.5 | 2 | 2 | 2 | 1 | 1 |
| Security and Compliance | 0 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| Change Management and Training | 0 | 0 | 0.5 | 1 | 1 | 1 | 1 |
| Support Analysts | 0 | 0 | 0 | 1 | 2 | 2 | 2 |

#### Tracking progress

- **Sprint planning and retrospectives:** Use Adaptive ceremonies to plan tasks, review progress, and address impediments. Maintain a programme backlog with epics for each agent and feature.
- **Milestone reviews:** At the end of each phase or release, hold a review session to evaluate deliverables against objectives, update the roadmap, and adjust resource allocation.
- **Metrics and KPIs:** Track burn-down charts, velocity, defect leakage, test coverage, and adoption metrics. Monitor the health of integrations and data pipelines including authentication success rates, RBAC policy adherence, IoT connector throughput, procurement cycle time, and UX task completion times.
- **Risk and dependency log:** Maintain a live register of risks (technical, commercial, adoption) and dependencies. Assign owners and mitigation actions.

---

### Part 2 — Change management and training plan

> **Implementation alignment note:** Validate feature claims against the current implementation in the solution index and architecture/runbook documentation before using this section for delivery commitments.

Change management is essential for successful digital transformation. The plan is built on the five Cs of change (communication, collaboration, commitment, clarity, and continuous improvement) and emphasises transparency, role-specific training, and ongoing feedback. It also addresses the AI adoption gap: an IPMA survey found that 42% of project managers are not using AI and only 23% are actively using it, highlighting the need for targeted training and confidence building.

#### 1. Assess readiness and vision

- **Stakeholder analysis:** Identify sponsors, champions, and affected user groups (executives, PMO, project managers, resource managers, finance, vendors). Assess their readiness, pain points, and expectations.
- **Define the vision and objectives:** Articulate how the platform will improve portfolio visibility, decision-making, and efficiency. Tie outcomes to organisational goals (faster project approval cycles, improved resource utilisation, reduced budget overruns).
- **Success metrics:** Establish KPIs such as adoption rate, user satisfaction, reduction in manual effort, improved forecast accuracy, and ROI.

#### 2. Communication strategy

- **Transparency and consistency:** Provide clear, consistent messages on the platform's purpose, benefits, and timeline. Address concerns around job impact and emphasise that agents augment—not replace—project professionals.
- **Tailored messaging:** Segment communications by role and maturity. Executives want strategic ROI and risk reduction; project managers need to understand daily workflows; IT teams must know technical implications.
- **Channels and cadence:** Use multiple channels (town halls, intranet posts, newsletters, Teams/Slack, email, webinars). Communicate early and often, especially before major milestones. Provide real-time updates during deployment and weekly status during pilots.
- **Feedback loops:** Encourage two-way communication via surveys, Q&A sessions, and community forums. Share responses and updates to build trust.

#### 3. Training programme

Training materials should include:

- **Onboarding kit:** Welcome emails, platform overview, login instructions, role-based quick start guides, and cheat sheets.
- **Interactive tutorials:** In-app guidance and tooltips with contextual help.
- **Video micro-learning:** Short videos (3–5 minutes) covering specific features or workflows. Provide transcripts and captions for accessibility.
- **Case studies and hands-on labs:** Use real or anonymised project data to walk through common scenarios (e.g., creating a business case, running portfolio optimisation). Encourage experimentation in a sandbox environment.
- **Certification and badges:** Offer optional certification paths (e.g., "Certified PPM Platform Practitioner") to motivate learning and recognise proficiency.
- **Continuous learning:** Provide refresher sessions, advanced modules (e.g., building custom metrics), and office hours. Highlight new features after each release.

**Role-based training matrix:**

| Audience | Training Components | Delivery Methods |
| --- | --- | --- |
| Executives and Sponsors | Vision briefing, ROI demonstration, governance model, dashboard overview | Executive workshops, briefing decks, interactive dashboards, recorded demos |
| PMO and Project Managers | End-to-end project lifecycle flows, use of agents (intent router, scheduling, resource management, risk), methodology map navigation, approval workflows | Instructor-led workshops, interactive webinars, self-paced e-learning, sandbox exercises, scenario-based simulations |
| Financial and Resource Analysts | Budgeting and forecasting features, integration with finance systems, resource planning and capacity, cost-benefit analysis | Hands-on labs, guided walk-throughs, how-to videos |
| Team Members and Contributors | Task management, sprint planning, collaboration features, notifications, self-service analytics | Quick start guides, in-app walk-throughs, micro-learning modules |
| IT and Integration Teams | Architecture overview, connector configuration, APIs, security and compliance controls | Technical documentation, configuration workshops, office hours with engineering |

#### 4. Implementation timeline

| Phase | Duration | Focus |
| --- | --- | --- |
| Phase 0: Preparation | 2–4 weeks | Assess readiness, appoint change champions, define KPIs, prepare communications and onboarding materials. |
| Phase 1: Pilot | 4–8 weeks | Roll out to a small group of power users and PMO members. Collect feedback via surveys and analytics. Refine training and processes. |
| Phase 2: Initial Deployment | 8–12 weeks | Expand to selected programmes or departments. Continue training and communication. Monitor adoption metrics and user sentiment. |
| Phase 3: Enterprise Rollout | 12–20 weeks | Deploy across the organisation. Conduct targeted workshops, provide additional support, and track KPIs. |
| Phase 4: Optimisation and Continuous Improvement | Ongoing | Review analytics and feedback, fine-tune processes, and schedule refresher trainings. Plan for onboarding new users and integrating additional agents. |

#### 5. Monitoring and measurement

Track the following metrics using analytics dashboards, reviewing results with sponsors and adjusting the plan accordingly:

- **Adoption and usage:** Number of active users, log-ins by role, feature usage, and completion of training modules.
- **Engagement and sentiment:** Survey results, NPS, qualitative feedback, participation in forums and Q&A sessions.
- **Performance and efficiency:** Reduction in manual tasks, cycle time for approvals, forecast accuracy, number of risks identified.
- **Value realisation:** Financial benefits such as cost avoidance, improved margins, or return on investment.
- **Learning outcomes:** Pass rate for certification exams, average scores on assessments, completion rates.

#### 6. Continuous improvement and sustainability

- **Refine and adapt:** Regularly review feedback, analytics, and lessons learned to identify gaps. Update training materials, communication strategies, and runbooks accordingly.
- **Change champions network:** Establish a community of super users and champions who provide peer support, gather feedback, and suggest improvements. Recognise and reward champions.
- **Leadership involvement:** Maintain visible leadership support and celebrate milestones. Provide executives with adoption metrics and success stories.
- **Integration of new hires:** Incorporate the platform into onboarding for new employees. Provide access to training resources and assign a mentor.
- **Governance:** Align changes with governance frameworks. Ensure change requests, enhancements, and new releases follow a standard process with approval gates. Keep an up-to-date change log accessible to all stakeholders.

#### Communication artefacts

| Artefact | Description |
| --- | --- |
| Change-management charter | Outlines objectives, scope, stakeholders, roles, and success metrics. |
| Communication plan | A living document detailing messages, audiences, channels, frequency, and owners. |
| Training curriculum | Matrix of training modules, target audiences, delivery methods, and prerequisites. |
| Onboarding guide | Step-by-step instructions for new users including login, initial setup, and orientation. |
| FAQ and knowledge base | Common questions, troubleshooting tips, and best practices accessible via the support portal. |
| Adoption dashboard | Real-time view of training completion, adoption metrics, and user feedback for sponsors and change leaders. |

---

## Training Plan

This training plan summarises the phased rollout and enablement strategy for adopting the Multi-Agent PPM platform. It is designed for practical execution by delivery, PMO, and support teams.

### Objectives

- Build role-based proficiency before each rollout wave.
- Increase adoption and confidence with agent-assisted workflows.
- Reduce time-to-productivity for new and existing users.
- Sustain capability through continuous learning after go-live.

### Rollout phases and training strategy

#### Phase 0: Preparation (2–4 weeks)

**Purpose:** Establish readiness and produce core enablement assets before the pilot.

**Training focus**
- Create role-based curriculum (executives, PMO/PMs, analysts, contributors, IT/integration).
- Publish onboarding kit (access instructions, quick starts, common workflows).
- Prepare facilitator guides, sandbox scenarios, and assessment criteria.

**Delivery methods**
- Change champion briefings.
- Train-the-trainer workshops.
- Introductory webinars and orientation sessions.

**Exit criteria**
- Curriculum and schedule approved.
- Training materials published and accessible.
- Champions and trainers assigned.

---

#### Phase 1: Pilot (4–8 weeks)

**Purpose:** Validate training effectiveness with a small representative cohort.

**Training focus**
- Hands-on workshops using real or anonymised pilot scenarios.
- Core workflow competence: project setup, planning, approvals, reporting.
- Agent usage guardrails and escalation/support paths.

**Delivery methods**
- Instructor-led sessions.
- Sandbox labs and guided exercises.
- Office hours and Q&A forums.

**Exit criteria**
- Pilot participants complete baseline modules.
- Feedback captured and curriculum refined.
- Common issues documented in FAQ/knowledge base.

---

#### Phase 2: Initial Deployment (8–12 weeks)

**Purpose:** Expand adoption to selected programmes/departments with targeted reinforcement.

**Training focus**
- Role-specific deep dives (resource planning, forecasting, risk workflows, connector operations).
- Manager enablement for KPI interpretation and governance workflows.
- Operational readiness for support and incident handoff.

**Delivery methods**
- Blended learning (live webinars + self-paced modules).
- Micro-learning videos (3–5 minutes).
- Scenario-based simulations by business unit.

**Exit criteria**
- Departmental completion targets met.
- Adoption and usage metrics trending upward.
- Support team runbooks and escalation drills completed.

---

#### Phase 3: Enterprise Rollout (12–20 weeks)

**Purpose:** Standardise capability across the organisation at scale.

**Training focus**
- Enterprise-wide onboarding by persona.
- Governance, compliance, and audit-ready usage patterns.
- Advanced practices for power users and champions.

**Delivery methods**
- Scheduled cohort training.
- Recorded modules for asynchronous completion.
- Community of practice sessions.

**Exit criteria**
- Enterprise training coverage meets target.
- Champion network active in each major function.
- Stable operational KPIs after rollout waves.

---

#### Phase 4: Optimisation and Continuous Improvement (ongoing)

**Purpose:** Sustain adoption and continuously improve proficiency.

**Training focus**
- Refresher courses after releases.
- New feature enablement and delta training.
- New-hire onboarding pathway and mentorship.

**Delivery methods**
- Monthly office hours.
- Quarterly advanced workshops.
- Knowledge base updates and release walkthroughs.

**Exit criteria**
- Continuous learning cadence established.
- Content updates published with each release cycle.
- Measurable improvement in outcome KPIs.

---

### Role-based curriculum summary

| Audience | Priority Topics | Delivery Pattern |
| --- | --- | --- |
| Executives and Sponsors | Value realisation, ROI, governance dashboards, decision cadence | Short executive briefings + dashboard walkthroughs |
| PMO and Project Managers | End-to-end lifecycle workflows, approvals, portfolio optimisation, agent interactions | Instructor-led workshops + sandbox labs |
| Financial and Resource Analysts | Forecasting, budgeting, capacity planning, benefits tracking | Guided labs + targeted how-to modules |
| Team Members and Contributors | Task execution, collaboration, status updates, notifications | Quick starts + micro-learning |
| IT and Integration Teams | Architecture, connectors, APIs, security/compliance controls | Technical workshops + office hours |

### Measurement and governance

Track training effectiveness alongside rollout health:

- Completion rate by role, function, and region.
- Assessment pass rates and practical lab outcomes.
- Adoption metrics (active users, feature usage, workflow completion).
- Sentiment and confidence from surveys and support interactions.
- Time-to-proficiency for new users.

Use monthly governance reviews to prioritise curriculum updates, reinforce underperforming cohorts, and align training changes to release roadmap milestones.
