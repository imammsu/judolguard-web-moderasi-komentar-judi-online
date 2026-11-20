import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import type { KeywordsData } from '../types/api';

export function useVideoKeywords(videoId: string, enabled = true) {
  return useQuery({
    queryKey: ['video-keywords', videoId],
    queryFn: () => api.get<KeywordsData>(`/api/videos/${encodeURIComponent(videoId)}/keywords`),
    enabled: Boolean(videoId) && enabled,
  });
}
