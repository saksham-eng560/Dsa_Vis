/** Export the visible flowchart as PNG / SVG, or copy it as Mermaid source. */
import { useReactFlow } from '@xyflow/react';
import { toPng, toSvg } from 'html-to-image';
import { Code2, Download, Image as ImageIcon } from 'lucide-react';

import type { Flowchart } from '../../types';
import { toMermaid } from '../../utils/diagramHelpers';
import { GlowButton } from '../ui/GlowButton';
import { toast } from '../ui/Toast';

interface FlowExportMenuProps {
  chart: Flowchart;
  group: string;
}

/** Skip UI chrome (zoom controls, panels) in the exported image. */
const exportFilter = (node: HTMLElement) =>
  !(node.classList?.contains('react-flow__controls') || node.classList?.contains('react-flow__panel'));

const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

export function FlowExportMenu({ chart, group }: FlowExportMenuProps) {
  const { fitView } = useReactFlow();
  const name = `codelens-${group.replace(/[^\w]+/g, '') || 'program'}`;

  const run = async (kind: 'png' | 'svg') => {
    const canvas = document.querySelector<HTMLElement>('[data-testid="flowchart-canvas"] .react-flow');
    if (!canvas) return;
    try {
      await fitView({ padding: 0.06, duration: 0 }); // whole diagram in frame
      await nextFrame();
      const light = document.documentElement.dataset.theme === 'light';
      const opts = { backgroundColor: light ? '#f5f3ff' : '#130f24', filter: exportFilter };
      // SVG skips font embedding (small files); PNG embeds fonts so text rasterises correctly.
      const url = kind === 'png' ? await toPng(canvas, { ...opts, pixelRatio: 2 }) : await toSvg(canvas, { ...opts, skipFonts: true });
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name}.${kind}`;
      a.click();
    } catch {
      toast('error', 'Export failed — try the other format.');
    }
  };

  return (
    <div className="flex gap-1.5">
      <GlowButton className="!h-8 !text-xs" icon={<ImageIcon size={14} />} onClick={() => void run('png')} aria-label="Export flowchart as PNG">
        PNG
      </GlowButton>
      <GlowButton className="!h-8 !text-xs" icon={<Download size={14} />} onClick={() => void run('svg')} aria-label="Export flowchart as SVG">
        SVG
      </GlowButton>
      <GlowButton
        className="!h-8 !text-xs"
        icon={<Code2 size={14} />}
        aria-label="Copy Mermaid source"
        onClick={() =>
          void navigator.clipboard
            ?.writeText(toMermaid(chart, group))
            .then(() => toast('success', 'Mermaid diagram copied'))
            .catch(() => toast('error', 'Clipboard unavailable'))
        }
      >
        Mermaid
      </GlowButton>
    </div>
  );
}
