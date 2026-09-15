// PROTOTYPE — throwaway. The floating bar that flips between variants. Development builds only.

import { useEffect } from 'react';
import { useSearchParams } from 'react-router';
import './PrototypeSwitcher.css';

export interface VariantEntry {
  key: string;
  name: string;
}

export function PrototypeSwitcher({ variants }: { variants: VariantEntry[] }) {
  const [params, setParams] = useSearchParams();
  const current = params.get('variant') ?? '';
  const index = Math.max(0, variants.findIndex((variant) => variant.key === current));

  const go = (step: number) => {
    const next = variants[(index + step + variants.length) % variants.length];
    const written = new URLSearchParams(params);

    if (next.key === '') {
      written.delete('variant');
    } else {
      written.set('variant', next.key);
    }

    setParams(written, { replace: true });
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target?.closest('input, textarea, select, [contenteditable], [role="radiogroup"], [role="slider"]');

      if (typing || event.altKey || event.ctrlKey || event.metaKey) {
        return;
      }

      if (event.key === 'ArrowLeft') {
        go(-1);
      } else if (event.key === 'ArrowRight') {
        go(1);
      }
    };

    window.addEventListener('keydown', onKey);

    return () => window.removeEventListener('keydown', onKey);
  });

  const shown = variants[index];

  return (
    <nav className="prototype-switcher" aria-label="Prototype variants">
      <button type="button" onClick={() => go(-1)} aria-label="Previous variant">
        ←
      </button>
      <span aria-live="polite">
        <strong>{shown.key === '' ? '0' : shown.key}</strong> — {shown.name}
      </span>
      <button type="button" onClick={() => go(1)} aria-label="Next variant">
        →
      </button>
    </nav>
  );
}
