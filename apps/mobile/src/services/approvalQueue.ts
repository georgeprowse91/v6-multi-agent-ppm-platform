import * as SecureStore from 'expo-secure-store';

import { submitApprovalAction, type ApprovalAction } from '../api/client';

const APPROVAL_QUEUE_KEY = 'ppm.mobile.approval.queue';

export type QueuedApprovalAction = {
  id: string;
  approvalId: string;
  action: ApprovalAction;
  tenantId?: string | null;
  createdAt: string;
  retries: number;
};

const parseQueue = (raw: string | null): QueuedApprovalAction[] => {
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as QueuedApprovalAction[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export const loadApprovalQueue = async (): Promise<QueuedApprovalAction[]> => {
  const raw = await SecureStore.getItemAsync(APPROVAL_QUEUE_KEY);
  return parseQueue(raw);
};

const saveApprovalQueue = async (queue: QueuedApprovalAction[]) => {
  await SecureStore.setItemAsync(APPROVAL_QUEUE_KEY, JSON.stringify(queue));
};

export const enqueueApprovalAction = async (
  approvalId: string,
  action: ApprovalAction,
  tenantId?: string | null
): Promise<QueuedApprovalAction> => {
  const queue = await loadApprovalQueue();
  const queued: QueuedApprovalAction = {
    id: `${approvalId}-${action}-${Date.now()}`,
    approvalId,
    action,
    tenantId,
    createdAt: new Date().toISOString(),
    retries: 0,
  };
  queue.push(queued);
  await saveApprovalQueue(queue);
  return queued;
};

export const replayApprovalQueue = async () => {
  const queue = await loadApprovalQueue();
  if (queue.length === 0) {
    return { delivered: 0, remaining: 0 };
  }

  const remaining: QueuedApprovalAction[] = [];
  let delivered = 0;

  for (const item of queue) {
    try {
      await submitApprovalAction(item.approvalId, item.action, item.tenantId);
      delivered += 1;
    } catch {
      remaining.push({ ...item, retries: item.retries + 1 });
    }
  }

  await saveApprovalQueue(remaining);
  return { delivered, remaining: remaining.length };
};

export const clearApprovalQueue = async () => {
  await SecureStore.deleteItemAsync(APPROVAL_QUEUE_KEY);
};

export const removeFromApprovalQueue = async (id: string) => {
  const queue = await loadApprovalQueue();
  const filtered = queue.filter((item) => item.id !== id);
  await saveApprovalQueue(filtered);
};
