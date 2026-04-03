import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { X, Pause, Play, CheckCircle, Clock } from 'lucide-react'
import { LineChart, Line, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts'
import { formatTimeAgo, cn } from '../utils'

export default function LeadDrawer({ leadId, onClose }) {
  const queryClient = useQueryClient()

  const { data: detail, isLoading } = useQuery({
    queryKey: ['lead', leadId],
    queryFn: async () => {
      const res = await api.get(`/leads/${leadId}`)
      return res.data
    },
    enabled: !!leadId
  })

  // To get timeline, we might need a history endpoint if lead detail doesn't include it.
  // The rules define LeadDetailRead which includes recent_events and latest_score.
  // Let's assume there's a /leads/{id}/history for the sparkline data.
  const { data: history } = useQuery({
    queryKey: ['lead-history', leadId],
    queryFn: async () => {
      const res = await api.get(`/leads/${leadId}/history`)
      return res.data
    },
    enabled: !!leadId
  })

  const updateStatusMutation = useMutation({
    mutationFn: (newStatus) => api.patch(`/leads/${leadId}`, { status: newStatus }),
    onSuccess: () => {
      queryClient.invalidateQueries(['leads'])
      queryClient.invalidateQueries(['lead', leadId])
    }
  })

  if (!leadId) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-[500px] bg-bgPanel border-l border-borderSubtle shadow-2xl z-50 flex flex-col overflow-hidden animate-in slide-in-from-right duration-200">
        <div className="flex justify-between items-center px-6 py-4 border-b border-borderSubtle bg-bgMain">
          <h2 className="text-lg font-medium text-slate-100">Lead Context</h2>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-md text-slate-400 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex-1 flex justify-center items-center">
            <p className="text-slate-500 animate-pulse">Loading...</p>
          </div>
        ) : detail ? (
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-8">
            {/* Header / Basic Info */}
            <div className="space-y-1">
              <div className="flex justify-between items-start">
                <h3 className="text-2xl font-semibold text-slate-100">{detail.name || detail.email}</h3>
                <span className={cn(
                  "px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wide",
                  detail.status === 'active' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                  detail.status === 'paused' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' :
                  detail.status === 'converted' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                )}>
                  {detail.status}
                </span>
              </div>
              <p className="text-slate-400">{detail.company}</p>
              <p className="text-slate-500 text-sm">{detail.email}</p>
            </div>

            {/* Quick Actions */}
            <div className="flex space-x-2">
              {detail.status === 'paused' ? (
                <button onClick={() => updateStatusMutation.mutate('active')} className="flex items-center px-3 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded transition-colors">
                  <Play className="w-3.5 h-3.5 mr-1.5" /> Resume
                </button>
              ) : (
                <button onClick={() => updateStatusMutation.mutate('paused')} className="flex items-center px-3 py-1.5 text-xs font-medium bg-amber-600 hover:bg-amber-500 text-white rounded transition-colors">
                  <Pause className="w-3.5 h-3.5 mr-1.5" /> Pause
                </button>
              )}
              <button 
                onClick={() => updateStatusMutation.mutate('converted')}
                disabled={detail.status === 'converted'}
                className="flex items-center px-3 py-1.5 text-xs font-medium border border-emerald-500 text-emerald-500 hover:bg-emerald-500/10 rounded transition-colors disabled:opacity-50"
              >
                <CheckCircle className="w-3.5 h-3.5 mr-1.5" /> Mark Converted
              </button>
            </div>

            {/* Sparkline */}
            <div>
              <h4 className="text-sm font-medium text-slate-300 uppercase tracking-wider mb-4 border-b border-borderSubtle pb-2">Score History</h4>
              <div className="h-24 w-full">
                {history?.scores?.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={history.scores}>
                      <Line type="monotone" dataKey="score" stroke="#818cf8" strokeWidth={2} dot={{ r: 3, fill: '#818cf8' }} activeDot={{ r: 5 }} />
                      <RechartsTooltip 
                        contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d', color: '#f8fafc', fontSize: '12px' }}
                        labelFormatter={(lbl, plts) => {
                          const item = plts[0]?.payload;
                          return item ? formatTimeAgo(item.scored_at) : '';
                        }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-slate-600 flex items-center h-full justify-center">No score history</p>
                )}
              </div>
            </div>

            {/* Event Timeline */}
            <div>
              <h4 className="text-sm font-medium text-slate-300 uppercase tracking-wider mb-4 border-b border-borderSubtle pb-2">Event Timeline</h4>
              <div className="space-y-4">
                {history?.events?.length > 0 ? (
                  history.events.map((ev, i) => (
                    <div key={ev.id || i} className="flex relative">
                      <div className="w-8 flex-shrink-0 flex flex-col items-center">
                        <div className="w-2 h-2 rounded-full bg-slate-600 mt-1.5" />
                        {i !== history.events.length - 1 && <div className="flex-1 w-px bg-slate-700/50 mt-2" />}
                      </div>
                      <div className="flex-1 pb-4">
                        <p className="text-sm text-slate-200 font-medium">
                          {ev.event_type.replace('_', ' ').toUpperCase()}
                        </p>
                        {ev.raw_data && ev.raw_data.subject && (
                          <p className="text-xs text-slate-400 mt-0.5">Subject: {ev.raw_data.subject}</p>
                        )}
                        {ev.raw_data && ev.raw_data.snippet && (
                          <p className="text-xs text-slate-500 italic mt-1 line-clamp-2">"{ev.raw_data.snippet}"</p>
                        )}
                        <p className="text-xs text-slate-600 mt-1 flex items-center"><Clock className="w-3 h-3 mr-1" /> {formatTimeAgo(ev.detected_at)}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-600">No events recorded</p>
                )}
              </div>
            </div>

          </div>
        ) : (
          <div className="p-6 text-slate-400">Failed to load lead</div>
        )}
      </div>
    </>
  )
}
