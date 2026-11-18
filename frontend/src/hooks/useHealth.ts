import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import type { HealthData } from '../types/api';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<HealthData>('/api/health'),
    refetchInterval: 15_000,
    retry: 1,
  });
}
