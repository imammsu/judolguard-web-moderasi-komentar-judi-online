import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../api/client';
import type { VideosData } from '../types/api';

export function useVideos(page: number, pageSize = 12, enabled = true) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['videos', page, pageSize],
    queryFn: () => api.get<VideosData>(`/api/videos?page=${page}&page_size=${pageSize}`),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });

  const refresh = async () => {
    const data = await api.get<VideosData>(
      `/api/videos?page=${page}&page_size=${pageSize}&refresh=true`,
    );
    queryClient.setQueryData(['videos', page, pageSize], data);
    return data;
  };

  return { ...query, refresh };
}
