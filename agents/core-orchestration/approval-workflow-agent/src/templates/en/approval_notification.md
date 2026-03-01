---
approval_request_subject: "Approval required: ${description}"
approval_request_body: |
  Hello ${approver},

  An approval decision is required for request ${request_id}.
  Description: ${description}
  Urgency: ${urgency}
  Deadline: ${deadline}

  ${delegation_note}

  Please review and submit your decision.
approval_escalation_subject: "Escalation notice: ${description}"
approval_escalation_body: |
  Hello ${approver},

  Approval request ${request_id} is being escalated.
  Due to ${risk_score} risk and ${criticality_level} criticality, escalation will occur after ${escalation_timeout_hours} hours.
  Deadline: ${deadline}.
approval_escalation_chat: "Escalation for request ${request_id}: ${risk_score} risk / ${criticality_level} criticality. Escalates after ${escalation_timeout_hours} hours."
approval_escalation_push: "Escalation: ${request_id} (${risk_score} risk, ${criticality_level} criticality)"
approval_request_chat: "Approval required for request ${request_id}: ${description} (deadline ${deadline})."
approval_request_push: "Approval required: ${description} (deadline ${deadline})"
approval_digest_subject: "You have ${count} pending approvals"
approval_digest_body: |
  Here is your approval digest:
  ${items}
  Generated at ${generated_at}.
approval_decision_subject: "Approval ${decision} for ${request_id}"
approval_decision_body: |
  Approval ${decision} for request ${request_id} by ${approver}.
  Comments: ${comments}
---
