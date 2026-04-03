import { useQuery } from '@tanstack/react-query';
import { getLeads, getLead, getLeadHistory } from '../lib/api';

export function useLeads(status) {
  return useQuery({
    queryKey: ['leads', status],
    queryFn: () => getLeads(status),
    refetchInterval: 10000,
  });
}

export function useLead(id) {
  return useQuery({
    queryKey: ['lead', id],
    queryFn: () => getLead(id),
    enabled: !!id,
    refetchInterval: 10000,
  });
}

export function useLeadHistory(id) {
  return useQuery({
    queryKey: ['lead-history', id],
    queryFn: () => getLeadHistory(id),
    enabled: !!id,
    refetchInterval: 10000,
  });
}
