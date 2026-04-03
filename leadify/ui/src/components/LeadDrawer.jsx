import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';
import { useLead, useLeadHistory } from '../hooks/useLeads';
import { updateLead } from '../lib/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import ScoreBadge from './ScoreBadge';
import DeltaBadge from './DeltaBadge';

const eventIcons = {
  opened: '📧',
  replied: '💬',
  signal_detected: '🔭',
  bounced: '⚠️',
  out_of_office: '📅',
};

const statusColors = {
  active: 'var(--emerald)',
  paused: 'var(--amber)',
  converted: 'var(--blue)',
  dead: 'var(--text-muted)',
};

function getEventDescription(ev) {
  const data = ev.raw_data || {};
  if (ev.event_type === 'opened') return data.snippet || 'Email opened';
  if (ev.event_type === 'replied') return data.snippet || 'Lead replied';
  if (ev.event_type === 'signal_detected') return data.summary || `${data.signal_type || 'Signal'} detected`;
  if (ev.event_type === 'bounced') return 'Email bounced';
  if (ev.event_type === 'out_of_office') return data.snippet || 'Out of office';
  return ev.event_type;
}

export default function LeadDrawer({ leadId, onClose }) {
  const { data: lead, isLoading: leadLoading } = useLead(leadId);
  const { data: history, isLoading: historyLoading } = useLeadHistory(leadId);
  const queryClient = useQueryClient();

  const pauseMutation = useMutation({
    mutationFn: () => updateLead(leadId, { status: 'paused' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] });
    },
  });

  const convertMutation = useMutation({
    mutationFn: () => updateLead(leadId, { status: 'converted' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] });
    },
  });

  const activateMutation = useMutation({
    mutationFn: () => updateLead(leadId, { status: 'active' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] });
    },
  });

  const scoreHistory = (history?.scores || [])
    .slice()
    .reverse()
    .map((s, i) => ({ idx: i + 1, score: s.score }));
  const events = history?.events || [];
  const drafts = history?.drafts || [];

  const currentScore = lead?.latest_score?.score ?? 0;
  const currentDelta = lead?.latest_score?.delta ?? 0;
  const reasoning = lead?.latest_score?.reasoning ?? null;

  return (
    <AnimatePresence>
      {leadId && (
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
            initial={{ x: '100%', boxShadow: '0 0 0 rgba(0,0,0,0)' }}
            animate={{ x: 0, boxShadow: '-10px 0 30px rgba(0,0,0,0.1)' }}
            exit={{ x: '100%', boxShadow: '0 0 0 rgba(0,0,0,0)' }}
            transition={{ type: 'spring', stiffness: 400, damping: 35 }}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0, width: 520,
              background: 'var(--bg-surface)', boxShadow: 'var(--shadow-drawer)',
              zIndex: 101, overflowY: 'auto', padding: 32,
              display: 'flex', flexDirection: 'column', gap: 20,
            }}
          >
            {leadLoading ? (
              <div style={{ padding: 20 }}>
                <div className="skeleton" style={{ height: 30, width: '60%', marginBottom: 10 }} />
                <div className="skeleton" style={{ height: 16, width: '40%' }} />
              </div>
            ) : lead ? (
              <>
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h2 className="font-heading" style={{ fontSize: 22, fontWeight: 700 }}>
                      {lead.name || 'Unknown'}
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4 }}>
                      {lead.company || 'Unknown Company'}
                    </p>
                    <p className="font-mono" style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      {lead.email}
                    </p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <ScoreBadge score={currentScore} size={48} />
                    <button onClick={onClose} style={{ color: 'var(--text-muted)' }}>
                      <XMarkIcon style={{ width: 22 }} />
                    </button>
                  </div>
                </div>

                {/* Status + Delta */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span className="font-mono" style={{
                    fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                    padding: '4px 12px', borderRadius: 20,
                    color: statusColors[lead.status] || 'var(--text-muted)',
                    background: lead.status === 'active' ? 'var(--emerald-glow)' :
                                lead.status === 'converted' ? 'var(--blue-dim)' : 'var(--bg-hover)',
                    border: `1px solid ${statusColors[lead.status] || 'var(--border)'}33`,
                  }}>
                    {lead.status}
                  </span>
                  <DeltaBadge delta={currentDelta} />
                  {lead.first_email_sent_at && (
                    <span className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      First email: {new Date(lead.first_email_sent_at).toLocaleDateString()}
                    </span>
                  )}
                </div>

                {/* Score Reasoning */}
                {reasoning && (
                  <div style={{
                    padding: '16px 20px', borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-void)',
                  }}>
                    <p className="font-mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
                      AI Score Reasoning
                    </p>
                    <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                      {reasoning}
                    </p>
                  </div>
                )}

                {/* Score Sparkline */}
                {scoreHistory.length > 1 && (
                  <div>
                    <p className="font-mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                      Score History ({scoreHistory.length} cycles)
                    </p>
                    <div style={{ height: 80, borderRadius: 'var(--radius-md)', overflow: 'hidden', background: 'var(--bg-void)' }}>
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
                  <p className="font-mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                    Event Timeline ({events.length})
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {events.length === 0 && (
                      <p style={{ fontSize: 13, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        No events recorded yet. Run agents to detect activity.
                      </p>
                    )}
                    {events.map((ev, i) => (
                      <motion.div
                        key={ev.id || i}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.04 }}
                        style={{
                          display: 'flex', alignItems: 'flex-start', gap: 12,
                          padding: '14px 16px', borderRadius: 'var(--radius-md)',
                          background: 'var(--bg-card)', boxShadow: 'var(--shadow-sm)',
                        }}
                      >
                        <span style={{ fontSize: 16, flexShrink: 0 }}>
                          {eventIcons[ev.event_type] || '📌'}
                        </span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontSize: 13, fontWeight: 500 }}>{getEventDescription(ev)}</p>
                          <div style={{ display: 'flex', gap: 8, marginTop: 3 }}>
                            <span className="font-mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                              {ev.event_type.replace(/_/g, ' ')}
                            </span>
                            <span className="font-mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                              {ev.detected_at ? new Date(ev.detected_at).toLocaleString() : ''}
                            </span>
                          </div>
                          {/* Show classification if available */}
                          {ev.raw_data?.classification && (
                            <span style={{
                              display: 'inline-block', marginTop: 4,
                              fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                              padding: '2px 8px', borderRadius: 10,
                              background: ev.raw_data.classification === 'interested' ? 'var(--emerald-glow)' :
                                          ev.raw_data.classification === 'warm' ? 'var(--amber-glow)' : 'var(--bg-hover)',
                              color: ev.raw_data.classification === 'interested' ? 'var(--emerald)' :
                                     ev.raw_data.classification === 'warm' ? 'var(--amber)' : 'var(--text-muted)',
                            }}>
                              {ev.raw_data.classification}
                            </span>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>

                {/* Past Drafts */}
                {drafts.length > 0 && (
                  <div>
                    <p className="font-mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                      Email Drafts ({drafts.length})
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {drafts.map((d, i) => (
                        <details key={d.id || i} style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '10px 12px' }}>
                          <summary style={{ cursor: 'pointer', fontSize: 13, fontWeight: 500, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>{d.subject || `Draft #${i + 1}`}</span>
                            <span className="font-mono" style={{
                              fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
                              padding: '2px 8px', borderRadius: 10, marginLeft: 8,
                              color: d.status === 'sent' ? 'var(--emerald)' :
                                     d.status === 'approved' ? 'var(--blue)' :
                                     d.status === 'revision_needed' ? 'var(--amber)' : 'var(--text-secondary)',
                              background: d.status === 'sent' ? 'var(--emerald-glow)' :
                                          d.status === 'approved' ? 'var(--blue-dim)' :
                                          d.status === 'revision_needed' ? 'var(--amber-glow)' : 'var(--bg-hover)',
                            }}>
                              {d.status?.replace(/_/g, ' ')}
                            </span>
                          </summary>
                          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                            {d.body}
                          </p>
                          {d.reviewer_feedback && (
                            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8, fontStyle: 'italic', borderTop: '1px solid var(--border)', paddingTop: 8 }}>
                              Reviewer: {d.reviewer_feedback}
                            </p>
                          )}
                        </details>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', gap: 8, marginTop: 'auto', paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                  {lead.status === 'active' ? (
                    <>
                      <motion.button
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => pauseMutation.mutate()}
                        disabled={pauseMutation.isPending}
                        style={{
                          flex: 1, padding: '10px 0', borderRadius: 'var(--radius-sm)',
                          background: 'var(--amber-glow)', color: 'var(--amber)',
                          fontSize: 13, fontWeight: 600, border: '1px solid rgba(245,158,11,0.2)',
                        }}
                      >
                        {pauseMutation.isPending ? 'Pausing…' : '⏸ Pause'}
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => convertMutation.mutate()}
                        disabled={convertMutation.isPending}
                        style={{
                          flex: 1, padding: '10px 0', borderRadius: 'var(--radius-sm)',
                          background: 'var(--emerald-glow)', color: 'var(--emerald)',
                          fontSize: 13, fontWeight: 600, border: '1px solid rgba(16,185,129,0.2)',
                        }}
                      >
                        {convertMutation.isPending ? 'Converting…' : '✅ Mark Converted'}
                      </motion.button>
                    </>
                  ) : (
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => activateMutation.mutate()}
                      disabled={activateMutation.isPending}
                      style={{
                        flex: 1, padding: '10px 0', borderRadius: 'var(--radius-sm)',
                        background: 'var(--blue-dim)', color: 'var(--blue)',
                        fontSize: 13, fontWeight: 600, border: '1px solid rgba(59,130,246,0.2)',
                      }}
                    >
                      {activateMutation.isPending ? 'Activating…' : '▶ Reactivate'}
                    </motion.button>
                  )}
                </div>
              </>
            ) : (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>
                Lead not found
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
