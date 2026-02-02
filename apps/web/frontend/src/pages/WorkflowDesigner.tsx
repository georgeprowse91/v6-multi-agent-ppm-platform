import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  MiniMap,
  type Connection,
  type Edge,
  type Node,
  useEdgesState,
  useNodesState,
} from 'reactflow';
import type { AgentConfig } from '@/store/agentConfig/types';
import type { Connector } from '@/store/connectors/types';
import styles from './WorkflowDesigner.module.css';
import 'reactflow/dist/style.css';

const API_BASE = '/v1';

const conditionOperators = [
  'equals',
  'not_equals',
  'greater_than',
  'less_than',
  'contains',
  'exists',
] as const;

const stepTypes = [
  'task',
  'decision',
  'approval',
  'notification',
  'api',
  'script',
] as const;

type ConditionOperator = (typeof conditionOperators)[number];
type StepType = (typeof stepTypes)[number];

interface WorkflowCondition {
  field: string;
  operator: ConditionOperator;
  value?: string;
}

interface WorkflowNodeData {
  label: string;
  trigger?: string;
  condition?: WorkflowCondition;
  agent_id?: string;
  action?: string;
  connector_id?: string;
  step_type: StepType;
}

interface WorkflowDefinitionSummary {
  workflow_id: string;
  name: string;
  description?: string | null;
}

interface WorkflowDefinitionRecord {
  workflow_id: string;
  name: string;
  description?: string | null;
  nodes: Array<Node<WorkflowNodeData>>;
  edges: Array<Edge>;
  definition: Record<string, unknown>;
}

const buildInitialNodes = (): Array<Node<WorkflowNodeData>> => [
  {
    id: 'step-start',
    position: { x: 80, y: 80 },
    data: {
      label: 'Trigger intake',
      trigger: 'New request submitted',
      agent_id: 'agent_001',
      action: 'triage_request',
      step_type: 'task',
    },
  },
  {
    id: 'step-review',
    position: { x: 380, y: 80 },
    data: {
      label: 'Approval gate',
      trigger: 'Triage completed',
      agent_id: 'agent_003_approval_workflow',
      action: 'request_approval',
      step_type: 'approval',
    },
  },
  {
    id: 'step-assign',
    position: { x: 680, y: 80 },
    data: {
      label: 'Assign execution',
      trigger: 'Approval granted',
      agent_id: 'agent_024',
      action: 'route_workflow',
      step_type: 'task',
    },
  },
];

const buildInitialEdges = (): Edge[] => [
  { id: 'edge-start-review', source: 'step-start', target: 'step-review' },
  { id: 'edge-review-assign', source: 'step-review', target: 'step-assign' },
];

const buildDefinition = (
  name: string,
  description: string,
  nodes: Array<Node<WorkflowNodeData>>,
  edges: Edge[]
) => {
  const steps = nodes.map((node) => {
    const outgoing = edges.filter((edge) => edge.source === node.id).map((edge) => edge.target);
    const step: Record<string, unknown> = {
      id: node.id,
      type: node.data.step_type,
    };
    const condition =
      node.data.condition && node.data.condition.field.trim()
        ? node.data.condition
        : undefined;
    if (node.data.step_type === 'decision') {
      if (outgoing[0]) {
        step.branches = [
          {
            name: 'Match',
            condition,
            next: outgoing[0],
          },
        ];
      }
      if (outgoing[1]) {
        step.default_next = outgoing[1];
      }
    } else if (condition) {
      step.condition = condition;
    } else if (outgoing.length === 1) {
      step.next = outgoing[0];
    }

    const config: Record<string, unknown> = {};
    if (node.data.agent_id) {
      config.agent = node.data.agent_id;
    }
    if (node.data.action) {
      config.action = node.data.action;
    }
    if (node.data.connector_id) {
      config.connector_id = node.data.connector_id;
    }
    if (node.data.trigger) {
      config.trigger = node.data.trigger;
    }
    if (Object.keys(config).length > 0) {
      step.config = config;
    }
    return step;
  });

  return {
    apiVersion: 'ppm.workflows/v1',
    kind: 'Workflow',
    metadata: {
      name,
      version: 'v1',
      owner: 'workflow-designer',
      description,
    },
    steps,
  };
};

const detectCycles = (nodeIds: string[], edges: Edge[]) => {
  const adjacency = new Map<string, string[]>();
  nodeIds.forEach((id) => adjacency.set(id, []));
  edges.forEach((edge) => {
    if (adjacency.has(edge.source)) {
      adjacency.get(edge.source)?.push(edge.target);
    }
  });
  const visiting = new Set<string>();
  const visited = new Set<string>();

  const visit = (nodeId: string): boolean => {
    if (visiting.has(nodeId)) {
      return true;
    }
    if (visited.has(nodeId)) {
      return false;
    }
    visiting.add(nodeId);
    for (const neighbor of adjacency.get(nodeId) ?? []) {
      if (visit(neighbor)) {
        return true;
      }
    }
    visiting.delete(nodeId);
    visited.add(nodeId);
    return false;
  };

  return nodeIds.some((id) => visit(id));
};

const buildGraphFromDefinition = (definition: Record<string, unknown>) => {
  const definitionSteps = (definition as { steps?: unknown }).steps;
  const steps = Array.isArray(definitionSteps) ? definitionSteps : [];
  const nodes: Array<Node<WorkflowNodeData>> = steps.map((step: any, index: number) => ({
    id: step.id,
    position: { x: 120 + index * 220, y: 120 },
    data: {
      label: step.id,
      step_type: step.type ?? 'task',
      trigger: step.config?.trigger,
      agent_id: step.config?.agent,
      action: step.config?.action,
      connector_id: step.config?.connector_id,
      condition: step.condition,
    },
  }));

  const edges: Edge[] = [];
  steps.forEach((step: any) => {
    if (step.next) {
      edges.push({
        id: `${step.id}-next`,
        source: step.id,
        target: step.next,
      });
    }
    if (Array.isArray(step.branches)) {
      step.branches.forEach((branch: any, index: number) => {
        if (branch.next) {
          edges.push({
            id: `${step.id}-branch-${index}`,
            source: step.id,
            target: branch.next,
          });
        }
      });
    }
    if (step.default_next) {
      edges.push({
        id: `${step.id}-default-next`,
        source: step.id,
        target: step.default_next,
      });
    }
  });

  return { nodes, edges };
};

export function WorkflowDesigner() {
  const [workflowId, setWorkflowId] = useState('workflow-new');
  const [workflowName, setWorkflowName] = useState('New Workflow');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [nodes, setNodes, onNodesChange] = useNodesState(buildInitialNodes());
  const [edges, setEdges, onEdgesChange] = useEdgesState(buildInitialEdges());
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [workflowList, setWorkflowList] = useState<WorkflowDefinitionSummary[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const selectedNode = useMemo(
    () => nodes.find((node) => node.id === selectedNodeId) ?? null,
    [nodes, selectedNodeId]
  );

  useEffect(() => {
    const fetchBasics = async () => {
      const [agentsResponse, connectorsResponse, workflowResponse] = await Promise.all([
        fetch(`${API_BASE}/agents/config`),
        fetch(`${API_BASE}/connectors`),
        fetch(`${API_BASE}/api/workflows`),
      ]);
      if (agentsResponse.ok) {
        setAgents((await agentsResponse.json()) as AgentConfig[]);
      }
      if (connectorsResponse.ok) {
        setConnectors((await connectorsResponse.json()) as Connector[]);
      }
      if (workflowResponse.ok) {
        setWorkflowList((await workflowResponse.json()) as WorkflowDefinitionSummary[]);
      }
    };
    fetchBasics().catch((error) => {
      console.error('Failed to load workflow designer dependencies', error);
    });
  }, []);

  const validateWorkflow = useCallback(
    (candidateNodes: Array<Node<WorkflowNodeData>>, candidateEdges: Edge[]) => {
      const messages: string[] = [];
      if (!workflowId.trim()) {
        messages.push('Workflow id is required.');
      }
      if (!workflowName.trim()) {
        messages.push('Workflow name is required.');
      }
      if (candidateNodes.length === 0) {
        messages.push('At least one workflow step is required.');
      }
      const nodeIds = new Set(candidateNodes.map((node) => node.id));
      candidateEdges.forEach((edge) => {
        if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
          messages.push('Connections must reference existing steps.');
        }
      });
      if (detectCycles(Array.from(nodeIds), candidateEdges)) {
        messages.push('Workflow cannot include cycles.');
      }
      candidateNodes.forEach((node) => {
        if (!node.data.label.trim()) {
          messages.push(`Step ${node.id} needs a label.`);
        }
        if (['task', 'api'].includes(node.data.step_type)) {
          if (!node.data.agent_id || !node.data.action) {
            messages.push(`Step ${node.id} needs an agent and action.`);
          }
        }
        const outgoing = candidateEdges.filter((edge) => edge.source === node.id);
        if (node.data.step_type === 'decision') {
          if (outgoing.length > 2) {
            messages.push(`Decision step ${node.id} supports at most 2 paths.`);
          }
        } else if (outgoing.length > 1) {
          messages.push(`Step ${node.id} supports only one outgoing path.`);
        }
      });
      return messages;
    },
    [workflowId, workflowName]
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) {
        return;
      }
      const newEdge: Edge = {
        id: `edge-${connection.source}-${connection.target}`,
        source: connection.source,
        target: connection.target,
      };
      const updatedEdges = addEdge(newEdge, edges);
      const cycleDetected = detectCycles(nodes.map((node) => node.id), updatedEdges);
      if (cycleDetected) {
        setErrors(['Connecting these steps would create a cycle.']);
        return;
      }
      setErrors([]);
      setEdges(updatedEdges);
    },
    [edges, nodes, setEdges]
  );

  const handleAddNode = () => {
    const newId = `step-${nodes.length + 1}`;
    const newNode: Node<WorkflowNodeData> = {
      id: newId,
      position: { x: 120 + nodes.length * 180, y: 320 },
      data: {
        label: `New step ${nodes.length + 1}`,
        step_type: 'task',
      },
    };
    setNodes((current) => [...current, newNode]);
  };

  const updateSelectedNode = (updates: Partial<WorkflowNodeData>) => {
    if (!selectedNodeId) {
      return;
    }
    setNodes((current) =>
      current.map((node) =>
        node.id === selectedNodeId
          ? { ...node, data: { ...node.data, ...updates } }
          : node
      )
    );
  };

  const handleConditionChange = (updates: Partial<WorkflowCondition>) => {
    const currentCondition = selectedNode?.data.condition;
    const updated = { field: '', operator: 'equals', value: '', ...currentCondition, ...updates };
    updateSelectedNode({ condition: updated });
  };

  const handleSave = async () => {
    const validationMessages = validateWorkflow(nodes, edges);
    if (validationMessages.length > 0) {
      setErrors(validationMessages);
      return;
    }
    setErrors([]);
    const definition = buildDefinition(workflowName, workflowDescription, nodes, edges);
    const payload = {
      workflow_id: workflowId,
      name: workflowName,
      description: workflowDescription,
      nodes,
      edges,
      definition,
    };
    const existing = workflowList.some((workflow) => workflow.workflow_id === workflowId);
    const response = await fetch(
      `${API_BASE}/api/workflows${existing ? `/${workflowId}` : ''}`,
      {
        method: existing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }
    );
    if (!response.ok) {
      setStatus('Failed to save workflow definition.');
      return;
    }
    const updated = (await response.json()) as WorkflowDefinitionRecord;
    setStatus('Workflow saved successfully.');
    setWorkflowList((current) => {
      const without = current.filter((workflow) => workflow.workflow_id !== updated.workflow_id);
      return [...without, {
        workflow_id: updated.workflow_id,
        name: updated.name,
        description: updated.description,
      }];
    });
  };

  const handleExport = () => {
    const definition = buildDefinition(workflowName, workflowDescription, nodes, edges);
    const payload = {
      workflow_id: workflowId,
      name: workflowName,
      description: workflowDescription,
      nodes,
      edges,
      definition,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${workflowId}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const text = await file.text();
    try {
      const payload = JSON.parse(text) as WorkflowDefinitionRecord;
      if (!payload.nodes || !payload.edges) {
        if (payload.definition) {
          const graph = buildGraphFromDefinition(payload.definition);
          setNodes(graph.nodes);
          setEdges(graph.edges);
        } else {
          setErrors(['Import file does not contain workflow graph data.']);
          return;
        }
      } else {
        setNodes(payload.nodes);
        setEdges(payload.edges);
      }
      setWorkflowId(payload.workflow_id);
      setWorkflowName(payload.name);
      setWorkflowDescription(payload.description ?? '');
      setStatus('Workflow imported successfully.');
      setErrors([]);
    } catch (error) {
      console.error('Failed to import workflow', error);
      setErrors(['Unable to parse workflow JSON.']);
    }
  };

  const handleLoadWorkflow = async (workflow: WorkflowDefinitionSummary) => {
    const response = await fetch(`${API_BASE}/api/workflows/${workflow.workflow_id}`);
    if (!response.ok) {
      setStatus('Failed to load workflow.');
      return;
    }
    const record = (await response.json()) as WorkflowDefinitionRecord;
    setWorkflowId(record.workflow_id);
    setWorkflowName(record.name);
    setWorkflowDescription(record.description ?? '');
    if (record.nodes && record.edges) {
      setNodes(record.nodes);
      setEdges(record.edges);
    } else {
      const graph = buildGraphFromDefinition(record.definition ?? {});
      setNodes(graph.nodes);
      setEdges(graph.edges);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1>Workflow Designer</h1>
          <p>Design multi-agent workflows with triggers, conditions, and execution steps.</p>
        </div>
        <div className={styles.headerActions}>
          <button type="button" className={styles.secondaryButton} onClick={handleAddNode}>
            Add step
          </button>
          <button type="button" className={styles.secondaryButton} onClick={handleExport}>
            Export JSON
          </button>
          <button type="button" className={styles.secondaryButton} onClick={handleImportClick}>
            Import JSON
          </button>
          <button type="button" className={styles.primaryButton} onClick={handleSave}>
            Save workflow
          </button>
        </div>
      </div>

      <div className={styles.content}>
        <div className={styles.sidebar}>
          <div className={styles.section}>
            <h2>Workflow details</h2>
            <label className={styles.label}>
              Workflow ID
              <input
                className={styles.input}
                value={workflowId}
                onChange={(event) => setWorkflowId(event.target.value)}
              />
            </label>
            <label className={styles.label}>
              Name
              <input
                className={styles.input}
                value={workflowName}
                onChange={(event) => setWorkflowName(event.target.value)}
              />
            </label>
            <label className={styles.label}>
              Description
              <textarea
                className={styles.textarea}
                value={workflowDescription}
                onChange={(event) => setWorkflowDescription(event.target.value)}
              />
            </label>
          </div>

          <div className={styles.section}>
            <h2>Load existing</h2>
            <div className={styles.workflowList}>
              {workflowList.length === 0 && (
                <span className={styles.hint}>No saved workflows yet.</span>
              )}
              {workflowList.map((workflow) => (
                <button
                  key={workflow.workflow_id}
                  type="button"
                  className={styles.listButton}
                  onClick={() => handleLoadWorkflow(workflow)}
                >
                  <span className={styles.listTitle}>{workflow.name}</span>
                  <span className={styles.listSubtitle}>{workflow.workflow_id}</span>
                </button>
              ))}
            </div>
          </div>

          <div className={styles.section}>
            <h2>Selected step</h2>
            {selectedNode ? (
              <div className={styles.nodeForm}>
                <label className={styles.label}>
                  Label
                  <input
                    className={styles.input}
                    value={selectedNode.data.label}
                    onChange={(event) => updateSelectedNode({ label: event.target.value })}
                  />
                </label>
                <label className={styles.label}>
                  Step type
                  <select
                    className={styles.select}
                    value={selectedNode.data.step_type}
                    onChange={(event) =>
                      updateSelectedNode({ step_type: event.target.value as StepType })
                    }
                  >
                    {stepTypes.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={styles.label}>
                  Trigger
                  <input
                    className={styles.input}
                    value={selectedNode.data.trigger ?? ''}
                    onChange={(event) => updateSelectedNode({ trigger: event.target.value })}
                  />
                </label>
                <label className={styles.label}>
                  Condition field
                  <input
                    className={styles.input}
                    value={selectedNode.data.condition?.field ?? ''}
                    onChange={(event) => handleConditionChange({ field: event.target.value })}
                  />
                </label>
                <label className={styles.label}>
                  Condition operator
                  <select
                    className={styles.select}
                    value={selectedNode.data.condition?.operator ?? 'equals'}
                    onChange={(event) =>
                      handleConditionChange({ operator: event.target.value as ConditionOperator })
                    }
                  >
                    {conditionOperators.map((operator) => (
                      <option key={operator} value={operator}>
                        {operator}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={styles.label}>
                  Condition value
                  <input
                    className={styles.input}
                    value={selectedNode.data.condition?.value ?? ''}
                    onChange={(event) => handleConditionChange({ value: event.target.value })}
                  />
                </label>
                <label className={styles.label}>
                  Agent
                  <select
                    className={styles.select}
                    value={selectedNode.data.agent_id ?? ''}
                    onChange={(event) => updateSelectedNode({ agent_id: event.target.value })}
                  >
                    <option value="">Select agent</option>
                    {agents.map((agent) => (
                      <option key={agent.agent_id} value={agent.agent_id}>
                        {agent.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={styles.label}>
                  Action
                  <input
                    className={styles.input}
                    value={selectedNode.data.action ?? ''}
                    onChange={(event) => updateSelectedNode({ action: event.target.value })}
                  />
                </label>
                <label className={styles.label}>
                  Connector
                  <select
                    className={styles.select}
                    value={selectedNode.data.connector_id ?? ''}
                    onChange={(event) => updateSelectedNode({ connector_id: event.target.value })}
                  >
                    <option value="">Optional connector</option>
                    {connectors.map((connector) => (
                      <option key={connector.connector_id} value={connector.connector_id}>
                        {connector.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : (
              <span className={styles.hint}>Select a step to edit its configuration.</span>
            )}
          </div>

          {status && <div className={styles.status}>{status}</div>}
          {errors.length > 0 && (
            <div className={styles.errorBox}>
              <h3>Validation</h3>
              <ul>
                {errors.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className={styles.canvas}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            onPaneClick={() => setSelectedNodeId(null)}
            onConnect={onConnect}
            fitView
          >
            <MiniMap />
            <Controls />
            <Background gap={16} />
          </ReactFlow>
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        className={styles.hidden}
        onChange={handleImport}
      />
    </div>
  );
}
