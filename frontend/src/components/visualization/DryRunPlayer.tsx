/** Playback controls: play/pause, step ±, scrubber, speed, breakpoint info. */
import { ChevronFirst, ChevronLast, Pause, Play, StepBack, StepForward } from 'lucide-react';

import { useAppStore } from '../../stores/appStore';
import { GlowButton } from '../ui/GlowButton';

const SPEEDS = [0.5, 1, 1.5, 2, 3, 4];

export function DryRunPlayer({ total }: { total: number }) {
  const step = useAppStore((s) => s.step);
  const playing = useAppStore((s) => s.playing);
  const speed = useAppStore((s) => s.speed);
  const breakpoints = useAppStore((s) => s.breakpoints);
  const { setStep, setPlaying, setSpeed } = useAppStore.getState();
  const atEnd = step >= total - 1;

  return (
    <div className="glass-inset flex flex-col gap-3 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <GlowButton iconOnly aria-label="First step" icon={<ChevronFirst size={16} />} onClick={() => setStep(0)} disabled={step === 0} />
        <GlowButton iconOnly aria-label="Previous step" icon={<StepBack size={16} />} onClick={() => setStep(step - 1)} disabled={step === 0} />
        <GlowButton
          variant="glow"
          aria-label={playing ? 'Pause' : 'Play'}
          icon={playing ? <Pause size={16} /> : <Play size={16} />}
          onClick={() => {
            if (atEnd) setStep(0);
            setPlaying(!playing);
          }}
        >
          {playing ? 'Pause' : atEnd ? 'Replay' : 'Play'}
        </GlowButton>
        <GlowButton iconOnly aria-label="Next step" icon={<StepForward size={16} />} onClick={() => setStep(step + 1)} disabled={atEnd} />
        <GlowButton iconOnly aria-label="Last step" icon={<ChevronLast size={16} />} onClick={() => setStep(total - 1)} disabled={atEnd} />
        <label className="ml-auto flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
          Speed
          <input
            type="range"
            className="slider w-24"
            min={0}
            max={SPEEDS.length - 1}
            step={1}
            value={Math.max(0, SPEEDS.indexOf(speed))}
            onChange={(e) => setSpeed(SPEEDS[Number(e.target.value)] ?? 1)}
            aria-valuetext={`${speed}x`}
          />
          <span className="w-8 font-mono">{speed}x</span>
        </label>
      </div>
      <div className="flex items-center gap-3">
        <input
          type="range"
          className="slider flex-1"
          min={0}
          max={Math.max(total - 1, 0)}
          value={step}
          onChange={(e) => setStep(Number(e.target.value))}
          aria-label="Step"
          aria-valuetext={`Step ${step + 1} of ${total}`}
        />
        <span className="font-mono text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>
          {step + 1} / {total}
        </span>
      </div>
      <p className="text-[0.7rem]" style={{ color: 'var(--text-faint)' }}>
        {breakpoints.length
          ? `● ${breakpoints.length} breakpoint${breakpoints.length > 1 ? 's' : ''} (lines ${[...breakpoints].sort((a, b) => a - b).join(', ')}) — playback pauses there.`
          : 'Tip: click a line number in the editor to set a breakpoint. ←/→ step, space plays.'}
      </p>
    </div>
  );
}
