import React, { useEffect } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';

import { useAppContext, AppProvider } from './src/context/AppContext';
import { colors } from './src/theme';
import { I18nProvider, useTranslation } from './src/i18n';
import { LoginScreen } from './src/screens/LoginScreen';
import { TenantSelectionScreen } from './src/screens/TenantSelectionScreen';
import { MethodologiesScreen } from './src/screens/MethodologiesScreen';
import { DashboardScreen } from './src/screens/DashboardScreen';
import { CanvasScreen } from './src/screens/CanvasScreen';
import { ApprovalsScreen } from './src/screens/ApprovalsScreen';
import { ConnectorsScreen } from './src/screens/ConnectorsScreen';
import { AssistantScreen } from './src/screens/AssistantScreen';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

const WorkspaceTabs = () => {
  const { tenantId, logout } = useAppContext();
  const { t } = useTranslation();

  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTitleStyle: { color: colors.text },
        headerTintColor: colors.text,
        tabBarStyle: { backgroundColor: colors.surface },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.muted,
        headerRight: () => (
          <Pressable
            onPress={logout}
            style={styles.headerButton}
            accessibilityRole="button"
            accessibilityLabel={t('mobile.signOut')}
          >
            <Text style={styles.headerButtonText}>{t('mobile.signOut')}</Text>
          </Pressable>
        ),
      }}
    >
      <Tab.Screen
        name="Methodologies"
        component={MethodologiesScreen}
        options={{
          title: tenantId
            ? t('mobile.tabs.methodologiesWithTenant', { tenantId })
            : t('mobile.tabs.methodologies'),
        }}
      />
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{ title: t('mobile.tabs.dashboard') }}
      />
      <Tab.Screen
        name="Canvas"
        component={CanvasScreen}
        options={{ title: t('mobile.tabs.canvas') }}
      />
      <Tab.Screen
        name="Approvals"
        component={ApprovalsScreen}
        options={{ title: t('mobile.tabs.approvals') }}
      />
      <Tab.Screen
        name="Connectors"
        component={ConnectorsScreen}
        options={{ title: t('mobile.tabs.connectors') }}
      />
      <Tab.Screen
        name="Assistant"
        component={AssistantScreen}
        options={{ title: t('mobile.tabs.assistant') }}
      />
    </Tab.Navigator>
  );
};

const RootNavigator = () => {
  const { session, loading, refreshSession, tenantId } = useAppContext();
  const { t } = useTranslation();

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator color={colors.accent} size="large" />
        <Text style={styles.loadingText}>{t('mobile.loadingSession')}</Text>
      </View>
    );
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!session.authenticated ? (
        <Stack.Screen name="Login" component={LoginScreen} />
      ) : !tenantId ? (
        <Stack.Screen name="TenantSelection" component={TenantSelectionScreen} />
      ) : (
        <Stack.Screen name="Workspace" component={WorkspaceTabs} />
      )}
    </Stack.Navigator>
  );
};

const navigationTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.background,
    card: colors.surface,
    text: colors.text,
    primary: colors.accent,
  },
};

const AppRoot = () => (
  <I18nProvider>
    <AppProvider>
      <NavigationContainer theme={navigationTheme}>
        <StatusBar style="light" />
        <RootNavigator />
      </NavigationContainer>
    </AppProvider>
  </I18nProvider>
);

export default AppRoot;

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    color: colors.muted,
    marginTop: 12,
  },
  headerButton: {
    marginRight: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    backgroundColor: colors.card,
  },
  headerButtonText: {
    color: colors.text,
    fontSize: 12,
    fontWeight: '600',
  },
});
