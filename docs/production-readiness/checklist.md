# Production Readiness Checklist

## Infrastructure
- [ ] Terraform plan reviewed for AKS, networking, storage, WAF, and monitoring resources.
- [ ] Private AKS cluster reachable via approved network path (jump box or VPN).
- [ ] Azure Front Door/App Gateway WAF policy applied and in prevention mode.
- [ ] Immutable audit log storage enabled with retention policy locked.

## Security
- [ ] Key Vault CSI + workload identity configured for all workloads.
- [ ] Secrets injected via CSI, no plaintext values in Helm values.
- [ ] NetworkPolicies enforced (default deny + explicit service allowlists).
- [ ] Pod Security Admission labels set to `restricted`.
- [ ] Secret scan and IaC scan workflows passing.

## Application
- [ ] Frontend API calls use shared `requestJson` helper (no raw `fetch` in pages/components) and expose retry + user-facing error states.
- [ ] Helm charts linted and rendered without errors.
- [ ] HPA configured for CPU autoscaling.
- [ ] Rate limiting and CORS policies validated in production mode.
- [ ] OTel collector deployed and exporting traces/metrics.

## CI/CD
- [ ] E2E and contract tests passing on main.
- [ ] Terraform validate + helm lint/template checks passing.
- [ ] SBOM generated and attached to release tags.
- [ ] Documentation build passes (`mkdocs build`).

## Verification
- [ ] Runbooks updated and linked.
- [ ] Load test profile meets SLA targets.
