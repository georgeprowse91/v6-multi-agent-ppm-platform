# ADR 0001: Record Architecture

## Status

Accepted.

## Context

The platform requires a repository structure that supports shared packages, multiple services, and a consistent documentation and governance footprint. Teams need to deliver apps, services, agents, and infrastructure in lockstep.

## Decision

Adopt a monorepo with clear boundaries for:

- Applications under `apps/`
- Services under `services/`
- Agents under `agents/`
- Shared packages under `packages/`
- Infrastructure under `ops/infra/`
- Documentation under `docs/`

The monorepo structure is enforced via tooling such as `tools/component_runner` and shared configuration under `ops/config/`.

## Consequences

- Shared dependency management and tooling is centralized in one repository.
- CI can validate schemas, manifests, docs, and infrastructure consistently.
- Teams must coordinate releases across multiple components in the same repo.

## References

- `apps/README.md`
- `services/README.md`
- `packages/README.md`
- `docs/README.md`
