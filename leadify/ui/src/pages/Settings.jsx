import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { CheckCircleIcon, XCircleIcon, EnvelopeIcon, PaperAirplaneIcon, SparklesIcon } from '@heroicons/react/24/solid';
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
    <div style={{ maxWidth: 720, margin: '0 auto', paddingBottom: 64 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        
        {/* ─── Card 0: ICP Chat Wizard ─── */}
        <ICPWizard />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          {/* ─── Card 1: Gmail Connection ─── */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            style={{
              background: 'var(--bg-card)', boxShadow: 'var(--shadow-sm)',
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
                    fontSize: 12, color: 'var(--rose)', background: 'none', border: 'none', cursor: 'pointer',
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
                    display: 'flex', alignItems: 'center', gap: 8, border: 'none', cursor: 'pointer',
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
            transition={{ delay: 0.2 }}
            style={{
              background: 'var(--bg-card)', boxShadow: 'var(--shadow-sm)',
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
    </div>
  );
}

/* ─── ICP Conversational Wizard ─── */
function ICPWizard() {
  const navigate = useNavigate();
  const scrollRef = useRef(null);

  const [messages, setMessages] = useState([
    { id: 'b0', role: 'bot', text: "👋 Hi! Let's dial in your Target Profile. What kind of company are you looking to target?" }
  ]);
  const [inputVal, setInputVal] = useState('');
  const [step, setStep] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  // Auto-scroll down when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputVal.trim() || isTyping || isComplete) return;

    const userMsg = inputVal.trim();
    setMessages(prev => [...prev, { id: `u${step}`, role: 'user', text: userMsg }]);
    setInputVal('');
    setIsTyping(true);

    // Mock bot logic delay
    setTimeout(() => {
      setIsTyping(false);
      let botResponse = '';
      if (step === 0) {
        botResponse = "Great. What specific role or title should we focus on reaching out to? (e.g. CTO, VP of Sales)";
      } else if (step === 1) {
        botResponse = "Got it. Any specific signals or keywords to prioritize? (e.g. 'recent series A', 'hiring engineers', etc.)";
      } else {
        botResponse = "Perfect! I've updated the Leadify Target Profile. Agents are ready to be dispatched.";
        setIsComplete(true);
      }

      setMessages(prev => [...prev, { id: `b${step + 1}`, role: 'bot', text: botResponse }]);
      setStep(s => s + 1);
    }, 1200);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: 'var(--bg-card)', boxShadow: 'var(--shadow-sm)',
        borderRadius: 'var(--radius-md)', padding: 28,
        display: 'flex', flexDirection: 'column',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <SparklesIcon style={{ width: 22, color: 'var(--violet)' }} />
        <h2 className="font-heading" style={{ fontSize: 18, fontWeight: 700 }}>AI Lead Generation Setup</h2>
        {isComplete && (
          <span style={{ marginLeft: 'auto', background: 'var(--emerald-glow)', color: 'var(--emerald)', padding: '4px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
            Ready
          </span>
        )}
      </div>

      <div 
        ref={scrollRef}
        style={{
          background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)',
          height: 320, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16,
          border: '1px solid var(--border)', marginBottom: 20,
        }}
      >
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ type: 'spring', stiffness: 450, damping: 30 }}
              style={{
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '80%', padding: '12px 16px', borderRadius: 'var(--radius-md)',
                backgroundColor: msg.role === 'user' ? 'var(--blue)' : 'var(--bg-hover)',
                color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
                fontSize: 14, lineHeight: 1.5,
                borderBottomRightRadius: msg.role === 'user' ? 2 : 'var(--radius-md)',
                borderBottomLeftRadius: msg.role === 'bot' ? 2 : 'var(--radius-md)',
              }}
            >
              {msg.text}
            </motion.div>
          ))}
          {isTyping && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              style={{
                alignSelf: 'flex-start', padding: '12px 16px', borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--bg-hover)', borderBottomLeftRadius: 2,
                display: 'flex', gap: 4, alignItems: 'center'
              }}
            >
              <div className="skeleton" style={{ width: 8, height: 8, borderRadius: '50%' }} />
              <div className="skeleton" style={{ width: 8, height: 8, borderRadius: '50%' }} />
              <div className="skeleton" style={{ width: 8, height: 8, borderRadius: '50%' }} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {!isComplete ? (
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 12 }}>
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Type your response..."
            disabled={isTyping}
            style={{
              flex: 1, padding: '14px 16px', borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-surface)', border: '1px solid var(--border)',
              color: 'var(--text-primary)',
            }}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            disabled={!inputVal.trim() || isTyping}
            type="submit"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 48, borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer',
              background: 'var(--blue)', color: 'white',
              opacity: !inputVal.trim() || isTyping ? 0.5 : 1,
            }}
          >
            <PaperAirplaneIcon style={{ width: 18 }} />
          </motion.button>
        </form>
      ) : (
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => navigate('/live')}
          style={{
            padding: '16px 20px', borderRadius: 'var(--radius-md)',
            background: 'var(--emerald)', color: 'white', border: 'none', cursor: 'pointer',
            fontSize: 15, fontWeight: 700, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8,
            boxShadow: '0 4px 20px rgba(16,185,129,0.3)',
          }}
        >
          <SparklesIcon style={{ width: 18 }} />
          Start Generating Leads
        </motion.button>
      )}
    </motion.div>
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
              flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
              borderRadius: 'var(--radius-sm)',
              fontSize: 14, fontWeight: 600,
              background: selected === opt ? 'var(--blue)' : 'var(--bg-elevated)',
              color: selected === opt ? 'white' : 'var(--text-secondary)',
              boxShadow: selected === opt ? 'none' : 'inset 0 0 0 1px var(--border)',
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
          width: '100%', padding: '11px 0', cursor: 'pointer',
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
