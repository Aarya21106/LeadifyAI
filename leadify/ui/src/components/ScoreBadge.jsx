import { motion } from 'framer-motion';

const colorMap = {
  hot:    { bg: 'rgba(16,185,129,0.15)', border: 'rgba(16,185,129,0.4)', text: '#34d399' },
  warm:   { bg: 'rgba(245,158,11,0.15)',  border: 'rgba(245,158,11,0.4)',  text: '#fbbf24' },
  cold:   { bg: 'rgba(244,63,94,0.15)',   border: 'rgba(244,63,94,0.4)',   text: '#fb7185' },
};

function tier(score) {
  if (score > 60) return 'hot';
  if (score >= 30) return 'warm';
  return 'cold';
}

export default function ScoreBadge({ score = 0, size = 44 }) {
  const t = tier(score);
  const c = colorMap[t];

  return (
    <motion.div
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: c.bg,
        border: `2px solid ${c.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-mono)',
        fontSize: size * 0.36,
        fontWeight: 700,
        color: c.text,
        flexShrink: 0,
      }}
    >
      {Math.round(score)}
    </motion.div>
  );
}
