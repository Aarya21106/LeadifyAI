import { useState, useEffect } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  InboxIcon, UsersIcon, Cog6ToothIcon,
  BoltIcon, PlayIcon,
} from '@heroicons/react/24/outline';
import { SignalIcon } from '@heroicons/react/24/solid';
import { runAgents, getGmailStatus, getAgentStatus } from '../lib/api';
import AgentPipeline from './AgentPipeline';

const NAV = [
  { name: 'Queue',    path: '/queue',    icon: InboxIcon },
  { name: 'Leads',    path: '/leads',    icon: UsersIcon },
  { name: 'Live',     path: '/live',     icon: BoltIcon },
  { name: 'Settings', path: '/settings', icon: Cog6ToothIcon },
];

const pageTitles = {
  '/queue': 'Draft Queue',
  '/leads': 'Lead Pipeline',
  '/live': 'Live Agent Monitor',
  '/settings': 'Settings',
};

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const queryClient = useQueryClient();
  const title = pageTitles[location.pathname] || 'Leadify';

  // Gmail status
  const { data: gmail } = useQuery({
    queryKey: ['gmail-status'],
    queryFn: getGmailStatus,
    retry: false,
    placeholderData: { connected: false },
  });

  // Agent status (for cycle countdown)
  const { data: agentData } = useQuery({
    queryKey: ['agent-status'],
    queryFn: getAgentStatus,
    refetchInterval: 10000,
    placeholderData: {},
  });

  // Run agents mutation
  const runMutation = useMutation({
    mutationFn: runAgents,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-status'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
  });

  const isRunning = agentData?.cycle_complete === false && agentData?.agents;
  const gmailConnected = gmail?.connected;

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-void)' }}>

      {/* ─── Sidebar ─── */}
      <motion.aside
        className="sidebar-desktop"
        onMouseEnter={() => setSidebarOpen(true)}
        onMouseLeave={() => setSidebarOpen(false)}
        animate={{ width: sidebarOpen ? 200 : 64 }}
        transition={{ type: 'spring', stiffness: 300, damping: 28 }}
        style={{
          height: '100vh', display: 'flex', flexDirection: 'column',
          background: 'var(--bg-surface)', borderRight: '1px solid var(--border)',
          overflow: 'hidden', flexShrink: 0, zIndex: 50,
        }}
      >
        {/* Logo */}
        <div style={{
          height: 64, display: 'flex', alignItems: 'center', gap: 10,
          padding: '0 18px', borderBottom: '1px solid var(--border)',
          overflow: 'hidden', flexShrink: 0,
        }}>
          <motion.div
            animate={{ scale: [1, 1.15, 1], opacity: [0.7, 1, 0.7] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              width: 10, height: 10, borderRadius: '50%',
              background: 'var(--blue)', flexShrink: 0,
              boxShadow: '0 0 10px var(--blue)',
            }}
          />
          <AnimatePresence>
            {sidebarOpen && (
              <motion.span
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                className="font-heading"
                style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}
              >
                Leadify
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Nav Items */}
        <nav style={{ flex: 1, padding: '16px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {NAV.map((item) => {
            const active = location.pathname === item.path;
            return (
              <NavLink key={item.path} to={item.path} style={{ textDecoration: 'none' }}>
                <motion.div
                  whileHover={{ background: 'var(--bg-hover)' }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 14px', borderRadius: 'var(--radius-sm)',
                    position: 'relative', overflow: 'hidden',
                    color: active ? 'var(--blue)' : 'var(--text-secondary)',
                    background: active ? 'var(--blue-dim)' : 'transparent',
                    transition: 'color 0.2s',
                  }}
                >
                  {active && (
                    <motion.div
                      layoutId="nav-indicator"
                      style={{
                        position: 'absolute', left: 0, top: '15%', bottom: '15%', width: 3,
                        background: 'var(--blue)', borderRadius: 4,
                      }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  )}
                  <item.icon style={{ width: 20, height: 20, flexShrink: 0 }} />
                  <AnimatePresence>
                    {sidebarOpen && (
                      <motion.span
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -6 }}
                        style={{ fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap' }}
                      >
                        {item.name}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </motion.div>
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom: Gmail + Countdown */}
        <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
              background: gmailConnected ? 'var(--emerald)' : 'var(--rose)',
              boxShadow: gmailConnected ? '0 0 8px var(--emerald)' : '0 0 8px var(--rose)',
            }} />
            <AnimatePresence>
              {sidebarOpen && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}
                >
                  Gmail {gmailConnected ? 'connected' : 'disconnected'}
                </motion.span>
              )}
            </AnimatePresence>
          </div>

          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="font-mono"
              style={{ marginTop: 8, fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}
            >
              <CycleCountdown lastCycleAt={agentData?.cycle_start} />
            </motion.div>
          )}
        </div>
      </motion.aside>

      {/* ─── Main ─── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>

        {/* Top Bar */}
        <header style={{
          height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 28px', borderBottom: '1px solid var(--border)',
          background: 'rgba(10,10,15,0.8)', backdropFilter: 'blur(16px)',
          flexShrink: 0, zIndex: 40,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <h1 className="font-heading" style={{ fontSize: 16, fontWeight: 700 }}>{title}</h1>
            {isRunning && <AgentPipeline mini />}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isRunning && (
              <motion.span
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="font-mono"
                style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: 1.5,
                  color: 'var(--blue)', padding: '3px 10px',
                  borderRadius: 20, background: 'var(--blue-dim)',
                  border: '1px solid rgba(59,130,246,0.2)',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}
              >
                <motion.span
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--blue)' }}
                />
                CYCLE RUNNING
              </motion.span>
            )}

            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '7px 16px', borderRadius: 'var(--radius-sm)',
                background: 'var(--blue)', color: 'white',
                fontSize: 13, fontWeight: 600,
                opacity: runMutation.isPending ? 0.6 : 1,
              }}
            >
              {runMutation.isPending ? (
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                  style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block' }}
                />
              ) : (
                <PlayIcon style={{ width: 14 }} />
              )}
              Run Agents Now
            </motion.button>
          </div>
        </header>

        {/* Page Content */}
        <main style={{ flex: 1, overflowY: 'auto', padding: 28, background: 'var(--bg-void)' }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

/* ─── Cycle Countdown ─── */
function CycleCountdown({ lastCycleAt }) {
  const [display, setDisplay] = useState('--:--');

  useEffect(() => {
    if (!lastCycleAt) return;
    const interval = 60 * 60 * 1000;
    const update = () => {
      const next = new Date(lastCycleAt).getTime() + interval;
      const diff = Math.max(0, next - Date.now());
      const m = Math.floor(diff / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setDisplay(`${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`);
    };
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, [lastCycleAt]);

  return <span>Next run {display}</span>;
}
