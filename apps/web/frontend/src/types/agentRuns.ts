export interface AgentRunData {
  id: string;
  tenant_id: string;
  agent_id: string;
  status: string;
  created_at?: string;
  updated_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  delay_reason?: string | null;
  completion_reason?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AgentRunRecord {
  id: string;
  tenant_id: string;
  schema_name: string;
  schema_version: number;
  data: AgentRunData;
  created_at: string;
  updated_at: string;
}
