// PROTOTYPE — throwaway. Round two: where the detail of a Turn or a Tool call goes, now that the conversation
// drawer won round one. Switchable via ?variant=. T is the conversation drawer as it won, with no detail.
// Round one's other variants, One Exchange and The chain, are kept at commit df043dc on this branch.
import { useSearchParams } from 'react-router';
import type { Band } from '../../lib/timeline/conversation';
import type { Mark } from '../../lib/steps';
import { Conversation } from './Conversation';
import { PrototypeSwitcher, type Variant } from './PrototypeSwitcher';
import { VariantAtMark, name as nameAtMark } from './VariantAtMark';
import { VariantPane, name as namePane } from './VariantPane';
import { VariantThread, name as nameThread } from './VariantThread';
import './promptPrototype.css';

const variants: readonly Variant[] = [
  { key: 'A', name: nameThread },
  { key: 'B', name: namePane },
  { key: 'C', name: nameAtMark },
  { key: 'T', name: 'Today, no detail' },
];

export function PromptPrototype({
  bands,
  marks,
  step,
  exchange,
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
  traced: boolean;
  agents: Record<string, string>;
  onOpen: (step: string | null) => void;
  onExchange: (band: Band) => void;
  onClose: () => void;
}) {
  const [params, setParams] = useSearchParams();
  const variant = params.get('variant') ?? 'A';
  const shared = { bands, marks, step, exchange, traced, agents, onOpen, onExchange, onClose };

  const pick = (key: string) => {
    const written = new URLSearchParams(params);

    written.set('variant', key);
    setParams(written, { replace: true });
  };

  return (
    <>
      {variant === 'A' ? <VariantThread {...shared} /> : null}
      {variant === 'B' ? <VariantPane {...shared} /> : null}
      {variant === 'C' ? <VariantAtMark {...shared} /> : null}
      {variant === 'T' ? (
        <Conversation bands={bands} marks={marks} step={step} exchange={exchange} onExchange={onExchange} onClose={onClose} />
      ) : null}
      <PrototypeSwitcher variants={variants} current={variant} onPick={pick} />
    </>
  );
}
