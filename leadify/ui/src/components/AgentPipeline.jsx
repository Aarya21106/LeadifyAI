import { motion, AnimatePresence } from 'framer-motion';
import { useAgentWebSocket } from '../hooks/useAgentWebSocket';
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/20/solid';

const AGENTS = [
  { id: 'watch',    name: 'Watch',    icon: '👁',  initial: 'W' },
  { id: 'scout',    name: 'Scout',    icon: '🔭', initial: 'S' },
  { id: 'reader',   name: 'Reader',   icon: '📖', initial: 'R' },
  { id: 'scorer',   name: 'Scorer',   icon: '📊', initial: 'Sc' },
  { id: 'writer',   name: 'Writer',   icon: '✍️',  initial: 'Wr' },
  { id: 'reviewer', name: 'Reviewer', icon: '🔍', initial: 'Rv' },
];

const statusColors = {
  idle:    { border: 'var(--border)', bg: 'var(--bg-card)', text: 'var(--text-muted)' },
  running: { border: 'var(--blue)', bg: 'rgba(59,130,246,0.06)', text: 'var(--blue)' },
  done:    { border: 'var(--emerald)', bg: 'rgba(16,185,129,0.06)', text: 'var(--emerald)' },
  error:   { border: 'var(--rose)', bg: 'rgba(244,63,94,0.06)', text: 'var(--rose)' },
};

/* ─── Full Pipeline (LiveView) ─── */
export default function AgentPipeline({ mini = false }) {
  const { agentStatus, connected } = useAgentWebSocket();

  if (!agentStatus?.agents) {
    if (mini) return null;
    return (
      <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)', fontSize: 13 }}>
        {!connected
          ? <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <span className="skeleton" style={{ width: 12, height: 12, borderRadius: '50%' }} />
              Reconnecting to agent stream…
            </span>
          : 'Waiting for first cycle data…'
        }
      </div>
    );
  }

  if (mini) return <MiniPipeline agents={agentStatus.agents} />;

  const isComplete = agentStatus.cycle_complete;

  return (
    <div style={{ width: '100%' }}>
      {/* Status Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24,
      }}>
        <div>
          <p className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: 1.5, textTransform: 'uppercase' }}>
            Live Pipeline
          </p>
        </div>
        <StatusPill complete={isComplete} />
      </div>

      {/* Agent Cards Row + Connectors */}
      <div style={{
        display: 'flex', alignItems: 'stretch', gap: 0,
        width: '100%',
      }}>
        {AGENTS.map((agent, idx) => {
          const state = agentStatus.agents[agent.id] || { status: 'idle' };
          const sc = statusColors[state.status] || statusColors.idle;
          const isRunning = state.status === 'running';
          const isDone = state.status === 'done';
          const isError = state.status === 'error';

          return (
            <div key={agent.id} style={{ display: 'flex', alignItems: 'stretch', flex: 1, minWidth: 0 }}>
              {/* Card */}
              <motion.div
                layout
                animate={{
                  scale: isRunning ? 1.03 : 1,
                  boxShadow: isRunning
                    ? '0 0 24px rgba(59,130,246,0.2), 0 0 48px rgba(59,130,246,0.08)'
                    : '0 0 0 transparent',
                }}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                style={{
                  flex: 1,
                  minWidth: 0,
                  background: sc.bg,
                  border: `1px solid ${sc.border}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                {/* Top glow bar when running */}
                {isRunning && (
                  <motion.div
                    animate={{ opacity: [0.4, 0.8, 0.4] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    style={{
                      position: 'absolute', top: 0, left: 0, right: 0, height: 2,
                      background: 'var(--blue)',
                      boxShadow: '0 0 12px var(--blue)',
                    }}
                  />
                )}

                {/* Shimmer when running */}
                {isRunning && (
                  <motion.div
                    animate={{ x: ['-100%', '200%'] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    style={{
                      position: 'absolute', top: 0, left: 0, width: '40%', height: '100%',
                      background: 'linear-gradient(90deg, transparent, rgba(59,130,246,0.06), transparent)',
                      pointerEvents: 'none',
                    }}
                  />
                )}

                {/* Agent name row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 18 }}>{agent.icon}</span>
                  <span className="font-heading" style={{ fontSize: 13, fontWeight: 600, color: sc.text }}>
                    {agent.name}
                  </span>
                </div>

                {/* Status pill */}
                <span className="font-mono" style={{
                  fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1.2,
                  color: sc.text, opacity: 0.8,
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  {isRunning && (
                    <motion.span
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ duration: 1.2, repeat: Infinity }}
                      style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--blue)', display: 'inline-block' }}
                    />
                  )}
                  {isDone && <CheckCircleIcon style={{ width: 12, color: 'var(--emerald)' }} />}
                  {isError && <ExclamationTriangleIcon style={{ width: 12, color: 'var(--rose)' }} />}
                  {state.status}
                </span>

                {/* Summary */}
                <AnimatePresence mode="wait">
                  {state.summary && (
                    <motion.p
                      key={state.summary}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.4, minHeight: 28 }}
                    >
                      {state.summary}
                    </motion.p>
                  )}
                </AnimatePresence>

                {/* Error shake */}
                {isError && (
                  <motion.div
                    animate={{ x: [-3, 3, -3, 3, 0] }}
                    transition={{ duration: 0.4 }}
                    style={{ position: 'absolute', inset: 0, borderRadius: 'var(--radius-md)', border: '1px solid var(--rose)', pointerEvents: 'none' }}
                  />
                )}
              </motion.div>

              {/* Connector */}
              {idx < AGENTS.length - 1 && (
                <div style={{
                  width: 24, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0, position: 'relative',
                }}>
                  <svg width="24" height="4" viewBox="0 0 24 4">
                    {isDone ? (
                      <line x1="0" y1="2" x2="24" y2="2" stroke="var(--emerald)" strokeWidth="2" />
                    ) : isRunning ? (
                      <line x1="0" y1="2" x2="24" y2="2" stroke="var(--blue)" strokeWidth="2"
                        strokeDasharray="4 4"
                        style={{ animation: 'flow-dots 0.6s linear infinite' }}
                      />
                    ) : (
                      <line x1="0" y1="2" x2="24" y2="2" stroke="var(--text-ghost)" strokeWidth="1" strokeDasharray="3 3" />
                    )}
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Status Pill ─── */
function StatusPill({ complete }) {
  return (
    <motion.span
      layout
      className="font-mono"
      style={{
        fontSize: 10, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase',
        padding: '4px 12px', borderRadius: 20,
        display: 'inline-flex', alignItems: 'center', gap: 6,
        color: complete ? 'var(--emerald)' : 'var(--blue)',
        background: complete ? 'var(--emerald-glow)' : 'var(--blue-dim)',
        border: `1px solid ${complete ? 'rgba(16,185,129,0.25)' : 'rgba(59,130,246,0.2)'}`,
      }}
    >
      {!complete && (
        <motion.span
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.2, repeat: Infinity }}
          style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--blue)' }}
        />
      )}
      {complete ? 'Cycle Complete' : 'Processing'}
    </motion.span>
  );
}

/* ─── Mini Pipeline (top bar) ─── */
function MiniPipeline({ agents }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      {AGENTS.map((a, idx) => {
        const st = agents[a.id]?.status || 'idle';
        const sc = statusColors[st];
        return (
          <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
            <motion.div
              animate={{
                scale: st === 'running' ? [1, 1.15, 1] : 1,
                opacity: st === 'idle' ? 0.35 : 1,
              }}
              transition={st === 'running' ? { duration: 1.2, repeat: Infinity } : {}}
              title={`${a.name}: ${st}`}
              className="font-mono"
              style={{
                width: 26, height: 22, borderRadius: 4,
                background: sc.bg, border: `1px solid ${sc.border}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 9, fontWeight: 700, color: sc.text,
              }}
            >
              {a.initial}
            </motion.div>
            {idx < AGENTS.length - 1 && (
              <span style={{ width: 6, height: 1, background: 'var(--text-ghost)', display: 'block' }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
