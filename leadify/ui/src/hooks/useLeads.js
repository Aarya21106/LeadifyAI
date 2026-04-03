import { useQuery } from '@tanstack/react-query';
import { getLeads, getLead } from '../lib/api';

export function useLeads(status) {
  return useQuery({
    queryKey: ['leads', status],
    queryFn: () => getLeads(status),
    refetchInterval: 30000,
  });
}

export function useLead(id) {
  return useQuery({
    queryKey: ['lead', id],
    queryFn: () => getLead(id),
    enabled: !!id,
  });
}
