# Event Bus Package

## Purpose

Provide shared event bus implementations for agent and service communication.

## Contents

- `event_bus.ServiceBusEventBus`: Async Azure Service Bus topic wrapper for publishing/subscribing events.

## How to use

Import the package in services or agents after adding `packages/event_bus/src` to `PYTHONPATH`:

```python
from event_bus import ServiceBusEventBus
```

## Testing

Run repository tests:

```bash
pytest
```
