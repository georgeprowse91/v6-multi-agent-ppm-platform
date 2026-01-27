/**
 * StructuredTreeCanvas - Hierarchical tree editor
 *
 * For WBS (Work Breakdown Structure), org charts, and other
 * hierarchical structures with add/edit/delete node capabilities.
 */

import { useState, useCallback } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { TreeContent, TreeNode } from '../../types/artifact';
import styles from './StructuredTreeCanvas.module.css';

export interface StructuredTreeCanvasProps extends CanvasComponentProps<TreeContent> {}

interface TreeNodeProps {
  node: TreeNode;
  nodes: Record<string, TreeNode>;
  depth: number;
  readOnly: boolean;
  onToggle: (nodeId: string) => void;
  onEdit: (nodeId: string, label: string) => void;
  onAdd: (parentId: string) => void;
  onDelete: (nodeId: string) => void;
  editingNodeId: string | null;
  setEditingNodeId: (id: string | null) => void;
}

function TreeNodeComponent({
  node,
  nodes,
  depth,
  readOnly,
  onToggle,
  onEdit,
  onAdd,
  onDelete,
  editingNodeId,
  setEditingNodeId,
}: TreeNodeProps) {
  const [editValue, setEditValue] = useState(node.label);
  const hasChildren = node.children.length > 0;
  const isEditing = editingNodeId === node.id;

  const handleSaveEdit = useCallback(() => {
    if (editValue.trim()) {
      onEdit(node.id, editValue.trim());
    }
    setEditingNodeId(null);
  }, [editValue, node.id, onEdit, setEditingNodeId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleSaveEdit();
      } else if (e.key === 'Escape') {
        setEditValue(node.label);
        setEditingNodeId(null);
      }
    },
    [handleSaveEdit, node.label, setEditingNodeId]
  );

  return (
    <div className={styles.nodeContainer}>
      <div
        className={styles.node}
        style={{ paddingLeft: `${depth * 24}px` }}
      >
        {hasChildren ? (
          <button
            className={styles.toggleButton}
            onClick={() => onToggle(node.id)}
            aria-expanded={!node.collapsed}
            aria-label={node.collapsed ? 'Expand' : 'Collapse'}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={node.collapsed ? styles.collapsed : ''}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        ) : (
          <span className={styles.leafSpacer} />
        )}

        <span className={styles.nodeIcon}>
          {hasChildren ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          )}
        </span>

        {isEditing ? (
          <input
            type="text"
            className={styles.editInput}
            value={editValue}
            onChange={e => setEditValue(e.target.value)}
            onBlur={handleSaveEdit}
            onKeyDown={handleKeyDown}
            autoFocus
          />
        ) : (
          <span
            className={styles.nodeLabel}
            onDoubleClick={() => {
              if (!readOnly) {
                setEditValue(node.label);
                setEditingNodeId(node.id);
              }
            }}
          >
            {node.label}
          </span>
        )}

        {!readOnly && !isEditing && (
          <div className={styles.nodeActions}>
            <button
              className={styles.actionButton}
              onClick={() => onAdd(node.id)}
              title="Add child node"
              aria-label={`Add child to ${node.label}`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
            <button
              className={styles.actionButton}
              onClick={() => {
                setEditValue(node.label);
                setEditingNodeId(node.id);
              }}
              title="Edit node"
              aria-label={`Edit ${node.label}`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
            {node.parentId !== null && (
              <button
                className={`${styles.actionButton} ${styles.deleteButton}`}
                onClick={() => onDelete(node.id)}
                title="Delete node"
                aria-label={`Delete ${node.label}`}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>

      {hasChildren && !node.collapsed && (
        <div className={styles.children}>
          {node.children.map(childId => {
            const childNode = nodes[childId];
            if (!childNode) return null;
            return (
              <TreeNodeComponent
                key={childId}
                node={childNode}
                nodes={nodes}
                depth={depth + 1}
                readOnly={readOnly}
                onToggle={onToggle}
                onEdit={onEdit}
                onAdd={onAdd}
                onDelete={onDelete}
                editingNodeId={editingNodeId}
                setEditingNodeId={setEditingNodeId}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

export function StructuredTreeCanvas({
  artifact,
  readOnly = false,
  onChange,
  className,
}: StructuredTreeCanvasProps) {
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const { nodes, rootId } = artifact.content;
  const rootNode = nodes[rootId];

  const handleToggle = useCallback(
    (nodeId: string) => {
      if (!onChange) return;
      const node = nodes[nodeId];
      if (!node) return;

      onChange({
        ...artifact.content,
        nodes: {
          ...nodes,
          [nodeId]: { ...node, collapsed: !node.collapsed },
        },
      });
    },
    [nodes, onChange, artifact.content]
  );

  const handleEdit = useCallback(
    (nodeId: string, label: string) => {
      if (!onChange) return;
      const node = nodes[nodeId];
      if (!node) return;

      onChange({
        ...artifact.content,
        nodes: {
          ...nodes,
          [nodeId]: { ...node, label },
        },
      });
    },
    [nodes, onChange, artifact.content]
  );

  const handleAdd = useCallback(
    (parentId: string) => {
      if (!onChange) return;
      const parent = nodes[parentId];
      if (!parent) return;

      const newId = `node-${Date.now()}`;
      const newNode: TreeNode = {
        id: newId,
        label: 'New Item',
        parentId,
        children: [],
      };

      onChange({
        ...artifact.content,
        nodes: {
          ...nodes,
          [parentId]: {
            ...parent,
            children: [...parent.children, newId],
            collapsed: false,
          },
          [newId]: newNode,
        },
      });

      // Start editing the new node
      setTimeout(() => setEditingNodeId(newId), 50);
    },
    [nodes, onChange, artifact.content]
  );

  const handleDelete = useCallback(
    (nodeId: string) => {
      if (!onChange) return;
      const node = nodes[nodeId];
      if (!node || node.parentId === null) return;

      const parent = nodes[node.parentId];
      if (!parent) return;

      // Remove from parent's children
      const newParent = {
        ...parent,
        children: parent.children.filter(id => id !== nodeId),
      };

      // Recursively collect all descendant IDs
      const getDescendantIds = (id: string): string[] => {
        const n = nodes[id];
        if (!n) return [id];
        return [id, ...n.children.flatMap(getDescendantIds)];
      };

      const idsToRemove = new Set(getDescendantIds(nodeId));

      // Create new nodes object without deleted nodes
      const newNodes: Record<string, TreeNode> = {};
      for (const [id, n] of Object.entries(nodes)) {
        if (!idsToRemove.has(id)) {
          newNodes[id] = id === node.parentId ? newParent : n;
        }
      }

      onChange({
        ...artifact.content,
        nodes: newNodes,
      });
    },
    [nodes, onChange, artifact.content]
  );

  if (!rootNode) {
    return (
      <div className={`${styles.container} ${className ?? ''}`}>
        <div className={styles.emptyState}>
          <p>Invalid tree structure: root node not found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      <div className={styles.treeHeader}>
        <h3 className={styles.treeTitle}>{artifact.title}</h3>
        <span className={styles.nodeCount}>
          {Object.keys(nodes).length} nodes
        </span>
      </div>
      <div className={styles.tree}>
        <TreeNodeComponent
          node={rootNode}
          nodes={nodes}
          depth={0}
          readOnly={readOnly}
          onToggle={handleToggle}
          onEdit={handleEdit}
          onAdd={handleAdd}
          onDelete={handleDelete}
          editingNodeId={editingNodeId}
          setEditingNodeId={setEditingNodeId}
        />
      </div>
    </div>
  );
}
