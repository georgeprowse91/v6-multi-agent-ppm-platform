import { Linking } from 'react-native';

export type ApprovalNotificationPayload = {
  approvalId?: string;
  screen?: string;
};

export const registerForApprovalNotifications = async () => {
  return Promise.resolve();
};

export const extractApprovalDeepLink = (payload: ApprovalNotificationPayload) => {
  if (payload.screen === 'Approvals' || payload.approvalId) {
    return payload.approvalId ? `ppm://approvals/${payload.approvalId}` : 'ppm://approvals';
  }
  return null;
};

export const subscribeToApprovalDeepLinks = (onLink: (url: string) => void) => {
  const subscription = Linking.addEventListener('url', ({ url }) => {
    onLink(url);
  });
  return () => subscription.remove();
};
