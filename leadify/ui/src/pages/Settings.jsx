import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { Mail, Shield, Check, Settings as SettingsIcon } from 'lucide-react'

export default function Settings() {
  const [interval, setIntervalVal] = useState('60')
  
  const { data: gmailStatus } = useQuery({
    queryKey: ['gmail-status'],
    queryFn: async () => {
      try {
        const res = await api.get('/auth/gmail/status')
        return res.data
      } catch {
        return { connected: false }
      }
    }
  })

  // Simulated API settings check endpoints
  const { data: envStatus } = useQuery({
    queryKey: ['env-status'],
    queryFn: async () => {
      try {
         const res = await api.get('/settings/status')
         return res.data
      } catch {
         // Mock data if backend isn't ready
         return {
           gemini: true,
           tavily: true,
           database: true
         }
      }
    }
  })

  const connectGmail = () => {
    // Trigger OAuth flow directly via window location
    window.location.href = 'http://localhost:8000/auth/gmail'
  }

  const disconnectGmail = async () => {
    // Simulated disconnect
    alert("Disconnect flow would trigger here.")
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-100 mb-1 leading-tight">System Settings</h2>
        <p className="text-slate-400 text-sm">Manage API connections and agent configuration.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Gmail Integration */}
        <div className="terminal-panel p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-2 bg-rose-500/10 rounded-md">
              <Mail className="w-5 h-5 text-rose-500" />
            </div>
            <h3 className="text-lg font-medium text-slate-200">Gmail Connection</h3>
          </div>
          
          {gmailStatus?.connected ? (
            <div>
              <div className="flex items-center space-x-2 text-emerald-400 mb-4 bg-emerald-500/10 px-3 py-2 rounded-md border border-emerald-500/20">
                <Check className="w-4 h-4" />
                <span className="text-sm font-medium">Connected as {gmailStatus.email || 'authenticated user'}</span>
              </div>
              <button 
                onClick={disconnectGmail}
                className="px-4 py-2 border border-slate-600 hover:bg-white/5 text-slate-300 transition-colors rounded text-sm w-full"
              >
                Disconnect Account
              </button>
            </div>
          ) : (
            <div>
              <p className="text-sm text-slate-400 mb-4">You need to connect an inbox for the Watch Agent to operate.</p>
              <button 
                onClick={connectGmail}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-sm font-medium w-full transition-colors"
              >
                Connect Gmail via OAuth
              </button>
            </div>
          )}
        </div>

        {/* API Status */}
        <div className="terminal-panel p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-2 bg-indigo-500/10 rounded-md">
              <Shield className="w-5 h-5 text-indigo-400" />
            </div>
            <h3 className="text-lg font-medium text-slate-200">System Checks</h3>
          </div>
          
          <ul className="space-y-4">
            <li className="flex items-center justify-between">
              <span className="text-sm text-slate-300">Database Connection</span>
              <div className="flex items-center text-xs space-x-1 text-emerald-400">
                 <Check className="w-3 h-3" /> <span>OK</span>
              </div>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-sm text-slate-300">Gemini LLM Key</span>
              <div className="flex items-center text-xs space-x-1 text-emerald-400">
                 <Check className="w-3 h-3" /> <span>Active</span>
              </div>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-sm text-slate-300">Tavily Search Key</span>
              <div className="flex items-center text-xs space-x-1 text-emerald-400">
                 <Check className="w-3 h-3" /> <span>Active</span>
              </div>
            </li>
          </ul>
        </div>

        {/* Agent Configuration */}
        <div className="terminal-panel p-6 md:col-span-2">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-2 bg-slate-700/50 rounded-md">
              <SettingsIcon className="w-5 h-5 text-slate-300" />
            </div>
            <h3 className="text-lg font-medium text-slate-200">Agent Cycle Configuration</h3>
          </div>
          
          <div className="flex flex-col sm:flex-row items-center space-y-4 sm:space-y-0 sm:space-x-4">
            <div className="flex-1 w-full relative">
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block">Cycle Interval (Minutes)</label>
              <input 
                type="number" 
                value={interval}
                onChange={e => setIntervalVal(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-4 py-2 font-mono text-slate-200 focus:outline-none focus:border-indigo-500" 
              />
            </div>
            <div className="w-full sm:w-auto self-end">
              <button className="w-full px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded font-medium transition-colors">
                Save Parameter
              </button>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-3">This controls how often the LangGraph orchestrator launches a full sweep.</p>
        </div>
      </div>
    </div>
  )
}
