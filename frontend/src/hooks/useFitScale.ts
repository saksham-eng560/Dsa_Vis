/** Scale that fits content (w×h) inside the container's width and a max height — never upscales. */
import { useEffect, useState, type RefObject } from 'react';

export function useFitScale(ref: RefObject<HTMLElement | null>, w: number, h: number, maxH: number): number {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(entry?.contentRect.width ?? 0));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  if (!w || !h || !width) return 1;
  return Math.min(1, width / w, maxH / h);
}
