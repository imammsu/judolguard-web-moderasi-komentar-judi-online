import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import type { VideoItem } from '../types/api';

export function useVideoDetail(videoId: string, enabled = true) {
  return useQuery({
    queryKey: ['video', videoId],
    queryFn: () => api.get<VideoItem>(`/api/videos/${encodeURIComponent(videoId)}`),
    enabled: Boolean(videoId) && enabled,
    staleTime: 30_000,
  });
}
