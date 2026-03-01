# Contributing to Multi-Agent PPM Platform

Thank you for your interest in contributing to the Multi-Agent PPM Platform! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Agent Development](#agent-development)
- [Connector Development](#connector-development)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. Be respectful, inclusive, and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git
- Azure subscription (for testing cloud integrations)
- Familiarity with:
  - Async Python (asyncio)
  - FastAPI
  - AI/ML concepts
  - PPM methodologies (helpful but not required)

### Find an Issue

1. Check the [Issues](https://github.com/georgeprowse91/multi-agent-ppm-platform/issues) page
2. Look for issues labeled:
   - `good first issue` - Great for newcomers
   - `help wanted` - We need help with these
   - `agent-implementation` - Agent development tasks
   - `connector` - Integration tasks
   - `documentation` - Documentation improvements

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/multi-agent-ppm-platform.git
cd multi-agent-ppm-platform

# Add upstream remote
git remote add upstream https://github.com/georgeprowse91/multi-agent-ppm-platform.git
```

### 2. Install Dependencies

```bash
# Install development dependencies
make install-dev

# Set up pre-commit hooks
pre-commit install

# Alternative dev install without editable package mode
pip install -r ops/requirements/requirements-dev.txt
```

### 3. Configure Environment

```bash
# Copy environment template
cp ops/config/.env.example .env

# Edit .env with your credentials
# Minimal setup for development:
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_API_KEY
# - DATABASE_URL (auto-configured with Docker)
```

### 4. Start Development Environment

```bash
# Start all services
make docker-up

# Or run individually
make run-api      # Terminal 1
make run-prototype  # Terminal 2
```

### 5. Verify Setup

```bash
# Run tests
make test-all

# Check linting
make lint

# Visit API docs
open http://localhost:8000/v1/docs
```

## Development Workflow

### 1. Create a Branch

```bash
# Update your fork
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 2. Make Changes

- Write clean, readable code
- Follow the coding standards below
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run tests
make test-all

# Run linters
make lint

# Format code
make format

# Run all checks
make check
```

### 4. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add feature: your feature description"
```

Commit message format:
```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

Example:
```
feat: Add risk prediction to Portfolio Strategy Agent

Implement Monte Carlo simulation for risk analysis in portfolio
optimization. Uses historical project data to predict schedule
and cost variance probabilities.

Closes #123
```

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create PR on GitHub
```

## Coding Standards

### Python Style Guide

We follow **PEP 8** with these tools:

- **Black** for formatting (line length: 100)
- **Ruff** for linting
- **MyPy** for type checking (optional but encouraged)

```bash
# Auto-format code
make format

# Check compliance
make lint
```

### Code Quality

- Write docstrings for all public functions/classes
- Use type hints
- Keep functions focused and small
- Avoid deep nesting (max 3 levels)
- Name variables descriptively

Good example:
```python
async def calculate_portfolio_score(
    projects: List[Project],
    criteria_weights: Dict[str, float]
) -> float:
    """
    Calculate weighted portfolio score.

    Args:
        projects: List of projects to score
        criteria_weights: Weights for each criterion

    Returns:
        Weighted portfolio score (0-100)
    """
    # Implementation
    pass
```

### Async/Await

- Use `async`/`await` for I/O-bound operations
- Don't block the event loop
- Use `asyncio.gather()` for parallel operations

```python
# Good
results = await asyncio.gather(
    fetch_data_from_api(),
    query_database(),
    call_external_service()
)

# Bad - sequential when could be parallel
result1 = await fetch_data_from_api()
result2 = await query_database()
result3 = await call_external_service()
```

## Testing Guidelines

### Test Commands Taxonomy

Use the Make targets below so local and CI runs are consistent:

```bash
make test-unit         # Unit-focused suite (excludes integration/e2e/security folders)
make test-integration  # tests/integration
make test-e2e          # tests/e2e
make test-security     # tests/security
make test-all          # Aggregate of unit + integration + e2e + security
make test-cov          # Full suite with coverage reporting
make test-quick        # Fast feedback alias for make test-unit
```

### Test Structure

```
tests/
├── test_base_agent.py      # Unit tests for base agent
├── test_intent_router.py   # Unit tests for specific agent
├── test_api.py             # API endpoint tests
├── integration/            # Integration tests
└── e2e/                    # End-to-end tests
```

### Writing Tests

```python
import pytest
from intent_router_agent import IntentRouterAgent

@pytest.mark.asyncio
async def test_intent_classification():
    """Test that portfolio queries are classified correctly."""
    agent = IntentRouterAgent()
    await agent.initialize()

    result = await agent.execute({
        "query": "Show me the portfolio overview",
        "context": {}
    })

    assert result["success"] is True
    intents = result["data"]["intents"]
    assert any(i["intent"] == "portfolio_query" for i in intents)
```

### Coverage Requirements

- Aim for >80% code coverage
- All new features must include tests
- Bug fixes should include regression tests

```bash
# Check coverage
make test-cov

# View detailed report
open htmlcov/index.html
```

## Documentation

### Code Documentation

- Add docstrings to all public APIs
- Use Google-style docstrings
- Include examples for complex functions

```python
def complex_calculation(value: int, multiplier: float = 1.0) -> float:
    """
    Perform complex calculation with optional multiplier.

    Args:
        value: Input value to process
        multiplier: Multiplication factor (default: 1.0)

    Returns:
        Calculated result

    Raises:
        ValueError: If value is negative

    Example:
        >>> complex_calculation(10, 2.5)
        25.0
    """
    if value < 0:
        raise ValueError("Value must be non-negative")
    return value * multiplier
```

### Documentation Updates

When adding features, update:

- README.md (if public-facing feature)
- API documentation (docstrings for endpoints)
- Configuration examples (if new config options)
- docs/architecture/ documentation (if architectural changes)

## Pull Request Process

### Before Submitting

1. ✅ Tests pass locally (`make test-all`)
2. ✅ Linting passes (`make lint`)
3. ✅ Code is formatted (`make format`)
4. ✅ Documentation updated
5. ✅ Commit messages follow conventions
6. ✅ Branch is up-to-date with main

### PR Template

Your PR description should include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings generated

## Related Issues
Closes #123
```

### Review Process

1. Automated checks run (CI/CD)
2. At least one maintainer review required
3. Address review feedback
4. Maintainer merges when approved

## Agent Development

### Creating a New the Intent Router agent. Create agent file in appropriate domain:

```bash
mkdir -p agents/portfolio-management/agent-XX-your-agent/src
touch agents/portfolio-management/agent-XX-your-agent/src/your_agent.py
```

2. Implement using BaseAgent template:

```python
from agents.runtime import BaseAgent

class YourAgent(BaseAgent):
    """
    Your Agent - Brief description

    See specification: agents/README.md
    """

    async def process(self, input_data: dict) -> dict:
        # Implementation
        pass
```

3. Add tests:

```bash
touch tests/test_your_agent.py
```

4. Update orchestrator to load agent

5. Document capabilities and integration points

See existing agents for examples:
- `agents/core-orchestration/intent-router-agent/src/intent_router_agent.py`
- `agents/portfolio-management/demand-intake-agent/src/demand_intake_agent.py`

## Connector Development

### Creating a New Connector

1. Create connector directory:

```bash
mkdir -p integrations/connectors/your-system/src
touch integrations/connectors/your-system/src/connector.py
```

2. Implement connector interface:

```python
class YourSystemConnector:
    """Connector for Your System integration."""

    async def authenticate(self) -> bool:
        """Authenticate with external system."""
        pass

    async def sync_data(self, entity_type: str) -> List[dict]:
        """Sync data from external system."""
        pass
```

3. Add configuration:

```yaml
# config/connectors/integrations.yaml
your_system:
  enabled: false
  base_url: "${YOUR_SYSTEM_URL}"
  auth:
    type: "oauth2"
  sync:
    interval_minutes: 30
```

4. Add tests and documentation

See [Connector Specifications](docs/connectors/overview.md) for detailed requirements.

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/georgeprowse91/multi-agent-ppm-platform/discussions)
- **Bugs**: Open an [Issue](https://github.com/georgeprowse91/multi-agent-ppm-platform/issues)
- **Documentation**: Check [docs/](docs/)

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to the Multi-Agent PPM Platform! 🎉
