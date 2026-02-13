import * as SecureStore from 'expo-secure-store';

import { submitProjectStatus, type StatusUpdatePayload } from '../api/client';

const STATUS_QUEUE_KEY = 'ppm.mobile.status.queue';

export type QueuedStatusUpdate = StatusUpdatePayload & {
  id: string;
  tenantId?: string | null;
  createdAt: string;
  retries: number;
};

const parseQueue = (raw: string | null): QueuedStatusUpdate[] => {
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as QueuedStatusUpdate[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export const loadStatusQueue = async (): Promise<QueuedStatusUpdate[]> => {
  const raw = await SecureStore.getItemAsync(STATUS_QUEUE_KEY);
  return parseQueue(raw);
};

const saveStatusQueue = async (queue: QueuedStatusUpdate[]) => {
  await SecureStore.setItemAsync(STATUS_QUEUE_KEY, JSON.stringify(queue));
};

export const enqueueStatusUpdate = async (
  payload: StatusUpdatePayload,
  tenantId?: string | null
): Promise<QueuedStatusUpdate> => {
  const queue = await loadStatusQueue();
  const queued: QueuedStatusUpdate = {
    ...payload,
    tenantId,
    id: `${payload.project_id}-${Date.now()}`,
    createdAt: new Date().toISOString(),
    retries: 0,
  };
  queue.push(queued);
  await saveStatusQueue(queue);
  return queued;
};

export const replayStatusQueue = async () => {
  const queue = await loadStatusQueue();
  if (queue.length === 0) {
    return { delivered: 0, remaining: 0 };
  }

  const remaining: QueuedStatusUpdate[] = [];
  let delivered = 0;

  for (const item of queue) {
    try {
      await submitProjectStatus(
        {
          project_id: item.project_id,
          status: item.status,
          summary: item.summary,
          updated_at: item.updated_at,
        },
        item.tenantId
      );
      delivered += 1;
    } catch {
      remaining.push({ ...item, retries: item.retries + 1 });
    }
  }

  await saveStatusQueue(remaining);
  return { delivered, remaining: remaining.length };
};

export const clearStatusQueue = async () => {
  await SecureStore.deleteItemAsync(STATUS_QUEUE_KEY);
};
