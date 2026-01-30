# Incident Response

This runbook outlines incident response steps, severity definitions, and escalation for the PPM platform.

## Severity Levels

| Severity | Description | Response Time | Escalation |
| --- | --- | --- | --- |
| SEV-1 | Platform outage, data loss, security breach | 15 minutes | Immediate exec notification |
| SEV-2 | Major functionality degraded | 30 minutes | Manager notification within 1 hour |
| SEV-3 | Partial degradation or single service issue | 4 hours | Team lead notification |

## RTO/RPO Reference

| Service | RTO | RPO | Priority |
| --- | --- | --- | --- |
| API Gateway | 15 minutes | N/A | Critical |
| Workflow Engine | 30 minutes | 5 minutes | Critical |
| Data Service | 1 hour | 15 minutes | High |
| Audit Log | 2 hours | 0 minutes (WORM) | High |
| Analytics | 4 hours | 30 minutes | Medium |

## Escalation Matrix

| Role | Contact Method | When to Escalate |
| --- | --- | --- |
| On-call Engineer | PagerDuty | All alerts |
| Platform Lead | Slack + Phone | SEV-1/2 unresolved > 30 min |
| Engineering Manager | Phone | SEV-1 unresolved > 1 hour |
| VP Engineering | Phone | SEV-1 with data loss or security breach |
| Legal/Compliance | Email + Phone | Security breach affecting customer data |

## Immediate Response Steps

### 1. Acknowledge Alert (Within SLA)

```bash
# Check current alerts
az monitor metrics alert list --resource-group ppm-production

# View Application Insights live metrics
# Navigate to: Azure Portal > Application Insights > Live Metrics
```

- Confirm alert severity and affected service
- Start incident bridge (Slack: #incident-response)
- Create incident ticket with initial details
- Assign Incident Commander (IC) role

### 2. Triage

```bash
# Check service health
kubectl get pods -n ppm-platform
kubectl describe pod <pod-name> -n ppm-platform

# View recent logs
kubectl logs -n ppm-platform -l app=ppm-api --tail=100

# Check Application Insights for errors
az monitor app-insights query --app ppm-production-appinsights \
  --analytics-query "exceptions | where timestamp > ago(15m) | summarize count() by problemId"
```

- Review service dashboards in Grafana/Azure Monitor
- Confirm tenant impact and scope
- Document affected services and estimated user impact

### 3. Containment

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/ppm-api -n ppm-platform

# Scale down problematic service
kubectl scale deployment/ppm-api --replicas=0 -n ppm-platform

# Enable maintenance mode (if available)
kubectl set env deployment/ppm-api MAINTENANCE_MODE=true -n ppm-platform
```

- Disable failing deployments or rollback
- Isolate compromised credentials
- Block malicious IPs if under attack

### 4. Mitigation

```bash
# Scale out services
kubectl scale deployment/ppm-api --replicas=10 -n ppm-platform

# Apply hotfix
kubectl set image deployment/ppm-api api=ghcr.io/org/ppm-api:hotfix-v1.2.3 -n ppm-platform

# Verify deployment
kubectl rollout status deployment/ppm-api -n ppm-platform
```

- Apply hotfix or scale out services
- Route traffic to healthy region if needed
- Implement temporary workarounds

### 5. Communication

| Audience | Channel | Frequency |
| --- | --- | --- |
| Internal Team | Slack #incident-response | Every 15 minutes |
| Stakeholders | Email | Every 30 minutes |
| Customers (SEV-1/2) | Status Page | Every 30 minutes |
| Executive | Email + Slack | Major updates only |

**Status Update Template:**

```
INCIDENT UPDATE - [SEV-X] [Service Name]
Time: [UTC timestamp]
Status: [Investigating/Identified/Monitoring/Resolved]
Impact: [Description of user impact]
Current Actions: [What we're doing]
ETA to Resolution: [Estimate or "Under investigation"]
Next Update: [Time]
```

### 6. Resolution

```bash
# Verify service health
curl -f https://api.ppm-platform.com/api/v1/health

# Check error rates returned to normal
az monitor app-insights query --app ppm-production-appinsights \
  --analytics-query "requests | where timestamp > ago(15m) | summarize count() by resultCode"

# Validate data integrity
python scripts/validate-data-integrity.py --tenant-id <affected-tenant>
```

- Confirm metrics return to SLO targets
- Validate tenant isolation and RBAC integrity
- Remove any temporary workarounds
- Update status page to "Resolved"

### 7. Post-Incident

- [ ] Create postmortem document within 24 hours
- [ ] Schedule postmortem meeting within 5 business days
- [ ] Identify root cause and contributing factors
- [ ] Create action items with owners and due dates
- [ ] Update runbooks based on learnings
- [ ] Close incident ticket with summary

## Common Incident Playbooks

### Database Connection Pool Exhaustion

1. Check current connections: `SELECT count(*) FROM pg_stat_activity;`
2. Identify long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start;`
3. Kill problematic queries if necessary
4. Scale up connection pool or add read replicas
5. Review application connection handling

### Agent Execution Failures

1. Check orchestrator logs for error patterns
2. Verify LLM provider (Azure OpenAI) status
3. Check rate limits and quotas
4. Review recent agent configuration changes
5. Restart affected agent pods if necessary

### Authentication Service Degradation

1. Verify Azure AD/Okta status
2. Check JWT signing key validity
3. Review OIDC discovery endpoint availability
4. Verify identity service pod health
5. Check for expired certificates

### High Memory Usage / OOM Kills

1. Identify affected pods: `kubectl top pods -n ppm-platform`
2. Check for memory leaks in recent deployments
3. Review request patterns for unusual load
4. Increase memory limits temporarily
5. Roll back if caused by recent deployment

## Security Incident Addendum

### Immediate Actions (Within 15 minutes)

1. **Isolate affected systems**
   ```bash
   # Block external access if needed
   kubectl patch networkpolicy deny-all -n ppm-platform
   ```

2. **Preserve evidence**
   - Do not delete or modify logs
   - Take snapshots of affected systems
   - Document timeline of events

3. **Rotate compromised credentials**
   ```bash
   # Rotate secrets in Key Vault
   az keyvault secret set --vault-name ppm-keyvault --name <secret-name> --value <new-value>

   # Force pod restart to pick up new secrets
   kubectl rollout restart deployment -n ppm-platform
   ```

### Notification Requirements

| Condition | Notify | Timeline |
| --- | --- | --- |
| PII exposure | Legal, DPO | Immediately |
| GDPR data breach | Supervisory Authority | Within 72 hours |
| Customer data access | Affected customers | As required by contract |

### Post-Security Incident

- [ ] Conduct forensic analysis
- [ ] Document attack vector and remediation
- [ ] Validate audit log integrity and retention policies
- [ ] Perform tenant impact assessment
- [ ] Update threat model and security controls
- [ ] Notify compliance team and complete required filings
