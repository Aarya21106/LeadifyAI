import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import DraftCard from '../components/DraftCard'
import { Loader2 } from 'lucide-react'

export default function Queue() {
  // Fetch pending drafts
  const { data, isLoading } = useQuery({
    queryKey: ['queue'],
    queryFn: async () => {
      const res = await api.get('/queue/pending')
      return res.data
    },
    refetchInterval: 30000,
  })

  // Fetch stats separately (stubbed structure for UI purposes)
  const { data: stats } = useQuery({
    queryKey: ['queue-stats'],
    queryFn: async () => {
      try {
        const res = await api.get('/queue/stats')
        return res.data
      } catch (e) {
        return { pending: 0, sent_today: 0, skipped_today: 0 }
      }
    },
    refetchInterval: 30000,
  })

  const draftsToRender = data || []
  
  // Sort descending by score_at_draft just in case backend doesnt ensure it
  const sortedDrafts = [...draftsToRender].sort((a, b) => b.draft.score_at_draft - a.draft.score_at_draft)

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header Stats */}
      <div className="flex items-center space-x-4 mb-8">
        <div className="bg-bgPanel border border-borderSubtle rounded-md px-4 py-2 flex items-center shadow-lg">
          <span className="text-sm text-slate-500 mr-2">Pending</span>
          <span className="text-lg font-mono font-medium text-slate-200">{stats?.pending || draftsToRender.length || 0}</span>
        </div>
        <div className="bg-bgPanel border border-borderSubtle bg-emerald-500/5 rounded-md px-4 py-2 flex items-center shadow-lg border-emerald-500/20">
          <span className="text-sm text-emerald-500 mr-2">Sent today</span>
          <span className="text-lg font-mono font-medium text-emerald-400">{stats?.sent_today || 0}</span>
        </div>
        <div className="bg-bgPanel border border-borderSubtle bg-rose-500/5 rounded-md px-4 py-2 flex items-center shadow-lg border-rose-500/20">
          <span className="text-sm text-rose-500 mr-2">Skipped</span>
          <span className="text-lg font-mono font-medium text-rose-400">{stats?.skipped_today || 0}</span>
        </div>
      </div>

      <div className="space-y-6">
        {isLoading ? (
          <div className="py-20 flex justify-center items-center text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : sortedDrafts.length === 0 ? (
          <div className="py-20 flex flex-col justify-center items-center text-slate-400 border border-dashed border-borderSubtle rounded-lg bg-bgPanel/50">
            <p className="text-lg mb-2 text-slate-300">No drafts pending.</p>
            <p className="text-sm">Agents will generate new drafts at their next cycle.</p>
          </div>
        ) : (
          sortedDrafts.map((obj) => (
            <DraftCard key={obj.draft.id} draftObj={obj} />
          ))
        )}
      </div>
    </div>
  )
}
