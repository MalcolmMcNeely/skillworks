// PROTOTYPE — throwaway. Three ways to show the Prompt again on the Session page, switchable via ?variant=.
// "Today" is the page as it is now, kept for side-by-side judging.
import { useSearchParams } from 'react-router';
import type { Band } from '../../lib/timeline/conversation';
import type { Highlight } from '../../lib/timeline/highlight';
import type { Mark } from '../../lib/steps';
import { OpenedStep } from '../timeline/OpenedStep';
import { PrototypeSwitcher, type Variant } from './PrototypeSwitcher';
import { VariantA, name as nameA } from './VariantA';
import { VariantB, name as nameB } from './VariantB';
import { VariantC, name as nameC } from './VariantC';
import './promptPrototype.css';

const variants: readonly Variant[] = [
  { key: 'A', name: nameA },
  { key: 'B', name: nameB },
  { key: 'C', name: nameC },
  { key: 'T', name: 'Today, no Prompt' },
];

export function PromptPrototype({
  bands,
  marks,
  step,
  exchange,
  highlight,
  lit,
  traced,
  agents,
  onOpen,
  onExchange,
  onClose,
}: {
  bands: readonly Band[];
  marks: readonly Mark[];
  step: string | null;
  exchange: number | null;
  highlight: Highlight | null;
  lit: ReadonlySet<string> | null;
  traced: boolean;
  agents: Record<string, string>;
  onOpen: (step: string) => void;
  onExchange: (band: Band) => void;
  onClose: () => void;
}) {
  const [params, setParams] = useSearchParams();
  const variant = params.get('variant') ?? 'A';

  const pick = (key: string) => {
    const written = new URLSearchParams(params);

    written.set('variant', key);
    setParams(written, { replace: true });
  };

  return (
    <>
      {variant === 'A' ? (
        <VariantA bands={bands} marks={marks} step={step} exchange={exchange} traced={traced} agents={agents} onExchange={onExchange} onClose={onClose} />
      ) : null}
      {variant === 'B' ? (
        <VariantB bands={bands} marks={marks} step={step} exchange={exchange} onExchange={onExchange} onClose={onClose} />
      ) : null}
      {variant === 'C' ? (
        <VariantC
          bands={bands}
          marks={marks}
          step={step}
          exchange={exchange}
          highlight={highlight}
          lit={lit}
          traced={traced}
          agents={agents}
          onOpen={onOpen}
          onExchange={onExchange}
          onClose={onClose}
        />
      ) : null}
      {variant === 'T' ? <OpenedStep marks={marks} traced={traced} agents={agents} selected={step} onClose={onClose} /> : null}
      <PrototypeSwitcher variants={variants} current={variant} onPick={pick} />
    </>
  );
}
