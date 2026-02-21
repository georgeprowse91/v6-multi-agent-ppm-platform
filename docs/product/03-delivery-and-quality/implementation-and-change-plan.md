# Implementation and Change Plan

**Purpose:** Consolidated delivery reference covering completed phases, milestones, resource plan, and the organisational change-management and training programme needed to successfully adopt the platform.
**Audience:** Project sponsors, PMO leads, delivery managers, change management leads, and training coordinators.
**Owner:** Delivery Lead / Change Management Lead
**Last reviewed:** 2026-02-20
**Related docs:** [acceptance-and-test-strategy.md](acceptance-and-test-strategy.md) · [compliance-evidence-process.md](compliance-evidence-process.md) · [../01-product-definition/user-journeys-and-stage-gates.md](../01-product-definition/user-journeys-and-stage-gates.md)

> **Migration note:** Consolidated from `success-metrics.md` (delivery phases, milestones, resource plan) and `solution-overview/change-management-training.md` (organisational enablement) on 2026-02-20.

---

## Part 1 — Delivery Phases, Milestones and Resource Plan

> *Source: `success-metrics.md`*

# Success Metrics & Delivery Summary

This document summarises the completed delivery phases, key milestones, resolved dependencies and staffing requirements used to deliver the multi‑agent PPM platform. It also highlights the success metrics now tracked for ongoing operations, including completed authentication and RBAC enforcement, the IoT connector, enhanced vendor procurement workflows and refreshed UI experiences.

## Overview

The platform delivers a comprehensive, AI‑enabled project portfolio management solution. Given the complexity of orchestrating dozens of specialised agents and integrating with multiple enterprise systems, a phased delivery plan and clear resource plan were critical. Interoperability has been identified as crucial for adoption[1] and resilience is supported by features like Azure Monitor’s multi‑zone replication[2]. The completed delivery phases reflect these priorities.

## Completed Phases and Milestones

## Dependencies & Critical Path (Resolved)

**Stakeholder Alignment:** Executive and PMO leadership alignment secured budget approval and adoption sponsorship, addressing known AI strategy barriers[4].

**Third‑Party Integrations:** Connectors for Planview, Jira, SAP, Workday, ServiceNow and the IoT ingestion pipeline were delivered early to unblock agent functionality.

**Data Quality & Migration:** The canonical data model was finalised before migration scripts were completed. Clean, consistent data remains critical to agent accuracy and ROI.

**Security & Compliance:** Encryption, authentication, RBAC and audit logging were delivered before production deployment[3]. Regulatory approvals (e.g., privacy assessments) cleared the go‑live gate.

**Resource Availability:** Specialised roles (e.g., LLM engineers, integration engineers) were staffed early to avoid schedule risk.

## Resource Plan

### Team Structure

**Product Owner / Sponsor (1 FTE):** Owns vision, prioritises backlog, liaises with stakeholders.

**Project Manager / Scrum Master (1 FTE):** Coordinates schedule, manages risks, tracks progress and dependencies.

**Solution Architect (1 FTE):** Oversees system architecture, data model, security design and integration patterns.

**Data Architect (0.5–1 FTE):** Designs data model & schemas, defines data lineage and quality processes.

**LLM/AI Engineer (1 FTE):** Responsible for integrating and fine‑tuning LLMs, building AI models for scheduling, risk prediction, etc.

**Backend Engineers (3–5 FTE):** Develop microservices, agents and APIs; implement orchestration logic.

**Frontend/UX Engineers (2–3 FTE):** Build UI components, dashboards, and interactive canvases; work closely with designers.

**Integration Engineers (2–3 FTE):** Develop connectors to external systems, handle data mapping, and manage API changes.

**DevOps Engineers (1–2 FTE):** Set up CI/CD pipelines, infrastructure automation, monitoring, and scaling.

**Quality Assurance/Test Engineers (2–3 FTE):** Design test plans (unit, integration, performance, UAT), automate tests and manage defects.

**Security & Compliance Specialist (0.5–1 FTE):** Implements security controls, manages compliance, conducts vulnerability assessments.

**Change‑Management & Training Lead (1 FTE):** Develops communication strategy, training programmes and monitors adoption.

**Support Analysts (2 FTE):** Provide Level 1/2 support during pilots and post‑launch; triage incidents and gather user feedback.

FTE numbers can scale up or down based on organisational size and outsourcing. During the heavy development (Phase 3), additional backend and integration engineers may be needed; later phases require more support and training staff.

### Staffing by Phase

**Note:** FTE values are indicative and represent approximate allocation per phase.

## Tracking Progress

**Sprint planning & retrospectives:** Use Adaptive ceremonies to plan tasks, review progress and address impediments. Maintain a programme backlog with epics for each agent and feature.

**Milestone reviews:** At the end of each phase or release, hold a review session to evaluate deliverables against objectives, update the roadmap and adjust resource allocation.

**Metrics & KPIs:** Track burn‑down charts, velocity, defect leakage, test coverage, and adoption metrics. Monitor the health of integrations and data pipelines using dashboards, including authentication success rates, RBAC policy adherence, IoT connector throughput, procurement cycle time and UX task completion times.

**Risk & dependency log:** Maintain a live register of risks (technical, commercial, adoption) and dependencies. Assign owners and mitigation actions. Use the risk management plan as a guide.

## Conclusion

The delivery summary captures the completed phases and milestones that enabled the multi‑agent PPM platform to launch with enterprise authentication, RBAC, enhanced vendor procurement workflows, an IoT connector and refreshed UX. The resource plan reflects the cross‑functional staffing that supported delivery, and the ongoing success metrics ensure the platform continues to meet client needs in production.

[1] 10 AI Agent Statistics for 2026: Adoption, Success Rates, & More

https://www.multimodal.dev/post/agentic-ai-statistics

[2] Best practices for Azure Monitor Logs - Azure Monitor | Microsoft Learn

https://learn.microsoft.com/en-us/azure/azure-monitor/logs/best-practices-logs

[3] Best Practices for Maximizing Data Security with Azure Backup | Cloudvara

https://cloudvara.com/best-practices-for-maximizing-data-security-with-azure-backup/

[4] AI-Four-Key-Factors-Report-v1-April-2024.pdf

https://pmi-ireland.org/static/uploaded/Files/Documents/AI-Four-Key-Factors-Report-v1-April-2024.pdf


---


**Table 1**

| Phase | Duration (Weeks) | Objectives & Key Deliverables | Milestones |

| --- | --- | --- | --- |

| 0. Initiation & Planning | 2–4 | • Finalised vision and scope; defined success metrics and KPIs; developed business case and secured budget. • Identified stakeholders, appointed product owner and project manager. • Created high‑level backlog of features and agents. | Project charter signed; backlog and release plan approved. |

| 1. Architecture & Design | 4–8 | • Designed system architecture: multi‑agent orchestration layer, data pipeline, connector framework, security model. • Defined data model & schemas; created entity relationships and metadata definitions. • Produced detailed agent specifications (25 agents). • Designed UI/UX wireframes and style guides. • Confirmed compliance requirements (e.g., encryption, RBAC)[3]. | Architecture design review complete; data model and agent specs baseline; design sign‑off. |

| 2. Core Platform & Infrastructure Setup | 8–12 | • Provisioned Azure environments (dev/test/stage/prod), including AKS clusters, storage, databases, monitoring & logging infrastructure. • Implemented foundational services: API gateway, identity & access management, orchestration engine skeleton, connector framework scaffold. • Established CI/CD pipelines and infrastructure as code. • Implemented security baseline (encryption, authentication, RBAC, MFA). | Infrastructure ready; orchestration engine & connector framework skeleton deployed; CI/CD pipeline operational; security controls validated. |

| 3. Agent Development & Integration (multiple sprints) | 12–24 | • Developed agents in prioritized batches, starting with foundational agents (Intent Router, Response Orchestration, Demand & Intake, Schedule & Planning, Resource & Capacity, Financial Management) and integrating core systems (Planview, Jira, SAP/Workday). • Built UI components for each agent, including updated dashboards and navigation. • Delivered advanced agents (Business Case, Portfolio Strategy, Program Management, Risk, Quality, Compliance, Vendor, Knowledge, Analytics) plus the IoT connector and vendor procurement enhancements. • Completed unit and integration testing of each agent and connector. | Completion of each agent batch; connectors validated; UI components functional; integration test reports; demonstration of end‑to‑end workflows. |

| 4. Data Migration & Pilot | 4–8 | • Analysed existing data sources; mapped fields to data model; prepared cleansing and transformation scripts. • Executed data migration to staging environment; validated data quality and lineage. • Deployed platform to pilot users (selected programs or departments). • Conducted user training and gathered feedback. • Refined configurations and fixed issues discovered. | Pilot launch; data migration completed; pilot feedback report; updated backlog. |

| 5. UAT & Hardening | 4–6 | • Performed user acceptance testing across all functionality. • Executed performance tests, security tests, and failover drills (leveraging Azure Monitor and backup resilience[2]). • Fixed defects and finalised documentation. | UAT sign‑off; performance and security tests passed; release candidate ready. |

| 6. Production Deployment & Rollout | 4–6 | • Deployed platform to production environment; integrated with enterprise IdP, email, messaging and financial systems. • Executed cut‑over plan and communicated go‑live. • Provided hyper‑care support and monitored adoption metrics. • Completed initial rollout to additional teams/business units in waves. | Go‑live complete; early adoption metrics tracked; initial support issues resolved. |

| 7. Continuous Improvement & Support (ongoing) | Ongoing | • Operate and monitor the platform. • Release incremental enhancements and refine based on feedback. • Conduct periodic DR drills and performance tuning. • Provide training for new users and maintain change‑management programmes. | Quarterly release cycles; adoption and performance reports; updated training materials. |



**Table 2**

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

| Security & Compliance | 0 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |

| Change Mgmt & Training | 0 | 0 | 0.5 | 1 | 1 | 1 | 1 |

| Support Analysts | 0 | 0 | 0 | 1 | 2 | 2 | 2 |


---

## Part 2 — Change Management and Training Plan

> *Source: `solution-overview/change-management-training.md`*

# Change Management & Training Plan

This plan provides a structured approach to guiding organisations through the adoption of the multi‑agent PPM platform. It combines change‑management principles with comprehensive training and communication strategies to ensure user confidence, reduce resistance, and maximise return on investment.

## Implementation alignment

This document is a change-management narrative. Validate feature claims against the current implementation in [Solution Index](../../solution-index.md) and the architecture/runbook documentation before using it for delivery commitments.

## Purpose and Principles

Change management is essential for successful digital transformation. Gartner’s study notes that half of change initiatives fail[1]; success requires aligning people, processes and technology. The plan is built on the five Cs of change (communication, collaboration, commitment, clarity and continuous improvement[2]) and emphasises transparency, role‑specific training and ongoing feedback. It also addresses the AI adoption gap: an IPMA survey found that 42 % of project managers are not using AI and only 23 % are actively using it[3], highlighting the need for targeted training and confidence building.

## Change‑Management Approach

### 1. Assess Readiness & Vision

**Stakeholder analysis:** Identify sponsors, champions and affected user groups (executives, PMO, project managers, resource managers, finance, vendors). Assess their readiness, pain points and expectations.

**Define the vision and objectives:** Articulate how the platform will improve portfolio visibility, decision‑making and efficiency. Tie outcomes to organisational goals (e.g., faster project approval cycles, improved resource utilisation, reduced budget overruns).

**Success metrics:** Establish KPIs such as adoption rate, user satisfaction, reduction in manual effort, improved forecast accuracy and ROI.

### 2. Communication Strategy

Resistance to change grows in an opaque environment. A communication plan should outline how and when updates will be shared[4]. Key elements:

**Transparency and consistency:** Provide clear, consistent messages on the platform’s purpose, benefits and timeline. Address concerns around job impact and emphasise that agents augment—not replace—project professionals.

**Tailored messaging:** Segment communications by role and maturity. Executives want strategic ROI and risk reduction; project managers need to understand daily workflows; IT teams must know technical implications[4].

**Channels and cadence:** Use multiple channels (town halls, intranet posts, newsletters, Teams/Slack, email, webinars) to reach stakeholders. Communicate early and often, especially before major milestones. Provide real‑time updates during deployment and weekly status during pilots.

**Feedback loops:** Encourage two‑way communication via surveys, Q&A sessions and community forums. Share responses and updates to build trust.

### 3. Training Programme

Design role‑specific training programmes that provide employees with the knowledge and skills they need to adapt[5]. Training should be iterative and blended:

Training materials should include:

**Onboarding kit:** Welcome emails, platform overview, login instructions, role‑based quick start guides and cheat sheets.

**Interactive tutorials:** In‑app guidance and tooltips with contextual help. Real‑time feedback and guidance reduce training costs and speed adoption[6].

**Video micro‑learning:** Short videos (3–5 minutes) covering specific features or workflows. Provide transcripts and captions for accessibility.

**Case studies & hands‑on labs:** Use real or anonymised project data to walk through common scenarios (e.g., creating a business case, running portfolio optimisation). Encourage experimentation in a sandbox environment.

**Certification & badges:** Offer optional certification paths (e.g., “Certified PPM Platform Practitioner”) to motivate learning and recognise proficiency.

**Continuous learning:** Provide refresher sessions, advanced modules (e.g., building custom metrics) and office hours. Highlight new features after each release.

### 4. Implementation Timeline

Break the change process into manageable phases with realistic deadlines[7]:

**Phase 0:** Preparation (2–4 weeks): Assess readiness, appoint change champions, define KPIs, prepare communications and onboarding materials.

**Phase 1:** Pilot (4–8 weeks): Roll out to a small group of power users and PMO members. Collect feedback via surveys and analytics. Refine training and processes.

**Phase 2:** Initial Deployment (8–12 weeks): Expand to selected programs or departments. Continue training and communication. Monitor adoption metrics and user sentiment.

**Phase 3:** Enterprise Rollout (12–20 weeks): Deploy across the organisation. Conduct targeted workshops, provide additional support, and track KPIs.

**Phase 4:** Optimisation & Continuous Improvement (ongoing): Review analytics and feedback, fine‑tune processes, and schedule refresher trainings. Plan for the onboarding of new users and integration of additional agents.

### 5. Monitoring and Measurement

Tracking progress is critical for keeping the change initiative on course[8]. Define quantitative and qualitative metrics:

**Adoption and usage:** Number of active users, log‑ins by role, feature usage, and completion of training modules.

**Engagement and sentiment:** Survey results, NPS, qualitative feedback, participation in forums and Q&A sessions.

**Performance and efficiency:** Reduction in manual tasks, cycle time for approvals, forecast accuracy, number of risks identified.

**Value realisation:** Financial benefits such as cost avoidance, improved margins or return on investment.

**Learning outcomes:** Pass rate for certification exams, average scores on assessments, completion rates.

Use analytics dashboards to monitor these metrics in real time. Tools that provide real‑time diagnostics can surface issues early[9]. Review results with sponsors and adjust the plan.

### 6. Continuous Improvement & Sustainability

**Refine and adapt:** No plan is flawless[10]. Regularly review feedback, analytics and lessons learned to identify gaps. Update training materials, communication strategies and runbooks accordingly.

**Change champions network:** Establish a community of super users and champions who provide peer support, gather feedback, and suggest improvements. Recognise and reward champions.

**Leadership involvement:** Maintain visible leadership support and celebrate milestones. Provide executives with adoption metrics and success stories to reinforce commitment.

**Integration of new hires:** Incorporate the platform into onboarding for new employees. Provide them with access to training resources and assign a mentor.

**Governance:** Align changes with governance frameworks. Ensure change requests, enhancements and new releases follow a standard process with approval gates. Keep an up‑to‑date change log accessible to all stakeholders.

## Communication Artefacts

The following artefacts support the change‑management and training plan:

**Change‑management charter:** Outlines objectives, scope, stakeholders, roles and success metrics.

**Communication plan:** A living document detailing messages, audiences, channels, frequency and owners.

**Training curriculum:** Matrix of training modules, target audiences, delivery methods and prerequisites.

**Onboarding guide:** Step‑by‑step instructions for new users including login, initial setup, and orientation.

**FAQ and knowledge base:** Common questions, troubleshooting tips, and best practices accessible via the support portal.

**Adoption dashboard:** Real‑time view of training completion, adoption metrics, and user feedback for sponsors and change leaders.

## Conclusion

The success of the multi‑agent PPM platform depends as much on people as on technology. A robust change‑management and training plan—rooted in transparent communication, role‑specific learning, phased deployment and continuous feedback—helps overcome resistance, bridges the AI adoption gap and accelerates realisation of benefits. By investing in the development of skills and maintaining open dialogue, organisations can ensure that their teams embrace the platform and unlock its full potential.

[1] [2] [4] [5] [6] [7] [8] [9] [10] How to Create a Change Management Plan Step-by-Step

https://apty.ai/blog/change-management-plan/

[3] Initial-AI-Survey-2024-Report.pdf

https://publications.ipma.world/wp-content/uploads/2025/01/Initial-AI-Survey-2024-Report.pdf

---

**Table 1**

| Audience | Training Components | Delivery Methods |
| --- | --- | --- |
| Executives & Sponsors | Vision briefing, ROI demonstration, governance model, dashboard overview | Executive workshops, briefing decks, interactive dashboards, recorded demos |
| PMO & Project Managers | End‑to‑end project lifecycle flows, use of agents (intent router, scheduling, resource management, risk), methodology map navigation, approval workflows | Instructor‑led workshops, interactive webinars, self‑paced e‑learning, sandbox exercises, scenario‑based simulations |
| Financial & Resource Analysts | Budgeting and forecasting features, integration with finance systems, resource planning & capacity, cost-benefit analysis | Hands‑on labs, guided walk‑throughs, how‑to videos |
| Team Members & Contributors | Task management, sprint planning, collaboration features, notifications, self‑service analytics | Quick start guides, in‑app walk‑throughs, micro‑learning modules |
| IT & Integration Teams | Architecture overview, connector configuration, APIs, security and compliance controls | Technical documentation, configuration workshops, office hours with engineering |
