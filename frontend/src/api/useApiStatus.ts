import { useQuery } from '@tanstack/react-query'

import { api } from './client'

/** GET /readyz: the API is up and reaches its database. */
export function useApiStatus() {
  return useQuery({
    queryKey: ['readyz'],
    queryFn: async () => {
      const { data, error } = await api.GET('/readyz')
      if (error !== undefined || data === undefined) throw new Error('API unavailable')
      return data
    },
    refetchInterval: 60_000,
  })
}
