import { useState, useEffect } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Inbox, Users, Settings, Play, Mail, Activity, Loader2 } from 'lucide-react'
import { cn } from '../utils'

function Countdown({ lastCycleAt, isRunning }) {
  const [timeLeft, setTimeLeft] = useState('--:--');

  useEffect(() => {
    if (!lastCycleAt) return;
    // Assuming a 60 min cycle for display. If Settings interval is fetched, use it.
    const intervalMs = 60 * 60 * 1000;
    
    const updateCountdown = () => {
      const lastRun = new Date(lastCycleAt).getTime();
      const nextRun = lastRun + intervalMs;
      const now = new Date().getTime();
      
      const diff = nextRun - now;
      if (diff <= 0) {
        setTimeLeft('00:00');
        return;
      }
      
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      setTimeLeft(`${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
    };

    updateCountdown();
    const timer = setInterval(updateCountdown, 1000);
    return () => clearInterval(timer);
  }, [lastCycleAt]);

  if (isRunning) {
    return <span className="text-indigo-400 animate-pulse font-mono flex items-center">Cycle running <Loader2 className="w-3 h-3 ml-2 animate-spin" /></span>;
  }

  return <span className="font-mono text-slate-400">Next cycle in: {timeLeft}</span>;
}


export default function Layout() {
  const queryClient = useQueryClient()

  // Poll agent status every 10 seconds
  const { data: statusData, isFetching: statusFetching } = useQuery({
    queryKey: ['agent-status'],
    queryFn: async () => {
      const res = await api.get('/agents/status')
      return res.data
    },
    refetchInterval: 10000,
  })

  // Basic gmail status check
  const { data: gmailStatus } = useQuery({
    queryKey: ['gmail-status'],
    queryFn: async () => {
      try {
        const res = await api.get('/auth/gmail/status')
        return res.data
      } catch {
        return { connected: false }
      }
    },
    retry: false
  })

  // Run cycle mutation
  const runMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/agents/run')
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-status'] })
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    }
  })

  const isGmailConnected = gmailStatus?.connected;
  const navItems = [
    { name: 'Queue', path: '/queue', icon: Inbox },
    { name: 'Leads', path: '/leads', icon: Users },
    { name: 'Settings', path: '/settings', icon: Settings },
  ]

  return (
    <div className="flex h-screen bg-bgMain overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-borderSubtle bg-bgPanel flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-borderSubtle">
          <Activity className="w-6 h-6 text-indigo-500 mr-2" />
          <h1 className="text-xl font-bold tracking-tight text-slate-100">Leadify AI</h1>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accentSubtle text-indigo-400"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                )
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Status Indicator */}
        <div className="p-4 border-t border-borderSubtle">
          <div className="flex items-center text-xs font-medium text-slate-400">
            <div className={cn(
              "w-2 h-2 rounded-full mr-2",
              isGmailConnected ? "bg-emerald-500" : "bg-red-500"
            )} />
            Gmail {isGmailConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top bar */}
        <header className="h-16 border-b border-borderSubtle bg-bgMain/80 backdrop-blur-md flex items-center justify-between px-8 z-10">
          <div className="flex items-center text-sm">
            <Countdown 
              lastCycleAt={statusData?.last_cycle_at} 
              isRunning={runMutation.isPending} 
            />
          </div>
          
          <button 
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-sm font-medium transition-colors"
          >
            <Play className="w-4 h-4 mr-2" />
            Run Now
          </button>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-bgMain p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
