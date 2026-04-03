import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckIcon, PencilIcon, XMarkIcon } from '@heroicons/react/20/solid';
import { useQueue } from '../hooks/useQueue';
import { approveDraft, skipDraft, editDraft } from '../lib/api';
import ScoreBadge from '../components/ScoreBadge';
import DeltaBadge from '../components/DeltaBadge';

/* ─── Count-up number ─── */
function CountUp({ to, duration = 0.8 }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (to === 0) { setVal(0); return; }
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / (duration * 1000), 1);
      setVal(Math.round(p * to));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [to, duration]);
  return <>{val}</>;
}

/* ─── Signal Chip ─── */
function SignalChip({ signal }) {
  if (!signal) return null;
  const icons = { funding_signal: '🔭', replied: '📧', email_opened: '📧', link_clicked: '🔗', job_change: '🏢' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 11, fontWeight: 500, padding: '2px 10px', borderRadius: 20,
      background: 'var(--blue-dim)', border: '1px solid rgba(59,130,246,0.15)',
      color: 'var(--text-secondary)',
    }}>
      {icons[signal] || '📌'} {signal.replace(/_/g, ' ')}
    </span>
  );
}

export default function Queue() {
  const { queue, stats } = useQueue();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState(null);
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');

  const sendMutation = useMutation({
    mutationFn: approveDraft,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queue'] }),
  });

  const skipMutation = useMutation({
    mutationFn: skipDraft,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queue'] }),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, data }) => editDraft(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      setEditingId(null);
    },
  });

  const drafts = (queue.data || [])
    .filter(d => d?.draft)
    .sort((a, b) => (b.draft.score_at_draft || 0) - (a.draft.score_at_draft || 0));

  const st = stats.data || {};

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* ─── Stat Cards ─── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{ display: 'flex', gap: 14, marginBottom: 32 }}
      >
        {[
          { label: 'Pending Review', value: st.pending || drafts.length, color: 'var(--blue)' },
          { label: 'Sent Today', value: st.sent_today || 0, color: 'var(--emerald)' },
          { label: 'Skipped Today', value: st.skipped_today || 0, color: 'var(--rose)' },
        ].map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            style={{
              flex: 1, padding: '18px 20px', borderRadius: 'var(--radius-md)',
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              position: 'relative', overflow: 'hidden',
            }}
          >
            {/* Gradient accent */}
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: 2,
              background: `linear-gradient(90deg, transparent, ${card.color}, transparent)`,
              opacity: 0.4,
            }} />
            <p style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1.2, fontWeight: 600, marginBottom: 6 }}>
              {card.label}
            </p>
            <p className="font-mono" style={{ fontSize: 32, fontWeight: 700, color: card.color, lineHeight: 1 }}>
              <CountUp to={card.value} />
            </p>
          </motion.div>
        ))}
      </motion.div>

      {/* ─── Draft Cards ─── */}
      {queue.isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 140 }} />
          ))}
        </div>
      ) : drafts.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            textAlign: 'center', padding: '64px 20px',
            borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)',
            background: 'var(--bg-card)',
          }}
        >
          {/* Sleeping robot SVG */}
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none" style={{ margin: '0 auto 16px', opacity: 0.4 }}>
            <rect x="16" y="24" width="48" height="36" rx="8" stroke="var(--text-muted)" strokeWidth="2" />
            <circle cx="32" cy="40" r="4" fill="var(--text-ghost)" />
            <circle cx="48" cy="40" r="4" fill="var(--text-ghost)" />
            <path d="M32 50 Q40 54 48 50" stroke="var(--text-ghost)" strokeWidth="2" fill="none" />
            <path d="M24 24 L24 18 M56 24 L56 18" stroke="var(--text-muted)" strokeWidth="2" />
            <text x="54" y="16" fontSize="10" fill="var(--text-ghost)">z</text>
            <text x="60" y="12" fontSize="8" fill="var(--text-ghost)">z</text>
            <text x="64" y="8" fontSize="6" fill="var(--text-ghost)">z</text>
          </svg>
          <p className="font-heading" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
            No drafts pending review
          </p>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Agents will generate new drafts at the next cycle.
          </p>
        </motion.div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <AnimatePresence mode="popLayout">
            {drafts.map((obj, idx) => {
              const d = obj.draft;
              const isEditing = editingId === d.id;

              return (
                <motion.div
                  key={d.id}
                  layout="position"
                  initial={{ opacity: 0, y: 20, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                  transition={{ delay: idx * 0.04, type: 'spring', stiffness: 400, damping: 30 }}
                  whileHover={{ y: -2, boxShadow: 'var(--shadow-lg)' }}
                  style={{
                    background: 'var(--bg-card)', boxShadow: 'var(--shadow-sm)',
                    borderRadius: 'var(--radius-md)', padding: '24px 28px',
                    position: 'relative', overflow: 'hidden',
                  }}
                >
                  {/* Top Row: Name + Score */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span className="font-heading" style={{ fontSize: 17, fontWeight: 700 }}>
                          {obj.lead?.name || 'Unknown Lead'}
                        </span>
                        <SignalChip signal={d.trigger_signal} />
                      </div>
                      <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{obj.lead?.company || ''}</p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                      <DeltaBadge delta={d.score_delta || obj.delta} />
                      <ScoreBadge score={d.score_at_draft || obj.lead?.score || 0} />
                    </div>
                  </div>

                  {/* Subject + Body */}
                  {isEditing ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
                      <input
                        value={editSubject}
                        onChange={(e) => setEditSubject(e.target.value)}
                        style={{ fontSize: 14, fontWeight: 600, padding: '10px 12px' }}
                      />
                      <textarea
                        value={editBody}
                        onChange={(e) => setEditBody(e.target.value)}
                        rows={6}
                        style={{ fontSize: 13, lineHeight: 1.7, resize: 'vertical', padding: '10px 12px' }}
                      />
                    </div>
                  ) : (
                    <>
                      <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>
                        {d.subject}
                      </p>
                      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap', marginBottom: 14 }}>
                        {d.body}
                      </p>
                    </>
                  )}

                  {/* Actions */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                    {isEditing ? (
                      <>
                        <Btn
                          variant="ghost"
                          onClick={() => setEditingId(null)}
                          icon={<XMarkIcon style={{ width: 14 }} />}
                          label="Cancel"
                        />
                        <Btn
                          variant="primary"
                          loading={editMutation.isPending}
                          onClick={() => editMutation.mutate({ id: d.id, data: { subject: editSubject, body: editBody } })}
                          icon={<CheckIcon style={{ width: 14 }} />}
                          label="Save & Send"
                        />
                      </>
                    ) : (
                      <>
                        <Btn
                          variant="danger-ghost"
                          onClick={() => skipMutation.mutate(d.id)}
                          icon={<XMarkIcon style={{ width: 14 }} />}
                          label="Skip"
                        />
                        <Btn
                          variant="outline"
                          onClick={() => { setEditingId(d.id); setEditSubject(d.subject); setEditBody(d.body); }}
                          icon={<PencilIcon style={{ width: 14 }} />}
                          label="Edit"
                        />
                        <Btn
                          variant="primary"
                          loading={sendMutation.isPending}
                          onClick={() => sendMutation.mutate(d.id)}
                          icon={<CheckIcon style={{ width: 14 }} />}
                          label="Send"
                        />
                      </>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

/* ─── Button Micro-Component ─── */
function Btn({ variant = 'primary', onClick, icon, label, loading = false }) {
  const styles = {
    primary: {
      background: 'var(--blue)', color: 'white',
      border: 'none',
    },
    outline: {
      background: 'transparent', color: 'var(--text-secondary)',
      border: '1px solid var(--border)',
    },
    'danger-ghost': {
      background: 'transparent', color: 'var(--text-muted)',
      border: '1px solid transparent',
    },
    ghost: {
      background: 'transparent', color: 'var(--text-muted)',
      border: 'none',
    },
  };

  return (
    <motion.button
      whileHover={{
        scale: 1.03,
        ...(variant === 'danger-ghost' ? { color: 'var(--rose)', borderColor: 'var(--rose)' } : {}),
        ...(variant === 'primary' ? { boxShadow: '0 0 16px rgba(59,130,246,0.3)' } : {}),
      }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      disabled={loading}
      style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '7px 14px', borderRadius: 'var(--radius-sm)',
        fontSize: 12, fontWeight: 600, cursor: 'pointer',
        transition: 'all 0.2s',
        ...styles[variant],
        opacity: loading ? 0.6 : 1,
      }}
    >
      {loading ? (
        <motion.span
          animate={{ rotate: 360 }}
          transition={{ duration: 0.6, repeat: Infinity, ease: 'linear' }}
          style={{ width: 12, height: 12, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block' }}
        />
      ) : icon}
      {label}
    </motion.button>
  );
}
