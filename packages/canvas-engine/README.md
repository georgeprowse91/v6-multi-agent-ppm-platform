# Canvas Engine Package

A reusable canvas framework for rendering and editing different artifact types in the PPM Platform.

## Features

- **Multi-tab management** - Open, close, and switch between multiple canvas tabs
- **Per-tab state persistence** - Each tab maintains its own state (in-memory)
- **Standard toolbar** - Save Draft, Publish, and Export actions
- **Type-safe artifacts** - Canonical `CanvasArtifact` interface with TypeScript support
- **Five canvas types** - Document, Tree, Timeline, Spreadsheet, Dashboard

## Installation

The package is included in the monorepo. To use it in the web app:

```json
{
  "dependencies": {
    "@ppm/canvas-engine": "workspace:*"
  }
}
```

## Usage

### Basic Setup

```tsx
import {
  CanvasHost,
  DocumentCanvas,
  StructuredTreeCanvas,
  useCanvasHost,
  type CanvasArtifact,
} from '@ppm/canvas-engine';

function MyCanvasApp() {
  const {
    tabs,
    activeTabId,
    openTab,
    closeTab,
    setActiveTab,
    getArtifact,
  } = useCanvasHost();

  const renderCanvas = (type, artifact, onChange) => {
    switch (type) {
      case 'document':
        return <DocumentCanvas artifact={artifact} onChange={onChange} />;
      case 'tree':
        return <StructuredTreeCanvas artifact={artifact} onChange={onChange} />;
      // ... other canvas types
    }
  };

  return (
    <CanvasHost
      tabs={tabs}
      activeTabId={activeTabId}
      getArtifact={getArtifact}
      onTabSelect={setActiveTab}
      onTabClose={closeTab}
      renderCanvas={renderCanvas}
    />
  );
}
```

### Creating Artifacts

```tsx
import { createArtifact, createEmptyContent } from '@ppm/canvas-engine';

// Create a new document artifact
const doc = createArtifact(
  'document',
  'Project Charter',
  'project-123',
  { html: '<h1>Charter</h1>', plainText: 'Charter' }
);

// Create with empty content
const emptyDoc = createArtifact(
  'document',
  'New Document',
  'project-123',
  createEmptyContent('document')
);
```

## Canvas Types

### DocumentCanvas
Rich text document editor for charters, reports, and notes.
- Basic formatting (bold, italic, underline, strikethrough)
- Headings (H1, H2, H3, paragraph)
- Lists (ordered and unordered)
- Undo/redo support

### StructuredTreeCanvas
Hierarchical tree editor for WBS, org charts, and taxonomies.
- Add, edit, and delete nodes
- Expand/collapse subtrees
- Drag-and-drop reordering (future)

### TimelineCanvas
Gantt chart / timeline viewer.
- Visual timeline bars with progress
- Auto-calculated view range
- Color-coded items

### SpreadsheetCanvas
Simple spreadsheet for tabular data.
- Cell selection and editing
- Keyboard navigation
- Add rows/columns
- Formula support (future)

### DashboardCanvas
Widget-based dashboard layout.
- Metric widgets
- Chart widgets (bar, line, pie, area)
- Table widgets
- Text widgets

## Adding a New Canvas Type

Follow these steps to add a new canvas type to the framework:

### 1. Define the Content Type

Add your content interface to `src/types/artifact.ts`:

```typescript
// Define the content structure
export interface MyCanvasContent {
  // Your content fields
  data: string;
  settings: Record<string, unknown>;
}

// Add to the union type
export type ArtifactContent =
  | DocumentContent
  | TreeContent
  // ... existing types
  | MyCanvasContent;  // Add your type

// Add to CanvasType union
export type CanvasType =
  | 'document'
  | 'tree'
  // ... existing types
  | 'mycanvas';  // Add your type
```

### 2. Update createEmptyContent

Add a case for your canvas type in `createEmptyContent()`:

```typescript
export function createEmptyContent(type: CanvasType): ArtifactContent {
  switch (type) {
    // ... existing cases
    case 'mycanvas':
      return { data: '', settings: {} } as MyCanvasContent;
  }
}
```

### 3. Add Canvas Type Config

Add configuration to `src/types/canvas.ts`:

```typescript
export const CANVAS_TYPE_CONFIGS: Record<CanvasType, CanvasTypeConfig> = {
  // ... existing configs
  mycanvas: {
    type: 'mycanvas',
    displayName: 'My Canvas',
    icon: 'my-icon',
    description: 'Description of what this canvas does',
    defaultTitle: 'Untitled My Canvas',
    supportsExport: true,
    exportFormats: ['json', 'csv'],
  },
};
```

### 4. Create the Canvas Component

Create a new directory `src/components/MyCanvas/`:

```
src/components/MyCanvas/
├── MyCanvas.tsx
├── MyCanvas.module.css
└── index.ts
```

**MyCanvas.tsx:**
```tsx
import type { CanvasComponentProps } from '../../types/canvas';
import type { MyCanvasContent } from '../../types/artifact';
import styles from './MyCanvas.module.css';

export interface MyCanvasProps extends CanvasComponentProps<MyCanvasContent> {}

export function MyCanvas({
  artifact,
  readOnly = false,
  onChange,
  className,
}: MyCanvasProps) {
  // Implement your canvas UI
  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      {/* Your canvas content */}
    </div>
  );
}
```

**index.ts:**
```typescript
export { MyCanvas, type MyCanvasProps } from './MyCanvas';
```

### 5. Export from Components

Update `src/components/index.ts`:

```typescript
export { MyCanvas } from './MyCanvas';
export type { MyCanvasProps } from './MyCanvas';
```

### 6. Handle in renderCanvas

Update your `renderCanvas` function to handle the new type:

```tsx
const renderCanvas = (type, artifact, onChange) => {
  switch (type) {
    // ... existing cases
    case 'mycanvas':
      return <MyCanvas artifact={artifact} onChange={onChange} />;
  }
};
```

## API Reference

### Types

| Type | Description |
|------|-------------|
| `CanvasArtifact<T>` | Core artifact interface with generic content type |
| `CanvasType` | Union type of all canvas types |
| `ArtifactStatus` | `'draft' \| 'published'` |
| `CanvasComponentProps<T>` | Base props for canvas components |
| `CanvasTab` | Tab state for the host component |
| `CanvasHostState` | Complete state for the canvas host |

### Components

| Component | Description |
|-----------|-------------|
| `CanvasHost` | Main container with tab bar and toolbar |
| `TabBar` | Tab navigation component |
| `Toolbar` | Action toolbar (save, publish, export) |
| `DocumentCanvas` | Rich text editor |
| `StructuredTreeCanvas` | Hierarchical tree editor |
| `TimelineCanvas` | Gantt chart / timeline |
| `SpreadsheetCanvas` | Spreadsheet grid |
| `DashboardCanvas` | Widget dashboard |

### Hooks

| Hook | Description |
|------|-------------|
| `useCanvasHost` | State management hook for canvas host |

### Helper Functions

| Function | Description |
|----------|-------------|
| `createArtifact(type, title, projectId, content)` | Create a new artifact |
| `createEmptyContent(type)` | Create empty content for a canvas type |
| `canvasHostReducer(state, action)` | Reducer for canvas host state |

## Testing

Run the tests:

```bash
cd packages/canvas-engine
npm test
```

Run tests in watch mode:

```bash
npm run test:watch
```

## Development

### Project Structure

```
packages/canvas-engine/
├── src/
│   ├── types/
│   │   ├── artifact.ts      # Artifact types and helpers
│   │   ├── canvas.ts        # Canvas host types and reducer
│   │   └── index.ts
│   ├── components/
│   │   ├── CanvasHost/      # Tab bar, toolbar, host container
│   │   ├── DocumentCanvas/
│   │   ├── StructuredTreeCanvas/
│   │   ├── TimelineCanvas/
│   │   ├── SpreadsheetCanvas/
│   │   ├── DashboardCanvas/
│   │   └── index.ts
│   ├── hooks/
│   │   ├── useCanvasHost.ts
│   │   └── index.ts
│   ├── test/
│   │   └── setup.ts
│   └── index.ts
├── package.json
├── tsconfig.json
├── vitest.config.ts
└── README.md
```

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```
