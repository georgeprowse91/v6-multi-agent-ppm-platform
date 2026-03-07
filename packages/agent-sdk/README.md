# PPM Agent SDK

Build custom agents for the PPM Agent Marketplace.

## Quick Start

```python
from agent_sdk import CustomAgent, AgentManifest, AgentContext

class MyAgent(CustomAgent):
    def get_manifest(self) -> AgentManifest:
        return AgentManifest(
            agent_id="my-custom-agent",
            display_name="My Custom Agent",
            version="1.0.0",
            description="Does something useful for project managers.",
            author={"name": "My Company"},
            category="custom",
            entry_point={"module": "my_agent", "class_name": "MyAgent"},
            capabilities=["my_capability"],
        )

    async def process(self, input_data: dict) -> dict:
        ctx = self.build_context(input_data)
        return {"result": "done", "tenant": ctx.tenant_id}
```

## Testing

```python
from agent_sdk import AgentTestHarness

harness = AgentTestHarness(MyAgent("my-agent"))
report = await harness.run_all_checks(
    sample_inputs=[{"query": "test", "context": {"tenant_id": "t1"}}]
)
print(f"Passed: {report['passed_count']}/{report['total']}")
```
