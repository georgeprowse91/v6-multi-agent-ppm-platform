---
approval_request_subject: "Approbation requise : ${description}"
approval_request_body: |
  Bonjour ${approver},

  Une décision d'approbation est requise pour la demande ${request_id}.
  Description : ${description}
  Urgence : ${urgency}
  Date limite : ${deadline}

  ${delegation_note}

  Veuillez examiner la demande et soumettre votre décision.
approval_escalation_subject: "Avis d'escalade : ${description}"
approval_escalation_body: |
  Bonjour ${approver},

  La demande ${request_id} est en cours d'escalade.
  En raison d'un risque ${risk_score} et d'une criticité ${criticality_level}, l'escalade aura lieu après ${escalation_timeout_hours} heures.
  Date limite : ${deadline}.
approval_escalation_chat: "Escalade pour la demande ${request_id} : risque ${risk_score} / criticité ${criticality_level}. Escalade après ${escalation_timeout_hours} heures."
approval_escalation_push: "Escalade : ${request_id} (${risk_score} risque, ${criticality_level} criticité)"
approval_request_chat: "Approbation requise pour la demande ${request_id} : ${description} (date limite ${deadline})."
approval_request_push: "Approbation requise : ${description} (date limite ${deadline})"
approval_digest_subject: "Vous avez ${count} approbations en attente"
approval_digest_body: |
  Voici votre récapitulatif d'approbations :
  ${items}
  Généré à ${generated_at}.
approval_decision_subject: "Approbation ${decision} pour ${request_id}"
approval_decision_body: |
  Approbation ${decision} pour la demande ${request_id} par ${approver}.
  Commentaires : ${comments}
---
