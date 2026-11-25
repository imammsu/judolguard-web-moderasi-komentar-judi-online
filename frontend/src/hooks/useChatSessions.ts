import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../api/client';
import type { ChatSession, ChatSessionsData } from '../types/api';

export function useChatSessions(videoId: string | undefined, enabled = true) {
  const queryClient = useQueryClient();
  const queryKey = ['chat-sessions', videoId || null];
  const sessions = useQuery({
    queryKey,
    queryFn: () =>
      api.get<ChatSessionsData>(
        `/api/chat/sessions${videoId ? `?video_id=${encodeURIComponent(videoId)}` : ''}`,
      ),
    enabled,
  });
  const create = useMutation({
    mutationFn: () =>
      api.post<ChatSession>('/api/chat/sessions', {
        video_id: videoId || undefined,
      }),
    onSuccess: (session) => {
      queryClient.setQueryData<ChatSessionsData>(queryKey, (current) => ({
        items: [session, ...(current?.items ?? [])],
        total: (current?.total ?? 0) + 1,
      }));
    },
  });
  const remove = useMutation({
    mutationFn: (sessionId: string) =>
      api.delete<{ deleted: boolean }>(`/api/chat/sessions/${sessionId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
  });

  return {
    sessions: sessions.data?.items ?? [],
    sessionsLoading: sessions.isLoading,
    createSession: create.mutateAsync,
    creatingSession: create.isPending,
    deleteSession: remove.mutateAsync,
  };
}
