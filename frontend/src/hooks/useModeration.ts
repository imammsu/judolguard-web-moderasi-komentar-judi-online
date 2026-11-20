import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '../api/client';
import type { RejectPreviewData, RejectSummary } from '../types/api';

export type RejectTarget =
  | { comment_ids: string[] }
  | { video_id: string; all_judol: true };

export function useModeration(videoId: string) {
  const queryClient = useQueryClient();
  const preview = useMutation({
    mutationFn: (target: RejectTarget) =>
      api.post<RejectPreviewData>('/api/comments/reject/preview', target),
  });
  const reject = useMutation({
    mutationFn: (target: RejectTarget) =>
      api.post<RejectSummary>('/api/comments/reject', {
        ...target,
        confirmed: true,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['video-comments', videoId] });
      void queryClient.invalidateQueries({ queryKey: ['video', videoId] });
    },
  });

  return { preview, reject };
}
