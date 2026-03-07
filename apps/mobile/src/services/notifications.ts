import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Linking, Platform } from 'react-native';

export type ApprovalNotificationPayload = {
  approvalId?: string;
  screen?: string;
};

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export const registerForApprovalNotifications = async (): Promise<string | null> => {
  if (!Device.isDevice) {
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    return null;
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('approvals', {
      name: 'Approvals',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF6B35',
      sound: 'default',
    });

    await Notifications.setNotificationChannelAsync('status-updates', {
      name: 'Status Updates',
      importance: Notifications.AndroidImportance.DEFAULT,
      sound: 'default',
    });
  }

  const tokenData = await Notifications.getExpoPushTokenAsync({
    projectId: process.env.EXPO_PUBLIC_PROJECT_ID,
  });

  return tokenData.data;
};

export const extractApprovalDeepLink = (payload: ApprovalNotificationPayload) => {
  if (payload.screen === 'Approvals' || payload.approvalId) {
    return payload.approvalId ? `ppm://approvals/${payload.approvalId}` : 'ppm://approvals';
  }
  if (payload.screen === 'Dashboard') {
    return 'ppm://dashboard';
  }
  if (payload.screen === 'Assistant') {
    return 'ppm://assistant';
  }
  return null;
};

export type NotificationNavigationHandler = (screen: string, params?: Record<string, string>) => void;

export const subscribeToApprovalDeepLinks = (onLink: (url: string) => void) => {
  const subscription = Linking.addEventListener('url', ({ url }) => {
    onLink(url);
  });
  return () => subscription.remove();
};

const parseDeepLink = (url: string): { screen: string; params: Record<string, string> } | null => {
  if (!url.startsWith('ppm://')) {
    return null;
  }
  const path = url.replace('ppm://', '');
  const parts = path.split('/');

  if (parts[0] === 'approvals' && parts[1]) {
    return { screen: 'Approvals', params: { approvalId: parts[1] } };
  }
  if (parts[0] === 'approvals') {
    return { screen: 'Approvals', params: {} };
  }
  if (parts[0] === 'dashboard') {
    return { screen: 'Dashboard', params: {} };
  }
  if (parts[0] === 'assistant') {
    return { screen: 'Assistant', params: {} };
  }
  if (parts[0] === 'status') {
    return { screen: 'StatusUpdates', params: {} };
  }
  return null;
};

export const subscribeToNotificationNavigation = (
  navigate: NotificationNavigationHandler
): (() => void) => {
  const responseSubscription = Notifications.addNotificationResponseReceivedListener((response) => {
    const data = response.notification.request.content.data as Record<string, unknown>;

    const deepLink = extractApprovalDeepLink({
      approvalId: data.approvalId as string | undefined,
      screen: data.screen as string | undefined,
    });

    if (deepLink) {
      const parsed = parseDeepLink(deepLink);
      if (parsed) {
        navigate(parsed.screen, parsed.params);
      }
    }
  });

  const deepLinkCleanup = subscribeToApprovalDeepLinks((url) => {
    const parsed = parseDeepLink(url);
    if (parsed) {
      navigate(parsed.screen, parsed.params);
    }
  });

  return () => {
    responseSubscription.remove();
    deepLinkCleanup();
  };
};

export const getLastNotificationResponse =
  async (): Promise<Notifications.NotificationResponse | null> => {
    return Notifications.getLastNotificationResponseAsync();
  };

export const setBadgeCount = async (count: number) => {
  await Notifications.setBadgeCountAsync(count);
};

export const scheduleLocalNotification = async (
  title: string,
  body: string,
  data?: Record<string, unknown>,
  channelId?: string
) => {
  await Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data,
      ...(Platform.OS === 'android' && channelId ? { channelId } : {}),
    },
    trigger: null,
  });
};
