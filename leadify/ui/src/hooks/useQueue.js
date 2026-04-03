import { useQuery } from '@tanstack/react-query';
import { getQueue, getQueueStats } from '../lib/api';

export function useQueue() {
  const queue = useQuery({
    queryKey: ['queue'],
    queryFn: getQueue,
    refetchInterval: 15000,
  });

  const stats = useQuery({
    queryKey: ['queue-stats'],
    queryFn: getQueueStats,
    refetchInterval: 15000,
    placeholderData: { pending: 0, sent_today: 0, skipped_today: 0 },
  });

  return { queue, stats };
}
