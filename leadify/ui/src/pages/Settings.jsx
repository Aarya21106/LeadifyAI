import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { CheckCircleIcon, XCircleIcon, EnvelopeIcon } from '@heroicons/react/24/solid';
import { getGmailStatus, getGmailAuthUrl, disconnectGmail } from '../lib/api';

export default function Settings() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();

  // Check for gmail=connected in query string (after OAuth redirect)
  useEffect(() => {
    if (searchParams.get('gmail') === 'connected') {
      queryClient.invalidateQueries({ queryKey: ['gmail-status'] });
    }
  }, [searchParams, queryClient]);

  const { data: gmail, isLoading: gmailLoading } = useQuery({
    queryKey: ['gmail-status'],
    queryFn: getGmailStatus,
    retry: false,
    placeholderData: { connected: false },
  });

  const connectMutation = useMutation({
    mutationFn: async () => {
      const data = await getGmailAuthUrl();
      window.location.href = data.auth_url;
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: disconnectGmail,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['gmail-status'] }),
  });

  const gmailConnected = gmail?.connected;

  return (
    <div style={{ maxWidth: 640, margin: '0 auto' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* ─── Card 1: Gmail Connection ─── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', padding: 28,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
            <EnvelopeIcon style={{ width: 22, color: gmailConnected ? 'var(--emerald)' : 'var(--rose)' }} />
            <h2 className="font-heading" style={{ fontSize: 18, fontWeight: 700 }}>Gmail Connection</h2>
          </div>

          {gmailLoading ? (
            <div className="skeleton" style={{ height: 60 }} />
          ) : gmailConnected ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                >
                  <CheckCircleIcon style={{ width: 28, color: 'var(--emerald)' }} />
                </motion.div>
                <div>
                  <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--emerald)' }}>Connected</p>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                    {gmail.email || 'Gmail account'}
                  </p>
                </div>
              </div>

              {gmail.last_sync && (
                <p className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 16 }}>
                  Last sync: {new Date(gmail.last_sync).toLocaleString()}
                </p>
              )}

              <button
                onClick={() => disconnectMutation.mutate()}
                disabled={disconnectMutation.isPending}
                style={{
                  fontSize: 12, color: 'var(--rose)', background: 'none',
                  textDecoration: 'underline', textUnderlineOffset: 3,
                  opacity: disconnectMutation.isPending ? 0.5 : 0.7,
                }}
              >
                {disconnectMutation.isPending ? 'Disconnecting…' : 'Disconnect Gmail'}
              </button>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <XCircleIcon style={{ width: 28, color: 'var(--rose)' }} />
                <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                  Connect your Gmail to start monitoring leads
                </p>
              </div>

              <motion.button
                whileHover={{ scale: 1.03, boxShadow: '0 0 20px rgba(59,130,246,0.3)' }}
                whileTap={{ scale: 0.97 }}
                onClick={() => connectMutation.mutate()}
                disabled={connectMutation.isPending}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '11px 24px', borderRadius: 'var(--radius-sm)',
                  background: 'var(--blue)', color: 'white',
                  fontSize: 14, fontWeight: 600,
                  opacity: connectMutation.isPending ? 0.6 : 1,
                }}
              >
                {connectMutation.isPending ? (
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                    style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block' }}
                  />
                ) : (
                  <EnvelopeIcon style={{ width: 16 }} />
                )}
                Connect Gmail
              </motion.button>
            </div>
          )}
        </motion.div>

        {/* ─── Card 2: Cycle Settings ─── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', padding: 28,
          }}
        >
          <h2 className="font-heading" style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>
            Cycle Settings
          </h2>

          <CycleIntervalSlider />
        </motion.div>
      </div>
    </div>
  );
}

/* ─── Cycle Interval Slider ─── */
function CycleIntervalSlider() {
  const options = [30, 60, 120, 240];
  const [selected, setSelected] = useState(60);

  return (
    <div>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
        Run agents every <span className="font-mono" style={{ color: 'var(--blue)', fontWeight: 700 }}>{selected}</span> minutes
      </p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {options.map(opt => (
          <motion.button
            key={opt}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setSelected(opt)}
            className="font-mono"
            style={{
              flex: 1, padding: '10px 0',
              borderRadius: 'var(--radius-sm)',
              fontSize: 14, fontWeight: 600,
              background: selected === opt ? 'var(--blue)' : 'var(--bg-elevated)',
              color: selected === opt ? 'white' : 'var(--text-secondary)',
              border: selected === opt ? 'none' : '1px solid var(--border)',
              transition: 'all 0.2s',
            }}
          >
            {opt}m
          </motion.button>
        ))}
      </div>

      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        style={{
          width: '100%', padding: '11px 0',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--blue-dim)', color: 'var(--blue)',
          border: '1px solid rgba(59,130,246,0.2)',
          fontSize: 13, fontWeight: 600,
        }}
      >
        Save Settings
      </motion.button>
    </div>
  );
}
