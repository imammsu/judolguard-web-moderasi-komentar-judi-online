import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../api/client';
import type { ChatMessagesData, ChatResponse } from '../types/api';

export function useChatbot(sessionId: string | null, enabled = true) {
  const queryClient = useQueryClient();
  const messages = useQuery({
    queryKey: ['chat-messages', sessionId],
    queryFn: () =>
      api.get<ChatMessagesData>(`/api/chat/sessions/${sessionId}/messages`),
    enabled: enabled && Boolean(sessionId),
  });
  const mutation = useMutation({
    mutationFn: (payload: { question: string }) =>
      api.post<ChatResponse>('/api/chat', {
        question: payload.question,
        session_id: sessionId,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['chat-messages', sessionId] });
      void queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
  });

  return {
    ask: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error,
    reset: mutation.reset,
    messages: messages.data,
    messagesLoading: messages.isLoading,
  };
}
