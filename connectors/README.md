# Connectors

Connectors integrate external systems (PPM tools, HR, finance, collaboration) with the platform.
Each connector has its own package with source code, mapping templates, and tests.

## Connector layout
- `<connector>/src`: Implementation code
- `<connector>/mappings`: Field mapping templates into the canonical model
- `<connector>/tests`: Connector-specific test coverage

## SDK
The `sdk` package provides shared helpers for authentication, retries, pagination, and event
publishing used by connector implementations.
