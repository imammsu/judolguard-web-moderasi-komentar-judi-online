import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../api/client';
import type { TelegramPairingData, TelegramStatusData } from '../types/api';

export function useTelegramPairing(waitingForPairing = false) {
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: ['telegram-status'],
    queryFn: () => api.get<TelegramStatusData>('/api/telegram/status'),
    refetchInterval: waitingForPairing ? 2000 : false,
  });
  const pairing = useMutation({
    mutationFn: () => api.post<TelegramPairingData>('/api/telegram/pairing'),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telegram-status'] });
    },
  });

  return {
    status: status.data,
    statusLoading: status.isLoading,
    statusError: status.error,
    createPairing: pairing.mutateAsync,
    creatingPairing: pairing.isPending,
    pairingError: pairing.error,
  };
}
