import React, { useState } from 'react';
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { apiFetch } from '../api/client';
import { Card } from '../components/Card';
import { useAppContext } from '../context/AppContext';
import { colors, radius, spacing } from '../theme';

type Message = {
  id: string;
  author: 'user' | 'assistant';
  text: string;
};

export const AssistantScreen = () => {
  const { tenantId, projectId } = useAppContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    if (!input.trim()) {
      return;
    }
    const messageText = input.trim();
    const newMessage: Message = {
      id: `user-${Date.now()}`,
      author: 'user',
      text: messageText,
    };
    setMessages((prev) => [newMessage, ...prev]);
    setInput('');
    setSending(true);
    setError(null);
    try {
      const payload = await apiFetch('/api/assistant/send', {
        tenantId,
        method: 'POST',
        body: JSON.stringify({
          project_id: projectId,
          message: messageText,
        }),
      });
      const responseText =
        typeof payload?.response === 'string'
          ? payload.response
          : JSON.stringify(payload?.response ?? payload, null, 2);
      setMessages((prev) => [
        {
          id: `assistant-${Date.now()}`,
          author: 'assistant',
          text: responseText,
        },
        ...prev,
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reach assistant.');
    } finally {
      setSending(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.select({ ios: 'padding', android: undefined })}
    >
      <Text style={styles.heading}>Assistant</Text>
      <Text style={styles.subheading}>Chat with orchestration agents for next best actions.</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        data={messages}
        inverted
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <Card style={item.author === 'user' ? styles.userCard : styles.assistantCard}>
            <Text style={styles.messageAuthor}>{item.author === 'user' ? 'You' : 'Assistant'}</Text>
            <Text style={styles.messageText}>{item.text}</Text>
          </Card>
        )}
        ListEmptyComponent={!sending ? <Text style={styles.empty}>Send a message to get started.</Text> : null}
        contentContainerStyle={styles.listContent}
      />
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder="Ask about project status..."
          placeholderTextColor={colors.muted}
          value={input}
          onChangeText={setInput}
          multiline
        />
        <Pressable style={styles.sendButton} onPress={handleSend} disabled={sending}>
          <Text style={styles.sendButtonText}>{sending ? '...' : 'Send'}</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
  },
  heading: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.text,
  },
  subheading: {
    color: colors.muted,
    marginBottom: spacing.md,
  },
  error: {
    color: colors.danger,
    marginBottom: spacing.sm,
  },
  listContent: {
    paddingBottom: spacing.md,
  },
  userCard: {
    borderLeftWidth: 3,
    borderLeftColor: colors.accent,
  },
  assistantCard: {
    borderLeftWidth: 3,
    borderLeftColor: colors.success,
  },
  messageAuthor: {
    color: colors.muted,
    fontSize: 12,
    marginBottom: spacing.xs,
  },
  messageText: {
    color: colors.text,
  },
  empty: {
    color: colors.muted,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.card,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.card,
    borderRadius: radius.sm,
    padding: spacing.sm,
    color: colors.text,
    marginRight: spacing.sm,
    minHeight: 44,
  },
  sendButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radius.sm,
  },
  sendButtonText: {
    color: colors.background,
    fontWeight: '600',
  },
});
