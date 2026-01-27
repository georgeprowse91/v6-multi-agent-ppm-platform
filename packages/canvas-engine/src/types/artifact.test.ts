/**
 * Tests for CanvasArtifact types and helper functions
 */

import { describe, it, expect } from 'vitest';
import {
  createArtifact,
  createEmptyContent,
  type CanvasType,
  type DocumentContent,
  type TreeContent,
  type TimelineContent,
  type SpreadsheetContent,
  type DashboardContent,
} from './artifact';

describe('createArtifact', () => {
  it('should create a document artifact with correct defaults', () => {
    const content: DocumentContent = { html: '<p>Test</p>', plainText: 'Test' };
    const artifact = createArtifact('document', 'Test Doc', 'project-1', content);

    expect(artifact.type).toBe('document');
    expect(artifact.title).toBe('Test Doc');
    expect(artifact.projectId).toBe('project-1');
    expect(artifact.content).toEqual(content);
    expect(artifact.version).toBe(1);
    expect(artifact.status).toBe('draft');
    expect(artifact.id).toMatch(/^artifact-/);
    expect(artifact.metadata.createdAt).toBeDefined();
    expect(artifact.metadata.updatedAt).toBeDefined();
  });

  it('should create a tree artifact', () => {
    const content: TreeContent = {
      rootId: 'root',
      nodes: {
        root: { id: 'root', label: 'Root', parentId: null, children: [] },
      },
    };
    const artifact = createArtifact('tree', 'Test Tree', 'project-2', content);

    expect(artifact.type).toBe('tree');
    expect(artifact.content.rootId).toBe('root');
    expect(artifact.content.nodes.root).toBeDefined();
  });

  it('should generate unique IDs for each artifact', () => {
    const content: DocumentContent = { html: '', plainText: '' };
    const artifact1 = createArtifact('document', 'Doc 1', 'p1', content);
    const artifact2 = createArtifact('document', 'Doc 2', 'p1', content);

    expect(artifact1.id).not.toBe(artifact2.id);
  });
});

describe('createEmptyContent', () => {
  it('should create empty document content', () => {
    const content = createEmptyContent('document') as DocumentContent;

    expect(content.html).toBe('');
    expect(content.plainText).toBe('');
  });

  it('should create empty tree content with root node', () => {
    const content = createEmptyContent('tree') as TreeContent;

    expect(content.rootId).toBe('root');
    expect(content.nodes.root).toBeDefined();
    expect(content.nodes.root.label).toBe('Root');
    expect(content.nodes.root.parentId).toBeNull();
    expect(content.nodes.root.children).toEqual([]);
  });

  it('should create empty timeline content', () => {
    const content = createEmptyContent('timeline') as TimelineContent;

    expect(content.items).toEqual([]);
  });

  it('should create empty spreadsheet content with default structure', () => {
    const content = createEmptyContent('spreadsheet') as SpreadsheetContent;

    expect(content.columns).toEqual(['A', 'B', 'C', 'D', 'E']);
    expect(content.rows).toHaveLength(10);
    expect(content.rows[0]).toHaveLength(5);
    expect(content.rows[0][0].value).toBeNull();
  });

  it('should create empty dashboard content', () => {
    const content = createEmptyContent('dashboard') as DashboardContent;

    expect(content.widgets).toEqual([]);
    expect(content.gridColumns).toBe(12);
    expect(content.gridRows).toBe(8);
  });

  it('should handle all canvas types', () => {
    const canvasTypes: CanvasType[] = ['document', 'tree', 'timeline', 'spreadsheet', 'dashboard'];

    canvasTypes.forEach((type) => {
      const content = createEmptyContent(type);
      expect(content).toBeDefined();
    });
  });
});
