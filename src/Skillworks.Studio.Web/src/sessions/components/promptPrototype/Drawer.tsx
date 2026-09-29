// PROTOTYPE — throwaway.
import { useEffect, type ReactNode } from 'react';

export function Drawer({
  open,
  label,
  wide = false,
  onClose,
  children,
}: {
  open: boolean;
  label: string;
  wide?: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) {
      return;
    }

    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', key);

    return () => window.removeEventListener('keydown', key);
  }, [open, onClose]);

  return (
    <aside
      className={`pp-drawer${open ? ' is-open' : ''}${wide ? ' is-wide' : ''}`}
      aria-label={label}
      aria-hidden={!open}
      inert={!open}
    >
      <header className="pp-drawer-head">
        <p className="micro pp-drawer-label">{label}</p>
        <button type="button" className="step-close" onClick={onClose}>
          Close · Esc
        </button>
      </header>
      {children}
    </aside>
  );
}

export function PromptWords({ words, length, clamp = false }: { words: string | null; length: number; clamp?: boolean }) {
  if (words === null || words === '') {
    return (
      <p className="pp-withheld">{length === 0 ? 'Nothing was recorded.' : `Withheld · ${length.toLocaleString('en-GB')} characters`}</p>
    );
  }

  return <blockquote className={`pp-prompt${clamp ? ' is-clamped' : ''}`}>{words}</blockquote>;
}
