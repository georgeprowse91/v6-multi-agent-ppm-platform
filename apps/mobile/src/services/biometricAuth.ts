import * as LocalAuthentication from 'expo-local-authentication';
import { Alert, Platform } from 'react-native';

export type BiometricType = 'fingerprint' | 'facial' | 'iris' | 'none';

export const isBiometricAvailable = async (): Promise<boolean> => {
  const compatible = await LocalAuthentication.hasHardwareAsync();
  if (!compatible) {
    return false;
  }
  const enrolled = await LocalAuthentication.isEnrolledAsync();
  return enrolled;
};

export const getBiometricType = async (): Promise<BiometricType> => {
  const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
  if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
    return 'facial';
  }
  if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
    return 'fingerprint';
  }
  if (types.includes(LocalAuthentication.AuthenticationType.IRIS)) {
    return 'iris';
  }
  return 'none';
};

export const getBiometricLabel = async (): Promise<string> => {
  const type = await getBiometricType();
  switch (type) {
    case 'facial':
      return Platform.OS === 'ios' ? 'Face ID' : 'Face Recognition';
    case 'fingerprint':
      return Platform.OS === 'ios' ? 'Touch ID' : 'Fingerprint';
    case 'iris':
      return 'Iris Scan';
    default:
      return 'Biometric';
  }
};

export const authenticateWithBiometrics = async (
  reason: string = 'Authenticate to continue'
): Promise<boolean> => {
  const available = await isBiometricAvailable();
  if (!available) {
    return true;
  }

  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: reason,
    cancelLabel: 'Cancel',
    disableDeviceFallback: false,
    fallbackLabel: 'Use passcode',
  });

  if (result.success) {
    return true;
  }

  if (result.error === 'user_cancel' || result.error === 'system_cancel') {
    return false;
  }

  Alert.alert('Authentication Failed', 'Biometric authentication was not successful. Please try again.');
  return false;
};

export const authenticateForApproval = async (approvalTitle?: string): Promise<boolean> => {
  const label = await getBiometricLabel();
  const reason = approvalTitle
    ? `Use ${label} to confirm approval: ${approvalTitle}`
    : `Use ${label} to confirm this approval action`;
  return authenticateWithBiometrics(reason);
};
