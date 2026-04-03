import { motion } from 'framer-motion';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/20/solid';

export default function DeltaBadge({ delta = 0 }) {
  if (delta === 0 || delta == null) return null;
  const positive = delta > 0;
  const isHot = Math.abs(delta) > 20;

  return (
    <motion.span
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 2,
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        fontWeight: 600,
        padding: '2px 8px',
        borderRadius: 20,
        color: positive ? 'var(--emerald)' : 'var(--rose)',
        background: positive ? 'var(--emerald-glow)' : 'var(--rose-glow)',
        animation: isHot ? 'glow-breathe 2s ease-in-out infinite' : 'none',
        '--blue-glow': positive ? 'var(--emerald-glow)' : 'var(--rose-glow)',
      }}
    >
      {positive
        ? <ArrowUpIcon style={{ width: 12, height: 12 }} />
        : <ArrowDownIcon style={{ width: 12, height: 12 }} />
      }
      {positive ? '+' : ''}{delta}
    </motion.span>
  );
}
