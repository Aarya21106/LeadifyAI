import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import LeadDrawer from '../components/LeadDrawer'
import { Filter, Search, Plus, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { formatTimeAgo, cn } from '../utils'

export default function Leads() {
  const [statusFilter, setStatusFilter] = useState('active')
  const [selectedLeadId, setSelectedLeadId] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)

  const { data: leads, isLoading } = useQuery({
    queryKey: ['leads', statusFilter],
    queryFn: async () => {
      const res = await api.get('/leads', { params: { status: statusFilter } })
      return res.data
    }
  })

  // We could implement AddLead logic purely mapped via standard API forms
  const AddLeadForm = () => {
    // Basic unmanaged form for mockup context
    return (
      <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
        <div className="bg-bgPanel border border-borderSubtle rounded-md w-full max-w-md p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4">Add New Lead</h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-500 uppercase">Email</label>
              <input type="email" className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm mt-1" />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase">Name</label>
              <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm mt-1" />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase">Company</label>
              <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm mt-1" />
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <button onClick={() => setShowAddModal(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
              <button onClick={() => setShowAddModal(false)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-sm font-medium">Add Lead</button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header Actions */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-2">
          <div className="bg-[#1a212d] border border-borderSubtle rounded-md p-1 flex">
            {['active', 'paused', 'converted', 'dead'].map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={cn(
                  "px-4 py-1.5 rounded text-sm font-medium transition-colors capitalize",
                  statusFilter === s ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <button 
          onClick={() => setShowAddModal(true)}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg transition-transform hover:scale-105"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      {/* Table Data */}
      <div className="terminal-panel flex-1 overflow-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-borderSubtle bg-slate-900/50 sticky top-0 z-10 text-xs uppercase tracking-wider text-slate-500">
              <th className="px-6 py-4 font-medium">Lead</th>
              <th className="px-6 py-4 font-medium">Company</th>
              <th className="px-6 py-4 font-medium">Score</th>
              <th className="px-6 py-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-borderSubtle">
            {isLoading ? (
              <tr><td colSpan="4" className="text-center py-10 text-slate-500">Loading...</td></tr>
            ) : leads?.length === 0 ? (
              <tr><td colSpan="4" className="text-center py-10 text-slate-500">No {statusFilter} leads found.</td></tr>
            ) : (
              leads?.map(lead => {
                const score = lead.latest_score?.score || 0
                const delta = lead.latest_score?.delta || 0
                const deltaColor = delta >= 0 ? 'text-emerald-400' : 'text-rose-400'
                const DeltaIcon = delta >= 0 ? ArrowUpRight : ArrowDownRight

                return (
                  <tr 
                    key={lead.id} 
                    className="hover:bg-white/5 cursor-pointer transition-colors group"
                    onClick={() => setSelectedLeadId(lead.id)}
                  >
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-200 truncate">{lead.name || '-'}</div>
                      <div className="text-sm text-slate-500 truncate">{lead.email}</div>
                    </td>
                    <td className="px-6 py-4 text-slate-300">{lead.company || '-'}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2 font-mono">
                        <span className="text-lg text-slate-200">{score}</span>
                        {delta !== 0 && (
                          <span className={cn("text-xs flex items-center", deltaColor)}>
                            {delta > 0 ? '+' : ''}{delta} <DeltaIcon className="w-3 h-3 ml-0.5" />
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="text-sm font-medium text-indigo-400 hover:text-indigo-300 opacity-0 group-hover:opacity-100 transition-opacity">
                        View Context
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {showAddModal && <AddLeadForm />}
      {selectedLeadId && <LeadDrawer leadId={selectedLeadId} onClose={() => setSelectedLeadId(null)} />}
    </div>
  )
}
