import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../api/client';
import type { JobData } from '../types/api';

interface ScanCreated {
  id: string;
  type: 'scan';
  video_id: string;
  status: JobData['status'];
  progress: number;
  total: number;
  processed: number;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export function useScanJob(videoId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      api.post<ScanCreated>(`/api/videos/${encodeURIComponent(videoId)}/scan`),
    onSuccess: (job) => {
      queryClient.setQueryData(['scan-job', job.id], job);
    },
  });

  const jobId = mutation.data?.id ?? '';
  const job = useQuery({
    queryKey: ['scan-job', jobId],
    queryFn: () => api.get<JobData>(`/api/tasks/${jobId}`),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'done' || status === 'failed' ? false : 1000;
    },
  });

  return {
    ...mutation,
    job: job.data,
    jobLoading: job.isFetching,
    resetJob: mutation.reset,
  };
}
