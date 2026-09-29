// PROTOTYPE — throwaway. The floating bar that flips between the variants.
import { useEffect } from 'react';

export interface Variant {
  key: string;
  name: string;
}

export function PrototypeSwitcher({
  variants,
  current,
  onPick,
}: {
  variants: readonly Variant[];
  current: string;
  onPick: (key: string) => void;
}) {
  const at = Math.max(0, variants.findIndex((variant) => variant.key === current));
  const step = (by: number) => onPick(variants[(at + by + variants.length) % variants.length].key);

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;

      if (target?.closest('input, textarea, [contenteditable]')) {
        return;
      }

      if (event.key === 'ArrowLeft') {
        step(-1);
      } else if (event.key === 'ArrowRight') {
        step(1);
      }
    };

    window.addEventListener('keydown', key);

    return () => window.removeEventListener('keydown', key);
  });

  if (!import.meta.env.DEV) {
    return null;
  }

  return (
    <div className="pp-switcher" role="toolbar" aria-label="Prototype variants">
      <button type="button" onClick={() => step(-1)} aria-label="Previous variant">
        ←
      </button>
      <span>
        {variants[at].key} — {variants[at].name}
      </span>
      <button type="button" onClick={() => step(1)} aria-label="Next variant">
        →
      </button>
    </div>
  );
}
