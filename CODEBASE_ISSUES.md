# Top 10 Codebase Issues — Impact & Fix Analysis

Comprehensive analysis of the multi-agent-ppm-platform-v4 codebase identifying the most
critical issues that need to be addressed. Each issue includes a concrete impact assessment
and a specific remediation plan with code examples.

---

## 1. Pervasive `sys.path.insert()` Abuse Across Production Code

**Severity:** High | **Category:** Architecture / Maintainability

### Description

There are **54+ instances** of `sys.path.insert()` in production source files across agents,
services, apps, and packages. Three distinct patterns exist:

- **Pattern A** — Service `main.py` files insert 3+ paths (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT)
- **Pattern B** — Agent files insert single package paths (e.g., FEATURE_FLAGS_ROOT)
- **Pattern C** — Base classes insert their own dependency paths (e.g., `base_agent.py:18`)

The project's own `test_security_review_fixes.py` tests that `sys.path.insert` has been
removed from 3 specific gateway files, and `pyproject.toml` contains comments acknowledging
this needs to be replaced by `pip install -e .`, but the pattern remains pervasive.

**Affected areas (sample):**
- `agents/runtime/src/base_agent.py:18`
- `agents/common/connector_integration.py:41,44`
- `services/*/main.py` (all 14 services)
- `services/agent-runtime/src/runtime.py:34` (inserts 12 paths in a loop)
- `apps/*/src/main.py` (all apps)
- `packages/workflow/src/workflow/executor.py:11`

### Impact

1. **Fragile import resolution** — The order in which `sys.path.insert(0, ...)` calls execute
   determines which module wins when names collide. The `pyproject.toml` already warns about
   this: `packages/contracts/src` contains an `api` sub-package that shadows
   `apps/api-gateway/src/api` (line 149-151). Any new package with an overlapping name
   silently breaks imports.

2. **Invisible dependency graph** — Static analysis tools (mypy, Pyright, IDEs) cannot resolve
   imports that depend on runtime path manipulation. This is why `pyproject.toml:193-199`
   has to suppress `E402` (module-level imports not at top of file) across every `main.py`,
   `config.py`, `routes/*.py`, and `auth.py`.

3. **Test/production environment drift** — Tests use `conftest.py:_bootstrap_paths()` (a
   well-designed centralized path resolver), while production code each manually inserts
   different subsets of paths. If a new package is added, every `main.py` must be updated
   independently.

4. **Docker build bloat** — Every service's Dockerfile must `COPY` every package directory
   that its `main.py` references via `sys.path`, even if only a small subset is actually
   imported. This bloats container images.

### Fix

The codebase already has the correct solution implemented in `tests/conftest.py:43-87` — a
`_bootstrap_paths()` function that auto-discovers all `*/src` directories, prioritizes
`api-gateway/src`, and de-duplicates. The fix is to extract this into a shared module and
use it everywhere.

**Step 1 — Create a shared bootstrap module:**

```python
# packages/common/src/common/bootstrap.py
"""
Centralized monorepo path bootstrap.

Replaces per-file sys.path.insert() calls with a single, idempotent function
that discovers all source trees. Mirrors the logic in tests/conftest.py.
"""
import sys
from pathlib import Path

_BOOTSTRAPPED = False

def ensure_monorepo_paths(repo_root: Path | None = None) -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    root = repo_root or _find_repo_root()
    ordered = [root / "vendor" / "stubs", root / "vendor", root]
    src_dirs = []
    for base in ("agents", "packages", "integrations/apps",
                 "integrations/connectors", "integrations/services",
                 "apps", "services"):
        base_path = root / base
        if base_path.exists():
            src_dirs.extend(p for p in base_path.glob("**/src") if p.is_dir())
    # Prioritize api-gateway to prevent shadowing
    api_gw = root / "apps" / "api-gateway" / "src"
    prioritized = [api_gw] if api_gw.exists() else []
    prioritized.extend(p for p in src_dirs if p != api_gw)
    ordered.extend(prioritized)
    seen = set(sys.path)
    new_paths = []
    for p in ordered:
        s = str(p.resolve())
        if s not in seen:
            seen.add(s)
            new_paths.append(s)
    sys.path[:0] = new_paths
    _BOOTSTRAPPED = True

def _find_repo_root() -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("Cannot find repo root (no pyproject.toml found)")
```

**Step 2 — Replace every `sys.path.insert()` block.** For example, in
`services/auth-service/src/main.py`:

```python
# BEFORE (lines 15-20):
REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

# AFTER:
from common.bootstrap import ensure_monorepo_paths
ensure_monorepo_paths()
```

**Step 3 — Add `packages/common/src` to Docker PYTHONPATH** in each Dockerfile so
`common.bootstrap` is importable before `ensure_monorepo_paths()` runs:

```dockerfile
ENV PYTHONPATH="/app/packages/common/src:${PYTHONPATH}"
```

**Step 4 — Update `tests/conftest.py`** to delegate to the same shared module, eliminating
the duplicated logic.

---

## 2. SQL Injection Risk via Dynamic Table/Column Names in f-strings

**Severity:** High | **Category:** Security

### Description

Multiple files construct SQL statements using f-strings with dynamic identifiers. Deep
analysis reveals two genuinely dangerous patterns and three that are safe-by-construction:

| File | Pattern | Sanitized? | Risk |
|------|---------|------------|------|
| `connector_integration.py:2712` | `CREATE TABLE {table_name}` | Character filter | Medium |
| `analytics.py:63,71` | `INSERT INTO {self._table}` / `CREATE TABLE {self._table}` | **None** | **Critical** |
| `knowledge_store.py:128-136` | `PRAGMA table_info({table})` / `ALTER TABLE {table}` / `UPDATE {table} SET {column}` | **None** | **Critical** |
| `storage.py:149` (lineage) | `WHERE {where_clause}` | Hardcoded fields + parameterized values | Safe |
| `scim_store.py:164` | `UPDATE users SET {updates}` | Hardcoded fields + parameterized values | Safe |

### Impact

1. **`analytics.py` — Full SQL injection via environment variable.** `SynapseAnalyticsProvider`
   accepts `table` from constructor (line 56), which flows from `ANALYTICS_SYNAPSE_TABLE`
   or config. No sanitization is applied. An attacker who controls this environment variable
   can inject: `analytics_events); DROP TABLE users; CREATE TABLE x (id int` which becomes
   a valid multi-statement DDL batch via SQLAlchemy's `text()`.

2. **`knowledge_store.py` — DDL injection via method parameters.** `_ensure_column()` (line 128)
   interpolates `table`, `column`, and `column_type` directly into `PRAGMA`, `ALTER TABLE`,
   and `UPDATE` statements with **zero sanitization**. While currently called with hardcoded
   values (line 117), any future caller passing user input would create immediate
   SQL injection. This is a latent vulnerability.

3. **`connector_integration.py` — Weakly sanitized table names.** `_normalize_collection_name()`
   (line 2666) filters to alphanumeric + underscore, which prevents traditional SQL injection
   breakout. However, interpolating into `IF OBJECT_ID(N'{table_name}', N'U')` and
   `CREATE TABLE {table_name}` is still a defense-in-depth failure — the intent is correct
   but the mechanism is fragile.

### Fix

**For `analytics.py` (Critical) — Add an allowlist:**

```python
# integrations/services/integration/analytics.py

_ALLOWED_TABLE_NAMES = frozenset({"analytics_events", "analytics_metrics", "analytics_logs"})

class SynapseAnalyticsProvider(AnalyticsProvider):
    def __init__(self, connection_string: str, table: str) -> None:
        from sqlalchemy import create_engine, text
        if table not in _ALLOWED_TABLE_NAMES:
            raise ValueError(
                f"Invalid analytics table name: {table!r}. "
                f"Allowed: {sorted(_ALLOWED_TABLE_NAMES)}"
            )
        self._engine = create_engine(connection_string)
        self._table = table
        # ... rest unchanged
```

**For `knowledge_store.py` (Critical) — Add identifier quoting:**

```python
# apps/web/src/knowledge_store.py

import re

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

def _quote_identifier(name: str) -> str:
    """Safely quote a SQLite identifier, rejecting invalid names."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'

def _ensure_column(self, conn, table: str, column: str, column_type: str,
                   *, default_value: str | None = None) -> None:
    safe_table = _quote_identifier(table)
    safe_column = _quote_identifier(column)
    if not _IDENTIFIER_RE.match(column_type):
        raise ValueError(f"Invalid column type: {column_type!r}")
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({safe_table})")}
    if column in columns:
        return
    conn.execute(f"ALTER TABLE {safe_table} ADD COLUMN {safe_column} {column_type}")
    if default_value is not None:
        conn.execute(
            f"UPDATE {safe_table} SET {safe_column} = ? WHERE {safe_column} IS NULL",
            (default_value,),
        )
```

**For `connector_integration.py` (Medium) — Add SQL Server bracket quoting:**

```python
# agents/common/connector_integration.py

def _safe_table_name(self, collection: str) -> str:
    """Normalize and bracket-quote a table name for SQL Server."""
    normalized = self._normalize_collection_name(collection)
    # SQL Server bracket quoting: [identifier] prevents injection
    return f"[{normalized}]"

def _ensure_azure_sql_table(self, cursor, table_name: str) -> None:
    safe = self._safe_table_name(table_name) if not table_name.startswith("[") else table_name
    cursor.execute(f"""
        IF OBJECT_ID(N'{safe}', N'U') IS NULL
        CREATE TABLE {safe} (
            record_id NVARCHAR(255) NOT NULL PRIMARY KEY,
            data NVARCHAR(MAX) NOT NULL,
            updated_at DATETIME2 NOT NULL
        )
    """)
```

---

## 3. Monolithic God-Class Files (2,000–7,600+ Lines)

**Severity:** High | **Category:** Maintainability / Code Quality

### Description

Many files vastly exceed maintainable sizes:

| File | Lines | Functions |
|------|-------|-----------|
| `apps/web/src/legacy_main.py` | 7,671 | 294 |
| `agents/.../resource_capacity_agent.py` | 3,791 | ~120 |
| `agents/.../vendor_procurement_agent.py` | 3,469 | ~110 |
| `agents/.../program_management_agent.py` | 3,042 | ~100 |
| `agents/common/connector_integration.py` | 3,006 | ~80 |
| `apps/web/frontend/.../ProjectConnectorGallery.tsx` | 1,699 | — |
| `apps/web/frontend/.../ConnectorGallery.tsx` | 1,488 | — |
| `apps/web/frontend/.../useConnectorStore.ts` | 1,446 | — |

### Impact

1. **Code review bottleneck** — A single change to `legacy_main.py` requires reviewing a
   7,671-line file. Merge conflicts are near-guaranteed when multiple developers touch
   the same file. PR reviewers cannot effectively assess changes in files this large.

2. **Testing difficulty** — Unit testing a 3,800-line agent class requires mocking the
   entire class's internal state. Isolated testing of individual behaviors is impossible
   without extracting them first. This is likely a contributing factor to the low frontend
   test coverage (Issue 7).

3. **Cognitive overload** — Developers must hold the entire 294-function `legacy_main.py`
   in working memory to understand control flow. New team members face a steep onboarding
   cliff.

4. **IDE performance** — Files this large cause noticeable lag in language servers (Pyright,
   TypeScript), autocompletion, and linting.

### Fix

**For `legacy_main.py` — Decompose into a FastAPI multi-module app.** The 294 functions
likely cluster into route groups. Extract into a standard FastAPI layout:

```
apps/web/src/
├── main.py                  # FastAPI app creation, middleware, lifespan
├── routes/
│   ├── projects.py          # /projects/* endpoints
│   ├── connectors.py        # /connectors/* endpoints
│   ├── agents.py            # /agents/* endpoints
│   ├── documents.py         # /documents/* endpoints
│   └── admin.py             # /admin/* endpoints
├── models/                  # Pydantic request/response models
├── services/                # Business logic layer
└── dependencies.py          # FastAPI Depends() factories
```

**For agent god-classes — Extract helper modules alongside each agent.** For example,
`resource_capacity_agent.py` (3,791 lines) likely contains capacity calculation logic,
allocation algorithms, and reporting helpers that can be split:

```
agents/delivery-management/resource-management-agent/src/
├── resource_capacity_agent.py   # Agent class (~300 lines, process() + lifecycle)
├── capacity_calculator.py       # Pure functions for capacity math
├── allocation_engine.py         # Allocation optimization logic
├── models.py                    # Pydantic models for inputs/outputs
└── reporting.py                 # Report generation helpers
```

**For React components — Extract sub-components and custom hooks:**

```
components/connectors/
├── ConnectorGallery.tsx         # Orchestrator component (~200 lines)
├── ConnectorCard.tsx            # Individual connector card
├── ConnectorFilterBar.tsx       # Search/filter controls
├── ConnectorDetailModal.tsx     # Detail modal
└── useConnectorGallery.ts       # State/logic hook
```

---

## 4. Docker `--from=repo-root` Requires BuildKit `additional_contexts`

**Severity:** Medium (downgraded from High) | **Category:** DevOps / Build

### Description

**20+ Dockerfiles** use `COPY --from=repo-root` but no build stage named `repo-root` is
defined *within* the Dockerfiles. Deep investigation reveals that `repo-root` is defined
externally via `additional_contexts` in `ops/docker/docker-compose.yml`:

```yaml
# ops/docker/docker-compose.yml (lines 8-11, repeated for each service)
build:
  context: ./apps/api-gateway
  dockerfile: Dockerfile
  additional_contexts:
    repo-root: .
```

This is a legitimate Docker BuildKit feature (Compose v2.4.0+). The Dockerfiles are
**correct when built via `docker-compose`**.

### Impact

1. **Standalone `docker build` fails** — Running `docker build -f apps/api-gateway/Dockerfile .`
   directly (without docker-compose) will fail with `"no stage named 'repo-root'"`. This
   breaks developer workflows when building individual services outside of Compose, and fails
   in CI pipelines that use plain `docker build`.

2. **Undocumented BuildKit dependency** — The `additional_contexts` feature requires
   `DOCKER_BUILDKIT=1` and Docker Compose v2.4.0+. This is not documented anywhere in the
   repository. Developers on older Docker versions will encounter opaque failures.

3. **Tight coupling to Compose** — Every Dockerfile is implicitly coupled to the Compose
   file's `additional_contexts` definition. A Dockerfile cannot be understood in isolation.

### Fix

**Option A (Recommended) — Add a comment header to each Dockerfile + document in CONTRIBUTING.md:**

```dockerfile
# NOTE: This Dockerfile requires Docker BuildKit and must be built via
# docker-compose (ops/docker/docker-compose.yml) which provides the
# 'repo-root' additional context pointing to the repository root.
# Standalone: DOCKER_BUILDKIT=1 docker build --build-context repo-root=../.. .
```

**Option B — Add a `Makefile` target for standalone builds:**

```makefile
# Makefile
build-service-%:
	DOCKER_BUILDKIT=1 docker build \
		--build-context repo-root=. \
		-f $*/Dockerfile \
		-t ppm-$* \
		$*
```

**Option C — Add fallback `ARG` in Dockerfiles** so they work both ways:

```dockerfile
# At top of each Dockerfile:
ARG REPO_ROOT_CONTEXT=repo-root
# Then use:
COPY --from=${REPO_ROOT_CONTEXT} pyproject.toml ./
```

---

## 5. Duplicate ErrorBoundary React Components

**Severity:** Medium | **Category:** Code Quality / Architecture

### Description

Two completely different `ErrorBoundary` implementations exist:

| Aspect | `error/ErrorBoundary.tsx` | `ui/ErrorBoundary.tsx` |
|--------|--------------------------|----------------------|
| Used in | `main.tsx` (root level) | `App.tsx` (router level) |
| Import style | `import React from 'react'` | `import { Component } from 'react'` |
| Fallback prop | No | Yes (`fallback?: ReactNode`) |
| Error state | `error?: Error` (optional) | `error: Error \| null` (required) |
| Console prefix | `'ui_error_boundary'` | `'[ErrorBoundary]'` |
| Action buttons | 3 (Reload, Home, Report) | 1 (Try again) |
| Email support | Yes (`support@example.com`) | No |
| Tests | Yes | **No** |

### Impact

1. **Double error catching** — Errors bubble up through two nested ErrorBoundary layers.
   The inner one (`ui/`) catches first, showing "Try again". If the user clicks it and
   the error recurs, the outer one (`error/`) catches it with different UI. This creates
   an inconsistent, confusing experience.

2. **Inconsistent logging** — Errors are logged twice with different prefixes
   (`ui_error_boundary` vs `[ErrorBoundary]`), creating duplicate noise in monitoring and
   making it harder to correlate errors.

3. **Maintenance burden** — Bug fixes must be applied in both files. The `ui/` version has
   no tests, so regressions there go undetected.

4. **Developer confusion** — New developers importing `ErrorBoundary` will find two options
   with no guidance on which to use.

### Fix

**Merge into a single component** that supports both use cases:

```tsx
// apps/web/frontend/src/components/ui/ErrorBoundary.tsx
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback UI. If omitted, the default error page is shown. */
  fallback?: ReactNode;
  /** Show full action buttons (reload/home/report). Default: false. */
  showActions?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary] Uncaught error:', error, info);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;
    return (
      <div role="alert" style={{ padding: '2rem', textAlign: 'center' }}>
        <h2>Something went wrong</h2>
        <pre style={{ color: 'red' }}>{this.state.error?.message}</pre>
        <button onClick={this.handleReset}>Try again</button>
        {this.props.showActions && (
          <>
            <button onClick={() => window.location.reload()}>Reload page</button>
            <button onClick={() => (window.location.href = '/')}>Go to home</button>
          </>
        )}
      </div>
    );
  }
}
```

Then update the two call sites:

```tsx
// main.tsx — root-level with full actions
<ErrorBoundary showActions>
  <BrowserRouter>
    <App />
  </BrowserRouter>
</ErrorBoundary>

// App.tsx — inner level with just retry
<ErrorBoundary>
  <Suspense fallback={<Loading />}>
    {/* routes */}
  </Suspense>
</ErrorBoundary>
```

Delete `components/error/ErrorBoundary.tsx` and update the existing test to cover both
modes.

---

## 6. Dynamic Code Execution Without Sandboxing in Agent Runtime

**Severity:** Medium | **Category:** Security

### Description

The agent runtime at `services/agent-runtime/src/runtime.py` uses `importlib`'s
`exec_module()` to dynamically load and execute agent code at three locations:

- **Line 192** — `_load_entrypoint_module()` loads connector entrypoints
- **Line 685** — `_load_agent_class()` loads agent classes from arbitrary file paths
- **Line 1076** — `_initialize_agents()` inserts agent parent directories into `sys.path`
  and loads classes

At line 679, `sys.path.insert(0, str(path.parent))` is called with the agent module's
parent directory, permanently polluting the process's import namespace.

### Impact

1. **Arbitrary code execution** — Any Python file that conforms to the `BaseAgent` interface
   can be loaded and executed with the full permissions of the runtime process. There is no
   validation of the agent code's contents (no AST analysis, no import restrictions, no
   filesystem access controls).

2. **Path pollution** — Each loaded agent permanently adds its parent directory to `sys.path`
   (line 679, 1076). Over time this accumulates, and a rogue agent directory could contain
   a `json.py` or `os.py` that shadows standard library modules for all subsequent imports.

3. **No isolation between agents** — All agents share the same process, memory space, and
   `sys.path`. A faulty agent can corrupt global state, exhaust memory, or crash the entire
   runtime.

### Fix

**Phase 1 — Agent module allowlisting (immediate):**

```python
# services/agent-runtime/src/runtime.py

import ast

_BLOCKED_IMPORTS = frozenset({"subprocess", "shutil", "ctypes", "socket"})

def _validate_agent_source(path: Path) -> None:
    """Static analysis: reject agents that import dangerous modules."""
    source = path.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _BLOCKED_IMPORTS:
                    raise ImportError(
                        f"Agent {path} imports blocked module: {alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in _BLOCKED_IMPORTS:
                raise ImportError(
                    f"Agent {path} imports blocked module: {node.module}"
                )
```

Call `_validate_agent_source(path)` before `spec.loader.exec_module(module)` in both
`_load_entrypoint_module()` and `_load_agent_class()`.

**Phase 2 — Subprocess isolation (longer-term):**

Run each agent in an isolated subprocess with restricted capabilities:

```python
import multiprocessing

def _execute_agent_isolated(agent_path: Path, input_data: dict) -> dict:
    """Execute an agent in a child process with timeout."""
    ctx = multiprocessing.get_context("spawn")  # Clean process, no shared state
    result_queue = ctx.Queue()
    proc = ctx.Process(target=_agent_worker, args=(agent_path, input_data, result_queue))
    proc.start()
    proc.join(timeout=60)
    if proc.is_alive():
        proc.terminate()
        raise TimeoutError(f"Agent {agent_path} exceeded 60s timeout")
    return result_queue.get_nowait()
```

---

## 7. Low Frontend Test Coverage (~16%)

**Severity:** Medium | **Category:** Testing

### Description

Only **34 test files** exist for **209 TypeScript/React source files** (~16% file-level
coverage). The largest untested files contain the most complex business logic:

| File | Lines | Tested? |
|------|-------|---------|
| `ProjectConnectorGallery.tsx` | 1,699 | No |
| `useConnectorStore.ts` | 1,446 | No |
| `WorkspacePage.tsx` | 1,328 | No |
| `useProjectConnectorStore.ts` | 962 | No |
| `WorkflowDesigner.tsx` | 907 | No |
| `MethodologyEditor.tsx` | 906 | No |
| `useCanvasStore.ts` | 749 | No |
| `useMethodologyStore.ts` | 694 | No |
| `IntakeFormPage.tsx` | 618 | No |
| `AgentGallery.tsx` | 577 | No |

### Impact

1. **Regressions go undetected** — The untested Zustand stores (`useConnectorStore`,
   `useProjectConnectorStore`, `useMethodologyStore`, `useCanvasStore`) contain the
   frontend's core business logic — state transitions, API orchestration, error handling.
   Changes here have no safety net.

2. **Refactoring is unsafe** — The monolithic components (Issue 3) cannot be safely
   decomposed without tests to verify behavior is preserved. This creates a chicken-and-egg
   problem: files are too large to test, and too untested to refactor.

3. **Integration bugs** — Page components like `WorkspacePage` (1,328 lines) orchestrate
   multiple stores and API calls. Without integration tests, the composition of these
   systems is unverified.

### Fix

**Priority 1 — Test Zustand stores first** (highest ROI, pure logic, no DOM):

```typescript
// apps/web/frontend/src/store/connectors/__tests__/useConnectorStore.test.ts
import { act, renderHook } from '@testing-library/react';
import { useConnectorStore } from '../useConnectorStore';

describe('useConnectorStore', () => {
  beforeEach(() => {
    useConnectorStore.setState(useConnectorStore.getInitialState());
  });

  it('adds a connector to the registry', () => {
    const { result } = renderHook(() => useConnectorStore());
    act(() => {
      result.current.addConnector({
        id: 'jira-1',
        type: 'jira',
        name: 'Jira Cloud',
        status: 'connected',
      });
    });
    expect(result.current.connectors).toHaveLength(1);
    expect(result.current.connectors[0].id).toBe('jira-1');
  });

  it('handles connection failure gracefully', async () => {
    // Test error state transitions
  });
});
```

**Priority 2 — Add smoke tests for page components** (prevents render crashes):

```typescript
// apps/web/frontend/src/pages/__tests__/WorkspacePage.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { WorkspacePage } from '../WorkspacePage';

it('renders without crashing', () => {
  render(
    <MemoryRouter>
      <WorkspacePage />
    </MemoryRouter>
  );
  expect(screen.getByRole('main')).toBeInTheDocument();
});
```

**Priority 3 — Enforce coverage threshold in CI:**

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      thresholds: {
        statements: 30,  // Start low, increment by 5% per sprint
        branches: 25,
        functions: 30,
      },
    },
  },
});
```

---

## 8. Inconsistent Build and Path Configuration

**Severity:** Medium | **Category:** DevOps / Configuration

### Description

The `@design-system` path alias resolves to different locations depending on which config
file is consulted:

| Config File | `@design-system` resolves to |
|------------|------------------------------|
| `tsconfig.json` | `../../../design-system/*` (does not exist) |
| `vite.config.ts` | `../../../design-system` (does not exist) |
| `vitest.config.ts` | `packages/ui-kit/design-system/tokens/tokens.ts` (correct) |
| **Actual location** | `packages/ui-kit/design-system/` |

The vitest config has been patched with specific sub-path aliases as a workaround, but
`tsconfig.json` and `vite.config.ts` still point to a non-existent root-level
`design-system/` directory.

### Impact

1. **TypeScript type checking may miss errors** — `tsconfig.json` resolves `@design-system/*`
   to a path that doesn't exist. TypeScript either silently ignores the import (if
   `skipLibCheck` or path fallback is active) or shows errors that developers learn to
   ignore.

2. **Vite build may use incorrect resolution** — The vite alias `@design-system` points to
   `../../../design-system` which doesn't exist. Vite may fall back to node_modules
   resolution or fail at build time.

3. **Test/build divergence** — Tests (via vitest) resolve `@design-system/tokens/tokens` to
   the correct location inside `packages/ui-kit`, while the build (via vite) resolves it
   differently, leading to subtle runtime differences.

### Fix

**Align all three configs to the correct path:**

```typescript
// apps/web/frontend/tsconfig.json — paths section
{
  "paths": {
    "@/*": ["src/*"],
    "@design-system/*": ["../../../packages/ui-kit/design-system/*"],
    "@ppm/canvas-engine": ["../../../packages/canvas-engine/src"],
    "@ppm/canvas-engine/*": ["../../../packages/canvas-engine/src/*"]
  }
}
```

```typescript
// apps/web/frontend/vite.config.ts — alias section
alias: {
  '@': path.resolve(__dirname, './src'),
  '@design-system': path.resolve(__dirname, '../../../packages/ui-kit/design-system'),
  '@ppm/canvas-engine': path.resolve(__dirname, '../../../packages/canvas-engine/src'),
}
```

```typescript
// apps/web/frontend/vitest.config.ts — remove specific workaround aliases
alias: {
  '@': path.resolve(__dirname, './src'),
  '@design-system': path.resolve(__dirname, '../../../packages/ui-kit/design-system'),
  '@ppm/canvas-engine': path.resolve(__dirname, '../../..', 'packages/canvas-engine/src'),
}
```

---

## 9. Loose Typing with `Any` Across Critical Infrastructure

**Severity:** Medium | **Category:** Type Safety

### Description

The base agent's core interface uses `Any` for both input and output:

```python
# agents/runtime/src/base_agent.py:224-225
@abstractmethod
async def process(self, input_data: dict[str, Any]) -> Any:
```

This propagates type uncertainty through all 27 agent implementations. Additionally,
`mypy` is configured to exclude virtually all production code (line 214-226 of
`pyproject.toml`), meaning type errors are never caught.

### Impact

1. **No compile-time contract enforcement** — The `process()` return type `Any` means mypy
   cannot verify that agents return valid `AgentPayload`-compatible data. The
   `_normalize_payload()` method (line 607) must handle `dict`, `BaseModel`, `AgentPayload`,
   or `None` at runtime, with a `TypeError` raised for anything else. This TypeError is only
   caught by the generic `except Exception` handler (line 447).

2. **Silent runtime failures** — If an agent returns a list instead of a dict, the
   `_normalize_payload()` call raises `TypeError` which is caught, logged as a generic
   error, and swallowed. The caller receives a success=false response with no indication
   of the type mismatch.

3. **IDE assistance degraded** — Developers get no autocomplete or type hints when working
   with agent outputs because everything is `Any`.

4. **mypy exclusions defeat the purpose** — `pyproject.toml:214-226` excludes all `main.py`,
   all `storage.py`, all `persistence.py`, all `config.py`, all test files, and the entire
   `vendor/` and `integrations/` directories. This means mypy only checks a small fraction
   of the codebase.

### Fix

**Step 1 — Define typed agent input/output models:**

```python
# agents/runtime/src/models.py (add to existing file)
from typing import TypeVar

class AgentInput(BaseModel):
    """Typed input contract for agent execution."""
    action: str
    data: dict[str, object] = {}
    context: dict[str, object] = {}
    tenant_id: str = "unknown"
    correlation_id: str | None = None

T = TypeVar("T", bound=BaseModel)
```

**Step 2 — Narrow the `process()` return type:**

```python
# agents/runtime/src/base_agent.py
@abstractmethod
async def process(self, input_data: dict[str, Any]) -> AgentPayload | dict[str, Any]:
    """Process the agent's core logic. Must return AgentPayload or a dict."""
    ...
```

This is a non-breaking change — all existing agents already return dicts.

**Step 3 — Incrementally reduce mypy exclusions.** Start by removing the broadest exclusion
patterns and fixing the resulting errors one service at a time:

```toml
# Remove these overly broad patterns:
# '(apps|services|agents)/.*/src/(storage|persistence|config|...)'
# Replace with specific file-level excludes as needed
```

---

## 10. Committed Demo/Dev Credentials in Version-Controlled Config Files

**Severity:** Medium | **Category:** Security

### Description

Three version-controlled files contain credential-like placeholder values:

**`ops/config/.env.demo`:**
```
AZURE_CLIENT_SECRET=replace-me-demo-secret
POSTGRES_ADMIN_PASSWORD=ChangeMe-DemoOnly-123!
JWT_SIGNING_KEY=replace-me-demo-jwt-signing-key
```

**`ops/config/.env.example`:**
```
POSTGRES_PASSWORD=replace_me_local_password
DATABASE_URL=postgresql://ppm_local:replace_me_local_password@db:5432/ppm_local
```

**`.devcontainer/dev.env`:**
```
DATABASE_URL=postgresql://ppm:ppm_password@localhost:5432/ppm_test
```

### Impact

1. **Placeholder drift to production** — `ChangeMe-DemoOnly-123!` looks like a real password.
   A developer running `cp .env.demo .env` and deploying without changing values would expose
   the system with known credentials. The env validation module (`common/env_validation.py`)
   has `STRICT_ENVIRONMENTS` checking for staging/production, but it validates **config
   format** (missing/invalid fields), not **credential values**.

2. **`AUTH_DEV_MODE=true` in `.env.example`** — While `api/config.py:65-69` correctly rejects
   `AUTH_DEV_MODE=true` in production, the `.env.example` template sets it to true by default.
   If a developer copies this template for staging, auth is bypassed unless they manually
   change it.

3. **Secret scanning false negatives** — `.gitleaks.toml` is configured but placeholder
   secrets with patterns like `replace-me-*` may not trigger secret scanning rules. The
   `POSTGRES_ADMIN_PASSWORD=ChangeMe-DemoOnly-123!` contains uppercase, lowercase, numbers,
   and special characters — it passes most password complexity checks.

### Fix

**Step 1 — Replace placeholders with obviously invalid values:**

```env
# ops/config/.env.demo
AZURE_CLIENT_SECRET=REPLACE_ME_NOT_A_REAL_SECRET
POSTGRES_ADMIN_PASSWORD=REPLACE_ME_NOT_A_REAL_PASSWORD
JWT_SIGNING_KEY=REPLACE_ME_NOT_A_REAL_KEY
```

**Step 2 — Add startup validation that rejects known placeholders in non-dev environments:**

```python
# packages/common/src/common/env_validation.py

_PLACEHOLDER_PATTERNS = (
    "replace_me", "replace-me", "changeme", "change_me",
    "REPLACE_ME", "CHANGE_ME", "not_a_real", "NOT_A_REAL",
)

def reject_placeholder_secrets(
    *,
    service_name: str,
    environment: str | None,
    secret_vars: dict[str, str],
) -> None:
    """Raise if any secret variable contains a placeholder value in strict environments."""
    if not is_strict_environment(environment):
        return
    for var_name, value in secret_vars.items():
        if any(pattern in value.lower() for pattern in _PLACEHOLDER_PATTERNS):
            raise ValueError(
                f"[{service_name}] {var_name} contains a placeholder value in "
                f"{normalize_environment(environment)}. "
                f"Replace with a real secret from your secrets manager."
            )
```

**Step 3 — Call the validation at service startup:**

```python
# In each service's config.py:
from common.env_validation import reject_placeholder_secrets

reject_placeholder_secrets(
    service_name="api-gateway",
    environment=settings.environment,
    secret_vars={
        "JWT_SIGNING_KEY": settings.jwt_signing_key,
        "DATABASE_URL": settings.database_url,
    },
)
```

---

## Summary

| # | Issue | Severity | Category | Fix Effort |
|---|-------|----------|----------|------------|
| 1 | `sys.path.insert()` abuse (54 instances) | High | Architecture | Medium — Create shared bootstrap module, mechanically replace all call sites |
| 2 | SQL injection via f-string identifiers | High | Security | Low — Add allowlists and identifier quoting to 3 files |
| 3 | Monolithic files (2,000–7,600+ lines) | High | Maintainability | High — Incremental extraction over multiple sprints |
| 4 | Docker `--from=repo-root` undocumented | Medium | DevOps | Low — Add documentation + standalone build support |
| 5 | Duplicate ErrorBoundary components | Medium | Code Quality | Low — Merge into single component, update 2 imports |
| 6 | Unsandboxed dynamic code execution | Medium | Security | Medium — Phase 1 (allowlist) is quick; Phase 2 (subprocess) is larger |
| 7 | Low frontend test coverage (~16%) | Medium | Testing | High — Ongoing effort, start with store tests |
| 8 | Inconsistent build/path configuration | Medium | Configuration | Low — Align 3 config files to correct path |
| 9 | Loose `Any` typing in infrastructure | Medium | Type Safety | Medium — Narrow base types, incrementally reduce mypy exclusions |
| 10 | Demo credentials in version control | Medium | Security | Low — Replace placeholders + add startup validation |
