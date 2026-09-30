import { useEffect } from 'react';
import { useSearchParams } from 'react-router';

// PROTOTYPE: throwaway. The bar only shows in dev, so a stray merge cannot ship it.
export function PrototypeSwitcher({ variants }: { variants: readonly { key: string; name: string }[] }) {
  const [params, setParams] = useSearchParams();
  const current = Math.max(
    0,
    variants.findIndex((each) => each.key === (params.get('variant') ?? variants[0].key)),
  );

  const go = (step: number) => {
    const next = new URLSearchParams(params);
    next.set('variant', variants[(current + step + variants.length) % variants.length].key);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target !== null && (target.closest('input, textarea') !== null || target.isContentEditable)) {
        return;
      }
      if (event.key === 'ArrowLeft') go(-1);
      if (event.key === 'ArrowRight') go(1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  if (!import.meta.env.DEV) {
    return null;
  }

  const shown = variants[current];

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 16,
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        gap: 12,
        alignItems: 'center',
        padding: '6px 14px',
        borderRadius: 999,
        background: '#111',
        color: '#ff0',
        boxShadow: '0 4px 16px rgba(0,0,0,.5)',
        font: '13px monospace',
        zIndex: 1000,
      }}
    >
      <button type="button" onClick={() => go(-1)} style={{ all: 'unset', cursor: 'pointer' }}>
        ◀
      </button>
      <span>
        PROTOTYPE {shown.key} — {shown.name}
      </span>
      <button type="button" onClick={() => go(1)} style={{ all: 'unset', cursor: 'pointer' }}>
        ▶
      </button>
    </div>
  );
}
