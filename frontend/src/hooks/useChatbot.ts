import { useMutation } from '@tanstack/react-query';

import { api } from '../api/client';
import type { ChatMessage, ChatResponse } from '../types/api';

export function useChatbot(videoId?: string) {
  const mutation = useMutation({
    mutationFn: (payload: { question: string; history: ChatMessage[] }) =>
      api.post<ChatResponse>('/api/chat', {
        question: payload.question,
        video_id: videoId || undefined,
        history: payload.history,
      }),
  });

  return {
    ask: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error,
    reset: mutation.reset,
  };
}
