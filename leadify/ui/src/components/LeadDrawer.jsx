import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon, ClockIcon } from '@heroicons/react/24/outline';
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';
import ScoreBadge from './ScoreBadge';

const eventIcons = {
  email_opened: '📧',
  replied: '💬',
  funding_signal: '🔭',
  job_change: '🏢',
  link_clicked: '🔗',
  bounced: '⚠️',
};

export default function LeadDrawer({ lead, onClose }) {
  if (!lead) return null;

  const scoreHistory = (lead.score_history || []).map((s, i) => ({
    idx: i,
    score: s.score ?? s,
  }));

  const events = lead.events || [];
  const drafts = lead.past_drafts || [];

  return (
    <AnimatePresence>
      {lead && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
              zIndex: 100, backdropFilter: 'blur(4px)',
            }}
          />

          {/* Drawer */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0, width: 480,
              background: 'var(--bg-surface)', borderLeft: '1px solid var(--border)',
              zIndex: 101, overflowY: 'auto', padding: 28,
              display: 'flex', flexDirection: 'column', gap: 24,
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h2 className="font-heading" style={{ fontSize: 22, fontWeight: 700 }}>
                  {lead.name}
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4 }}>
                  {lead.company || 'Unknown Company'}
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <ScoreBadge score={lead.score || 0} size={48} />
                <button onClick={onClose} style={{ color: 'var(--text-muted)' }}>
                  <XMarkIcon style={{ width: 22 }} />
                </button>
              </div>
            </div>

            {/* Score Sparkline */}
            {scoreHistory.length > 1 && (
              <div>
                <p className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                  Score History
                </p>
                <div style={{ height: 80, borderRadius: 'var(--radius-md)', overflow: 'hidden', background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={scoreHistory}>
                      <defs>
                        <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--blue)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="var(--blue)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Tooltip
                        contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, fontFamily: 'var(--font-mono)' }}
                        labelStyle={{ display: 'none' }}
                      />
                      <Area type="monotone" dataKey="score" stroke="var(--blue)" fill="url(#scoreGrad)" strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Event Timeline */}
            <div>
              <p className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                Event Timeline
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {events.length === 0 && (
                  <p style={{ fontSize: 13, color: 'var(--text-muted)', fontStyle: 'italic' }}>No events recorded yet.</p>
                )}
                {events.map((ev, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    style={{
                      display: 'flex', alignItems: 'flex-start', gap: 10,
                      padding: '10px 12px', borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-card)', border: '1px solid var(--border)',
                    }}
                  >
                    <span style={{ fontSize: 16, flexShrink: 0 }}>
                      {eventIcons[ev.event_type] || '📌'}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 13, fontWeight: 500 }}>{ev.summary || ev.event_type}</p>
                      <p className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                        {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Past Drafts */}
            {drafts.length > 0 && (
              <div>
                <p className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                  Past Drafts ({drafts.length})
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {drafts.map((d, i) => (
                    <details key={i} style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '10px 12px' }}>
                      <summary style={{ cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
                        {d.subject || `Draft #${i + 1}`}
                      </summary>
                      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                        {d.body}
                      </p>
                    </details>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 8, marginTop: 'auto', paddingTop: 16, borderTop: '1px solid var(--border)' }}>
              <button style={{
                flex: 1, padding: '10px 0', borderRadius: 'var(--radius-sm)',
                background: 'var(--amber-glow)', color: 'var(--amber)',
                fontSize: 13, fontWeight: 600,
              }}>
                Pause
              </button>
              <button style={{
                flex: 1, padding: '10px 0', borderRadius: 'var(--radius-sm)',
                background: 'var(--emerald-glow)', color: 'var(--emerald)',
                fontSize: 13, fontWeight: 600,
              }}>
                Mark Converted
              </button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
