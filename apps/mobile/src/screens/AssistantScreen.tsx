import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';

import { apiFetch } from '../api/client';
import { Card } from '../components/Card';
import { useAppContext } from '../context/AppContext';
import { colors, radius, spacing } from '../theme';

type Message = {
  id: string;
  author: 'user' | 'assistant';
  text: string;
};

type RecordingState = 'idle' | 'recording' | 'processing';

export const AssistantScreen = () => {
  const { tenantId, projectId } = useAppContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [speechAvailable, setSpeechAvailable] = useState(false);

  useEffect(() => {
    const checkSpeech = async () => {
      try {
        const voices = await Speech.getAvailableVoicesAsync();
        setSpeechAvailable(voices.length > 0);
      } catch {
        setSpeechAvailable(false);
      }
    };
    void checkSpeech();
  }, []);

  const handleSend = async (messageText?: string) => {
    const text = messageText || input.trim();
    if (!text) {
      return;
    }
    const newMessage: Message = {
      id: `user-${Date.now()}`,
      author: 'user',
      text,
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
          message: text,
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

  const startRecording = useCallback(async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('Permission Required', 'Microphone access is needed for voice input.');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(newRecording);
      setRecordingState('recording');
    } catch (err) {
      Alert.alert('Recording Error', 'Unable to start voice recording. Please check permissions.');
      setRecordingState('idle');
    }
  }, []);

  const stopRecording = useCallback(async () => {
    if (!recording) {
      return;
    }

    setRecordingState('processing');
    try {
      await recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });

      const uri = recording.getURI();
      setRecording(null);

      if (!uri) {
        setRecordingState('idle');
        return;
      }

      const formData = new FormData();
      formData.append('audio', {
        uri,
        type: 'audio/m4a',
        name: 'voice-input.m4a',
      } as any);
      formData.append('project_id', projectId);

      try {
        const transcriptionPayload = await apiFetch('/api/assistant/transcribe', {
          tenantId,
          method: 'POST',
          body: formData,
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        const transcribedText =
          typeof transcriptionPayload?.text === 'string'
            ? transcriptionPayload.text
            : '';

        if (transcribedText) {
          setInput(transcribedText);
        }
      } catch {
        Alert.alert(
          'Transcription Unavailable',
          'Voice transcription service is not available. Your recording has been saved.'
        );
      }
    } catch (err) {
      Alert.alert('Recording Error', 'Unable to process voice recording.');
    } finally {
      setRecordingState('idle');
    }
  }, [recording, projectId, tenantId]);

  const handleVoicePress = useCallback(() => {
    if (recordingState === 'recording') {
      void stopRecording();
    } else if (recordingState === 'idle') {
      void startRecording();
    }
  }, [recordingState, startRecording, stopRecording]);

  const speakResponse = useCallback((text: string) => {
    if (!speechAvailable) {
      return;
    }
    Speech.stop();
    Speech.speak(text, {
      language: 'en-US',
      rate: 0.9,
      pitch: 1.0,
    });
  }, [speechAvailable]);

  const voiceButtonLabel = () => {
    switch (recordingState) {
      case 'recording':
        return 'Stop';
      case 'processing':
        return '...';
      default:
        return 'Mic';
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
            <View style={styles.messageHeader}>
              <Text style={styles.messageAuthor}>
                {item.author === 'user' ? 'You' : 'Assistant'}
              </Text>
              {item.author === 'assistant' && speechAvailable && (
                <Pressable onPress={() => speakResponse(item.text)} style={styles.speakButton}>
                  <Text style={styles.speakButtonText}>Listen</Text>
                </Pressable>
              )}
            </View>
            <Text style={styles.messageText}>{item.text}</Text>
          </Card>
        )}
        ListEmptyComponent={
          !sending ? <Text style={styles.empty}>Send a message to get started.</Text> : null
        }
        contentContainerStyle={styles.listContent}
      />
      <View style={styles.inputRow}>
        <Pressable
          style={[
            styles.voiceButton,
            recordingState === 'recording' && styles.voiceButtonRecording,
          ]}
          onPress={handleVoicePress}
          disabled={recordingState === 'processing'}
        >
          <Text style={styles.voiceButtonText}>{voiceButtonLabel()}</Text>
        </Pressable>
        <TextInput
          style={styles.input}
          placeholder="Ask about project status..."
          placeholderTextColor={colors.muted}
          value={input}
          onChangeText={setInput}
          multiline
        />
        <Pressable style={styles.sendButton} onPress={() => handleSend()} disabled={sending}>
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
  messageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  messageAuthor: {
    color: colors.muted,
    fontSize: 12,
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
  voiceButton: {
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.sm,
    marginRight: spacing.sm,
    minWidth: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.card,
  },
  voiceButtonRecording: {
    backgroundColor: colors.danger,
    borderColor: colors.danger,
  },
  voiceButtonText: {
    color: colors.text,
    fontWeight: '600',
    fontSize: 12,
  },
  speakButton: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.sm,
    backgroundColor: colors.surface,
  },
  speakButtonText: {
    color: colors.accent,
    fontSize: 11,
    fontWeight: '600',
  },
});
