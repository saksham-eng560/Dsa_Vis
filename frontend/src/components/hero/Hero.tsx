/** Landing hero: big headline, live product demo, scroll-driven fade/scale, feature captions. */
import { motion, useScroll, useTransform } from 'framer-motion';
import { ChevronRight, Cpu, MessageCircleQuestion, Network } from 'lucide-react';
import { useRef } from 'react';

import { useLeetCode } from '../../stores/leetcodeStore';
import { LiveDemo } from './LiveDemo';

const EASE = [0.22, 1, 0.36, 1] as const;

const FEATURES = [
  { icon: Cpu, title: 'Real execution, not guesses.', text: 'Python and C++ are actually run and traced line by line — every value is the real one.' },
  { icon: Network, title: 'Every structure, animated.', text: 'Arrays, maps, stacks, linked lists, trees and graphs, with pointers and swaps highlighted.' },
  { icon: MessageCircleQuestion, title: 'A tutor that knows your code.', text: 'Ask about the exact step you are looking at. It sees your code, the problem and your tests.' },
];

export function scrollToWorkspace() {
  document.getElementById('workspace')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const opacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);
  const scale = useTransform(scrollYProgress, [0, 0.7], [1, 0.94]);
  const y = useTransform(scrollYProgress, [0, 1], [0, -60]);

  const startLeetCode = () => {
    useLeetCode.getState().setMode('leetcode');
    scrollToWorkspace();
  };

  return (
    <section ref={ref} id="overview" className="relative overflow-hidden px-5 pb-20 pt-20 md:pt-28" style={{ background: 'var(--hero-glow)' }}>
      <motion.div style={{ opacity, scale, y }} className="mx-auto max-w-5xl text-center">
        <motion.p className="eyebrow" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: EASE }}>
          CodeLens
        </motion.p>
        <h1 className="display mt-3 text-5xl md:text-7xl lg:text-[5.5rem]">
          {['See', 'your', 'code'].map((w, i) => (
            <span key={w}>
              <motion.span className="inline-block" initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: EASE, delay: 0.1 + i * 0.08 }}>
                {w}
              </motion.span>{' '}
            </span>
          ))}
          <motion.span className="text-spectrum inline-block" initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: EASE, delay: 0.38 }}>
            think.
          </motion.span>
        </h1>
        <motion.p
          className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed md:text-xl"
          style={{ color: 'var(--text-muted)' }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: EASE, delay: 0.55 }}
        >
          Paste Python or C++, or bring a LeetCode problem. Watch it run line by line — every pointer, swap and recursive
          call, made visible.
        </motion.p>
        <motion.div className="mt-9 flex flex-wrap items-center justify-center gap-5" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: EASE, delay: 0.7 }}>
          <button className="btn btn-glow focus-ring !h-12 !px-7 !text-base" onClick={scrollToWorkspace}>
            Open the workspace
          </button>
          <button className="focus-ring flex items-center gap-0.5 rounded-full text-base font-medium hover:underline" style={{ color: 'var(--accent-primary)' }} onClick={startLeetCode}>
            Practise a LeetCode problem <ChevronRight size={18} aria-hidden />
          </button>
        </motion.div>
      </motion.div>

      <motion.div
        className="mx-auto mt-16 max-w-5xl"
        initial={{ opacity: 0, y: 60, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 1.2, ease: EASE, delay: 0.5 }}
      >
        <LiveDemo />
      </motion.div>

      <div className="mx-auto mt-20 grid max-w-5xl gap-10 md:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, text }, i) => (
          <motion.div
            key={title}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.8, ease: EASE, delay: i * 0.12 }}
          >
            <Icon size={28} strokeWidth={1.6} style={{ color: 'var(--accent-primary)' }} aria-hidden />
            <h3 className="display mt-4 text-xl">{title}</h3>
            <p className="mt-2 text-[0.95rem] leading-relaxed" style={{ color: 'var(--text-muted)' }}>{text}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
