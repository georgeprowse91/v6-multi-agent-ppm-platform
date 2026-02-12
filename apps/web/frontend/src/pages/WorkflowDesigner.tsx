import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
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
import { parseJsonResponse, parseWithSchema } from '@/utils/apiValidation';
import { s } from '@/utils/schema';
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


const agentConfigSchema = s.object({
  agent_id: s.string(),
  name: s.string().optional(),
  status: s.string().optional(),
  role: s.string().optional(),
  temperature: s.number().optional(),
  model: s.string().optional(),
  prompts: s.array(s.string()).optional(),
  capabilities: s.array(s.string()).optional(),
  rag_sources: s.array(s.string()).optional(),
  tools: s.array(s.string()).optional(),
});

const connectorSchema = s.object({
  id: s.string(),
  name: s.string(),
  category: s.string(),
  enabled: s.boolean(),
  status: s.string(),
  description: s.string().optional(),
  type: s.string().optional(),
  endpoint: s.string().optional(),
  auth_type: s.string().optional(),
  capabilities: s.array(s.string()).optional(),
  metrics: s.array(s.string()).optional(),
  mcp_enabled: s.boolean().optional(),
  mcp_server_id: s.string().nullish(),
  mcp_server_url: s.string().nullish(),
  mcp_tool_map: s.record(s.unknown()).nullish(),
});

const workflowConditionSchema = s.object({
  field: s.string(),
  operator: s.enum(conditionOperators),
  value: s.string().optional(),
});

const workflowNodeSchema = s.object({
  id: s.string(),
  position: s.object({ x: s.number(), y: s.number() }),
  data: s.object({
    label: s.string(),
    trigger: s.string().optional(),
    condition: workflowConditionSchema.optional(),
    agent_id: s.string().optional(),
    action: s.string().optional(),
    connector_id: s.string().optional(),
    step_type: s.enum(stepTypes),
  }),
});

const workflowEdgeSchema = s.object({
  id: s.string(),
  source: s.string(),
  target: s.string(),
});

const workflowDefinitionSummarySchema = s.object({
  workflow_id: s.string(),
  name: s.string(),
  description: s.string().nullish(),
});

const workflowStepDefinitionSchema = s.object({
  id: s.string(),
  type: s.enum(stepTypes).optional(),
  next: s.string().optional(),
  default_next: s.string().optional(),
  branches: s.array(
    s.object({
      name: s.string().optional(),
      condition: workflowConditionSchema.optional(),
      next: s.string().optional(),
    })
  ).optional(),
  condition: workflowConditionSchema.optional(),
  config: s
    .object({
      trigger: s.string().optional(),
      agent: s.string().optional(),
      action: s.string().optional(),
      connector_id: s.string().optional(),
    })
    .optional(),
});

const workflowDefinitionGraphSchema = s.object({
  steps: s.array(workflowStepDefinitionSchema).default([]),
});

const workflowDefinitionRecordSchema = s.object({
  workflow_id: s.string(),
  name: s.string(),
  description: s.string().nullish(),
  nodes: s.array(workflowNodeSchema).default([]),
  edges: s.array(workflowEdgeSchema).default([]),
  definition: s.record(s.unknown()).default({}),
});

type WorkflowDefinitionGraph = {
  steps: WorkflowStepDefinition[];
};

interface WorkflowStepDefinition {
  id: string;
  type?: StepType;
  next?: string;
  default_next?: string;
  branches?: Array<{
    name?: string;
    condition?: WorkflowCondition;
    next?: string;
  }>;
  condition?: WorkflowCondition;
  config?: {
    trigger?: string;
    agent?: string;
    action?: string;
    connector_id?: string;
  };
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
  const { steps } = parseWithSchema<WorkflowDefinitionGraph>(
    workflowDefinitionGraphSchema,
    definition,
    'workflow definition graph'
  );
  const nodes: Array<Node<WorkflowNodeData>> = steps.map((step, index) => {
    const nodeId = step.id ?? `step-${index + 1}`;
    const stepType = step.type ?? 'task';
    return {
      id: nodeId,
      position: { x: 120 + index * 220, y: 120 },
      data: {
        label: nodeId,
        step_type: stepType,
        trigger: step.config?.trigger,
        agent_id: step.config?.agent,
        action: step.config?.action,
        connector_id: step.config?.connector_id,
        condition: step.condition,
      },
    };
  });

  const edges: Edge[] = [];
  steps.forEach((step) => {
    if (!step.id) {
      return;
    }
    if (step.next) {
      edges.push({
        id: `${step.id}-next`,
        source: step.id,
        target: step.next,
      });
    }
    if (Array.isArray(step.branches)) {
      step.branches.forEach((branch, index) => {
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
  const selectedAgentActions = useMemo(() => {
    if (!selectedNode?.data.agent_id) {
      return [];
    }
    const agent = agents.find((candidate) => candidate.agent_id === selectedNode.data.agent_id);
    return agent?.capabilities ?? [];
  }, [agents, selectedNode?.data.agent_id]);

  useEffect(() => {
    const fetchBasics = async () => {
      const [agentsResponse, connectorsResponse, workflowResponse] = await Promise.all([
        fetch(`${API_BASE}/agents/config`),
        fetch(`${API_BASE}/connectors`),
        fetch(`${API_BASE}/api/workflows`),
      ]);
      if (agentsResponse.ok) {
        setAgents(await parseJsonResponse(agentsResponse, s.array(agentConfigSchema), 'workflow designer agents'));
      }
      if (connectorsResponse.ok) {
        setConnectors(await parseJsonResponse(connectorsResponse, s.array(connectorSchema), 'workflow designer connectors'));
      }
      if (workflowResponse.ok) {
        setWorkflowList(await parseJsonResponse(workflowResponse, s.array(workflowDefinitionSummarySchema), 'workflow designer workflow list'));
      }
    };
    fetchBasics().catch((error) => {
      console.error('Failed to load workflow designer dependencies', error);
      setStatus('Some workflow designer data failed validation.');
      setErrors(['Unable to load one or more external payloads.']);
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
        if (node.data.step_type === 'decision') {
          if (!node.data.condition || !node.data.condition.field.trim()) {
            messages.push(`Decision step ${node.id} needs a condition.`);
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
    try {
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
      const updated = await parseJsonResponse(
        response,
        workflowDefinitionRecordSchema,
        'workflow save response'
      );
      setStatus('Workflow saved successfully.');
      setWorkflowList((current) => {
        const without = current.filter((workflow) => workflow.workflow_id !== updated.workflow_id);
        return [...without, {
          workflow_id: updated.workflow_id,
          name: updated.name,
          description: updated.description,
        }];
      });
    } catch (error) {
      console.error('Failed to save workflow', error);
      setStatus('Workflow save failed due to invalid response payload.');
    }
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
      const payload = parseWithSchema(workflowDefinitionRecordSchema, JSON.parse(text), 'workflow import file');
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
    try {
      const response = await fetch(`${API_BASE}/api/workflows/${workflow.workflow_id}`);
      if (!response.ok) {
        setStatus('Failed to load workflow.');
        return;
      }
      const record = await parseJsonResponse(
        response,
        workflowDefinitionRecordSchema,
        'workflow load response'
      );
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
    } catch (error) {
      console.error('Failed to load workflow', error);
      setStatus('Workflow load failed due to invalid response payload.');
      setErrors(['Workflow payload did not match expected schema.']);
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
                    list={
                      selectedAgentActions.length > 0
                        ? `workflow-actions-${selectedNode.id}`
                        : undefined
                    }
                    value={selectedNode.data.action ?? ''}
                    onChange={(event) => updateSelectedNode({ action: event.target.value })}
                  />
                  {selectedAgentActions.length > 0 && (
                    <datalist id={`workflow-actions-${selectedNode.id}`}>
                      {selectedAgentActions.map((action) => (
                        <option key={action} value={action} />
                      ))}
                    </datalist>
                  )}
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
            onNodeClick={(_: MouseEvent, node: Node<WorkflowNodeData>) =>
              setSelectedNodeId(node.id)
            }
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
