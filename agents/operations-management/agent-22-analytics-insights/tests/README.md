# Tests

This directory holds automated tests for the **agent 22 analytics insights** component. Tests should focus on behavior,
contract boundaries, and regression coverage for the component's public APIs.

## What to add here
- Unit tests for core logic and pure functions
- Integration tests for adapters (mocking external systems)
- Fixtures and reusable test helpers

## Conventions
- Keep tests deterministic and fast
- Prefer pytest and reuse shared fixtures in `/tests`
- Document any assumptions about external dependencies
