import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError, api } from '../api/client';
import type { MeData, UserProfile } from '../types/api';

/**
 * Status login dari sesi sisi server (cookie HttpOnly). Token OAuth tidak
 * pernah disentuh frontend: hanya profil channel dari GET /api/me.
 */
export function useAuth() {
  const qc = useQueryClient();

  const me = useQuery({
    queryKey: ['me'],
    queryFn: async (): Promise<UserProfile | null> => {
      try {
        const data = await api.get<MeData>('/api/me');
        return data.user;
      } catch (err) {
        // 401 = belum login (kondisi normal), bukan galat.
        if (err instanceof ApiError && err.status === 401) return null;
        throw err;
      }
    },
    retry: false,
    staleTime: 30_000,
  });

  const logout = useMutation({
    mutationFn: () => api.post<{ logged_out: boolean }>('/auth/logout'),
    onSuccess: () => qc.setQueryData(['me'], null),
  });

  // Mulai alur OAuth di backend; ?next=/videos mengembalikan pengguna ke halaman video setelah login.
  const login = (nextUrl = '/videos') => {
    window.location.href = `/auth/login?next=${encodeURIComponent(nextUrl)}`;
  };

  return {
    user: me.data ?? null,
    loading: me.isLoading,
    login,
    logout: () => logout.mutate(),
    loggingOut: logout.isPending,
  };
}
