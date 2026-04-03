import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAgentWebSocket } from '../hooks/useAgentWebSocket';
import AgentPipeline from '../components/AgentPipeline';
import { ClockIcon } from '@heroicons/react/24/outline';

function LiveTimer({ startTime, running }) {
  const [elapsed, setElapsed] = useState('00:00:00');
  useEffect(() => {
    if (!startTime) return;
    const update = () => {
      const diff = Math.max(0, Date.now() - new Date(startTime).getTime());
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setElapsed(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`);
    };
    update();
    if (running) {
      const t = setInterval(update, 1000);
      return () => clearInterval(t);
    }
  }, [startTime, running]);
  return <span>{elapsed}</span>;
}

export default function LiveView() {
  const { agentStatus, connected } = useAgentWebSocket();
  const data = agentStatus || {};
  const isRunning = data.agents && data.cycle_complete === false;
  const isComplete = data.cycle_complete === true;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', height: '100%', display: 'flex', flexDirection: 'column' }}>

      {/* ─── Cycle Info Bar ─── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: 20, padding: '14px 20px', borderRadius: 'var(--radius-md)',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          marginBottom: 28, flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
          {/* Cycle ID */}
          <div>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Cycle ID</span>
            <p className="font-mono" style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              {data.cycle_id ? data.cycle_id.slice(0, 8) + '…' : '——'}
            </p>
          </div>

          {/* Started At */}
          <div>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Started</span>
            <p className="font-mono" style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              {data.cycle_start ? new Date(data.cycle_start).toLocaleTimeString() : '——'}
            </p>
          </div>

          {/* Duration */}
          <div>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Duration</span>
            <p className="font-mono" style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              <ClockIcon style={{ width: 12, display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />
              <LiveTimer startTime={data.cycle_start} running={isRunning} />
            </p>
          </div>
        </div>

        {/* Status */}
        <motion.span
          className="font-mono"
          animate={{
            color: isRunning ? 'var(--blue)' : isComplete ? 'var(--emerald)' : 'var(--text-muted)',
          }}
          style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 1.5,
            padding: '5px 14px', borderRadius: 20,
            background: isRunning ? 'var(--blue-dim)' : isComplete ? 'var(--emerald-glow)' : 'rgba(255,255,255,0.03)',
            border: `1px solid ${isRunning ? 'rgba(59,130,246,0.2)' : isComplete ? 'rgba(16,185,129,0.2)' : 'var(--border)'}`,
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          {isRunning && (
            <motion.span
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
              style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--blue)' }}
            />
          )}
          {isRunning ? 'RUNNING' : isComplete ? 'COMPLETE' : 'IDLE'}
        </motion.span>
      </motion.div>

      {/* ─── Main Pipeline ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        style={{
          flex: 1, minHeight: 280,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '32px 24px', borderRadius: 'var(--radius-lg)',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          position: 'relative', overflow: 'hidden',
        }}
      >
        {/* Atmospheric glow */}
        {isRunning && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
            width: 500, height: 300, borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 70%)',
            pointerEvents: 'none',
          }} />
        )}

        {!connected ? (
          <div style={{ textAlign: 'center' }}>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              style={{
                width: 24, height: 24, border: '2px solid var(--text-ghost)',
                borderTopColor: 'var(--blue)', borderRadius: '50%',
                margin: '0 auto 12px',
              }}
            />
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Reconnecting to agent stream…</p>
          </div>
        ) : (
          <div style={{ width: '100%' }}>
            <AgentPipeline />
          </div>
        )}
      </motion.div>

      {/* ─── Cycle Summary (when complete) ─── */}
      {isComplete && data.agents && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          style={{
            display: 'flex', gap: 14, marginTop: 20,
          }}
        >
          {Object.entries(data.agents).map(([key, agent], i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 + i * 0.08 }}
              style={{
                flex: 1, textAlign: 'center', padding: '14px 8px',
                borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)',
                border: '1px solid var(--border)',
              }}
            >
              <p className="font-mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'capitalize', marginBottom: 4 }}>
                {key}
              </p>
              <p style={{ fontSize: 12, color: agent.status === 'done' ? 'var(--emerald)' : 'var(--rose)' }}>
                {agent.summary || agent.status}
              </p>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
