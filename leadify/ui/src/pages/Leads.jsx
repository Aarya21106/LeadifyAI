import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLeads } from '../hooks/useLeads';
import { createLead } from '../lib/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusIcon, MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/20/solid';
import ScoreBadge from '../components/ScoreBadge';
import DeltaBadge from '../components/DeltaBadge';
import LeadDrawer from '../components/LeadDrawer';

const STATUS_OPTIONS = ['all', 'active', 'paused', 'converted', 'dead'];
const COLUMNS = [
  { key: 'name',       label: 'Name',       sortable: true },
  { key: 'company',    label: 'Company',    sortable: true },
  { key: 'score',      label: 'Score',      sortable: true },
  { key: 'delta',      label: 'Delta',      sortable: true },
  { key: 'status',     label: 'Status',     sortable: true },
  { key: 'last_event', label: 'Last Event', sortable: false },
];

/* ─── Event type formatting ─── */
const eventTypeLabels = {
  opened: '📧 Opened',
  replied: '💬 Replied',
  signal_detected: '🔭 Signal',
  bounced: '⚠️ Bounced',
  out_of_office: '📅 OOO',
};

function getLastEventSummary(events) {
  if (!events || events.length === 0) return '—';
  const ev = events[0];
  const label = eventTypeLabels[ev.event_type] || ev.event_type;
  const snippet = ev.raw_data?.snippet || ev.raw_data?.summary || '';
  if (snippet) return `${label}: ${snippet.slice(0, 40)}…`;
  return label;
}

export default function Leads() {
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('score');
  const [sortDir, setSortDir] = useState('desc');
  const [selectedLeadId, setSelectedLeadId] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);

  const queryClient = useQueryClient();
  const { data: rawLeads, isLoading } = useLeads(statusFilter === 'all' ? undefined : statusFilter);

  const leads = useMemo(() => {
    let list = (rawLeads || []).map(lead => ({
      ...lead,
      score: lead.latest_score?.score ?? 0,
      delta: lead.latest_score?.delta ?? 0,
      reasoning: lead.latest_score?.reasoning ?? null,
      last_event_summary: getLastEventSummary(lead.recent_events),
    }));

    // Filter by search
    list = list.filter(l => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (l.name || '').toLowerCase().includes(q) ||
             (l.company || '').toLowerCase().includes(q) ||
             (l.email || '').toLowerCase().includes(q);
    });

    // Sort
    list.sort((a, b) => {
      let aVal = a[sortKey], bVal = b[sortKey];
      if (sortKey === 'name' || sortKey === 'company' || sortKey === 'status') {
        aVal = (aVal || '').toLowerCase();
        bVal = (bVal || '').toLowerCase();
        return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDir === 'asc' ? (aVal || 0) - (bVal || 0) : (bVal || 0) - (aVal || 0);
    });

    return list;
  }, [rawLeads, search, sortKey, sortDir]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  // Summary stats
  const totalLeads = leads.length;
  const avgScore = totalLeads > 0 ? Math.round(leads.reduce((s, l) => s + l.score, 0) / totalLeads) : 0;
  const highPriority = leads.filter(l => l.delta > 20).length;
  const withEvents = leads.filter(l => l.last_event_summary !== '—').length;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* ─── Summary Stats ─── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', gap: 12, marginBottom: 20 }}
      >
        {[
          { label: 'Total Leads', value: totalLeads, color: 'var(--blue)' },
          { label: 'Avg Score', value: avgScore, color: 'var(--emerald)' },
          { label: 'High Priority', value: highPriority, color: 'var(--amber)' },
          { label: 'With Events', value: withEvents, color: 'var(--violet, #8b5cf6)' },
        ].map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            style={{
              flex: 1, padding: '16px 20px', borderRadius: 'var(--radius-md)',
              background: 'var(--bg-card)', boxShadow: 'var(--shadow-sm)',
              position: 'relative', overflow: 'hidden',
            }}
          >
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: 2,
              background: `linear-gradient(90deg, transparent, ${card.color}, transparent)`,
              opacity: 0.4,
            }} />
            <p style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1.2, fontWeight: 600 }}>
              {card.label}
            </p>
            <p className="font-mono" style={{ fontSize: 26, fontWeight: 700, color: card.color, lineHeight: 1, marginTop: 4 }}>
              {card.value}
            </p>
          </motion.div>
        ))}
      </motion.div>

      {/* ─── Filter Bar ─── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        style={{
          display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap',
        }}
      >
        <div style={{ position: 'relative', flex: 1, maxWidth: 320 }}>
          <MagnifyingGlassIcon style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', width: 16, color: 'var(--text-muted)' }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search leads…"
            style={{ width: '100%', paddingLeft: 32, height: 38, fontSize: 13 }}
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ height: 38, fontSize: 13, paddingRight: 28, textTransform: 'capitalize' }}
        >
          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </motion.div>

      {/* ─── Table ─── */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        style={{
          borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-sm)',
          overflow: 'hidden', background: 'var(--bg-card)',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1.5fr 80px 80px 100px 2fr',
          padding: '14px 24px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-surface)',
        }}>
          {COLUMNS.map(col => (
            <div
              key={col.key}
              onClick={col.sortable ? () => toggleSort(col.key) : undefined}
              style={{
                fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: 1.2, color: 'var(--text-muted)',
                cursor: col.sortable ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', gap: 4,
                userSelect: 'none',
              }}
            >
              {col.label}
              {col.sortable && sortKey === col.key && (
                <span style={{ fontSize: 8 }}>{sortDir === 'asc' ? '▲' : '▼'}</span>
              )}
            </div>
          ))}
        </div>

        {/* Rows */}
        {isLoading ? (
          <div style={{ padding: 20 }}>
            {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 42, marginBottom: 6 }} />)}
          </div>
        ) : leads.length === 0 ? (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            No leads found. Run agents to generate leads.
          </div>
        ) : (
          leads.map((lead, idx) => (
            <motion.div
              layout
              key={lead.id || idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: 'spring', delay: Math.min(idx * 0.03, 0.5), stiffness: 300, damping: 24 }}
              onClick={() => setSelectedLeadId(lead.id)}
              style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1.5fr 80px 80px 100px 2fr',
                padding: '16px 24px', borderBottom: '1px solid var(--border)',
                cursor: 'pointer', alignItems: 'center',
                transition: 'all 0.15s',
              }}
              whileHover={{
                background: 'var(--bg-hover)',
                borderLeft: '3px solid var(--blue)',
                paddingLeft: '17px',
              }}
            >
              <div>
                <span style={{ fontSize: 14, fontWeight: 600 }}>{lead.name || 'Unknown'}</span>
                <p className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>{lead.email}</p>
              </div>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{lead.company || '—'}</span>
              <ScoreBadge score={lead.score} size={32} />
              <DeltaBadge delta={lead.delta} />
              <span className="font-mono" style={{
                fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                padding: '3px 8px', borderRadius: 12,
                color: lead.status === 'active' ? 'var(--emerald)' :
                       lead.status === 'converted' ? 'var(--blue)' :
                       lead.status === 'paused' ? 'var(--amber)' : 'var(--text-muted)',
                background: lead.status === 'active' ? 'var(--emerald-glow)' :
                            lead.status === 'converted' ? 'var(--blue-dim)' :
                            lead.status === 'paused' ? 'var(--amber-glow)' : 'var(--bg-hover)',
              }}>
                {lead.status || '—'}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {lead.last_event_summary}
              </span>
            </motion.div>
          ))
        )}
      </motion.div>

      {/* ─── Floating Add Button ─── */}
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setShowAddModal(true)}
        style={{
          position: 'fixed', bottom: 28, right: 28,
          width: 52, height: 52, borderRadius: '50%',
          background: 'var(--blue)', color: 'white',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 24px rgba(59,130,246,0.4)',
          zIndex: 50,
        }}
      >
        <PlusIcon style={{ width: 24 }} />
      </motion.button>

      {/* ─── Lead Drawer ─── */}
      <LeadDrawer leadId={selectedLeadId} onClose={() => setSelectedLeadId(null)} />

      {/* ─── Add Lead Modal ─── */}
      <AnimatePresence>
        {showAddModal && <AddLeadModal onClose={() => setShowAddModal(false)} />}
      </AnimatePresence>
    </div>
  );
}

/* ─── Add Lead Modal ─── */
function AddLeadModal({ onClose }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => createLead({ name, email, company }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      onClose();
    },
  });

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)', zIndex: 100 }}
      />
      <motion.div
        initial={{ y: '100%', opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: '100%', opacity: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        style={{
          position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)',
          width: '100%', maxWidth: 480, padding: 32,
          background: 'var(--bg-surface)', boxShadow: '0 -10px 40px rgba(0,0,0,0.1)',
          borderRadius: 'var(--radius-xl) var(--radius-xl) 0 0',
          zIndex: 101,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 className="font-heading" style={{ fontSize: 18, fontWeight: 700 }}>Add Lead</h3>
          <button onClick={onClose}><XMarkIcon style={{ width: 20, color: 'var(--text-muted)' }} /></button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input placeholder="Name" value={name} onChange={e => setName(e.target.value)} />
          <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input placeholder="Company" value={company} onChange={e => setCompany(e.target.value)} />

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !name || !email}
            style={{
              padding: '12px 0', borderRadius: 'var(--radius-sm)',
              background: 'var(--blue)', color: 'white',
              fontSize: 14, fontWeight: 600, marginTop: 4,
              opacity: mutation.isPending ? 0.6 : 1,
            }}
          >
            {mutation.isPending ? 'Adding…' : 'Add Lead'}
          </motion.button>
        </div>
      </motion.div>
    </>
  );
}
