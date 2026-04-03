import { useState } from 'react'
import { FileEdit, Send, X, ArrowUpRight, ArrowDownRight, MessageSquare, AlertCircle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { cn } from '../utils'

export default function DraftCard({ draftObj }) {
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const { draft, lead } = draftObj
  
  const [subject, setSubject] = useState(draft.subject)
  const [body, setBody] = useState(draft.body)

  const sendMutation = useMutation({
    mutationFn: () => api.post(`/queue/${draft.id}/approve`),
    onSuccess: () => queryClient.invalidateQueries(['queue'])
  })

  const skipMutation = useMutation({
    mutationFn: () => api.post(`/queue/${draft.id}/skip`),
    onSuccess: () => queryClient.invalidateQueries(['queue'])
  })

  const saveMutation = useMutation({
    mutationFn: (data) => api.patch(`/queue/${draft.id}`, data),
    onSuccess: () => {
      setIsEditing(false)
      queryClient.invalidateQueries(['queue'])
    }
  })

  // Simulated Delta (assuming lead.latest_score.delta exists, otherwise using score > 50 indicator)
  // Backend gives draft with score_at_draft. Real delta logic might need a LeadScore relation. 
  // Let's assume queue drafts come with latest_score on the Lead or a delta field.
  const delta = lead.latest_score?.delta || 0;
  const score = draft.score_at_draft;
  
  const badgeColor = score >= 60 ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 
                     score >= 30 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 
                     'bg-rose-500/20 text-rose-400 border-rose-500/30';

  const deltaColor = delta >= 0 ? 'text-emerald-400' : 'text-rose-400';
  const DeltaIcon = delta >= 0 ? ArrowUpRight : ArrowDownRight;

  return (
    <div className="terminal-panel p-5 hover:border-slate-600 transition-colors group">
      {/* Header Info */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-medium text-slate-200 leading-tight">{lead.name || lead.email}</h3>
          <p className="text-sm text-slate-500">{lead.company || 'Unknown Company'} <span className="opacity-50 mx-1">•</span> {lead.email}</p>
        </div>
        
        <div className="flex flex-col items-end">
          <div className={cn("px-3 py-1 rounded border text-xl font-mono font-bold flex items-center space-x-2", badgeColor)}>
            <span>{score}</span>
            {delta !== 0 && (
              <span className={cn("text-xs flex items-center", deltaColor)}>
                ({delta > 0 ? '+' : ''}{delta} <DeltaIcon className="w-3 h-3 ml-0.5" />)
              </span>
            )}
          </div>
        </div>
      </div>

      {draft.signal_summary && (
        <div className="mb-4 text-xs italic text-indigo-300 bg-indigo-500/10 px-3 py-2 rounded flex items-start">
          <AlertCircle className="w-4 h-4 mr-2 mt-0.5 opacity-70 flex-shrink-0" />
          <p>{draft.signal_summary}</p>
        </div>
      )}

      {/* Editor / Viewer */}
      <div className="bg-[#0e1117] rounded-md border border-borderSubtle p-4 mb-4">
        {isEditing ? (
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-1 block">Subject</label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-1 block">Body</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={6}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 whitespace-pre-wrap font-sans focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex justify-end space-x-2 mt-2">
              <button 
                onClick={() => setIsEditing(false)}
                className="px-3 py-1.5 text-sm text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button 
                onClick={() => saveMutation.mutate({ subject, body })}
                disabled={saveMutation.isPending}
                className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm disabled:opacity-50"
              >
                Save Edits
              </button>
            </div>
          </div>
        ) : (
          <div className="group/content text-sm">
            <p className="font-medium text-slate-200 mb-2 border-b border-borderSubtle pb-2">Subject: {draft.subject}</p>
            <p className="whitespace-pre-wrap text-slate-400 font-sans leading-relaxed">{draft.body}</p>
          </div>
        )}
      </div>

      {/* Actions */}
      {!isEditing && (
        <div className="flex justify-end space-x-3 mt-4">
          <button 
            onClick={() => skipMutation.mutate()}
            disabled={skipMutation.isPending}
            className="flex items-center px-4 py-2 text-sm font-medium text-rose-400 hover:bg-rose-500/10 rounded transition-colors disabled:opacity-50"
          >
            <X className="w-4 h-4 mr-2" /> Skip
          </button>
          
          <button 
             onClick={() => setIsEditing(true)}
             className="flex items-center px-4 py-2 text-sm font-medium text-blue-400 hover:bg-blue-500/10 rounded transition-colors"
          >
             <FileEdit className="w-4 h-4 mr-2" /> Edit
          </button>
          
          <button 
             onClick={() => sendMutation.mutate()}
             disabled={sendMutation.isPending}
             className="flex items-center px-4 py-2 text-sm font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded transition-colors disabled:opacity-50"
          >
             <Send className="w-4 h-4 mr-2" /> Send ✓
          </button>
        </div>
      )}
    </div>
  )
}
