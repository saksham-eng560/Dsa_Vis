/** LeetCode difficulty colour coding. */
const TONE: Record<string, string> = { Easy: 'tone-green', Medium: 'tone-yellow', Hard: 'tone-red' };

export function DifficultyBadge({ difficulty }: { difficulty: string }) {
  return (
    <span className={`${TONE[difficulty] ?? 'tone-neutral'} tone-badge rounded-full px-2 py-0.5 text-[0.7rem] font-semibold`}>
      {difficulty || '—'}
    </span>
  );
}
