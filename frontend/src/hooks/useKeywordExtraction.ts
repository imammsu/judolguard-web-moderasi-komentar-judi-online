import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { api } from '../api/client';
import type { JobData } from '../types/api';

export function useKeywordExtraction(videoId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      api.post<JobData>(`/api/videos/${encodeURIComponent(videoId)}/keywords/extract`),
    onSuccess: (job) => {
      queryClient.setQueryData(['keyword-extraction-job', job.id], job);
    },
  });

  const jobId = mutation.data?.id ?? '';
  const job = useQuery({
    queryKey: ['keyword-extraction-job', jobId],
    queryFn: () => api.get<JobData>(`/api/tasks/${jobId}`),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'done' || status === 'failed' ? false : 1000;
    },
  });

  useEffect(() => {
    if (job.data?.status === 'done') {
      void queryClient.invalidateQueries({ queryKey: ['video-keywords', videoId] });
    }
  }, [job.data?.status, queryClient, videoId]);

  return {
    start: mutation.mutate,
    startAsync: mutation.mutateAsync,
    startPending: mutation.isPending,
    startError: mutation.error,
    job: job.data,
    jobLoading: job.isFetching,
  };
}
