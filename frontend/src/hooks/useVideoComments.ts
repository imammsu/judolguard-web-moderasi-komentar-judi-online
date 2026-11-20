import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import type { CommentsData } from '../types/api';

export interface CommentFilters {
  zone: string;
  search: string;
  sort: string;
  page: number;
  pageSize: number;
}

export function useVideoComments(videoId: string, filters: CommentFilters, enabled = true) {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize),
    sort: filters.sort,
  });
  if (filters.zone !== 'all') params.set('zone', filters.zone);
  if (filters.search.trim()) params.set('search', filters.search.trim());

  return useQuery({
    queryKey: ['video-comments', videoId, filters],
    queryFn: () =>
      api.get<CommentsData>(
        `/api/videos/${encodeURIComponent(videoId)}/comments?${params.toString()}`,
      ),
    enabled: Boolean(videoId) && enabled,
    placeholderData: keepPreviousData,
  });
}
