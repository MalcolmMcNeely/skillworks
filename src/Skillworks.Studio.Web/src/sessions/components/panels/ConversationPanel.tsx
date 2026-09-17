import { describeCount, describeMoney, describeStretch } from '../../../figures/lib/figures';
import { inRange, type Range } from '../../lib/brush';
import { describeWithheld, figuresOf, type Band } from '../../lib/panels/conversation';
import { describeClock } from '../../lib/steps';

function Words({ what, said, length, missing }: { what: string; said: string | null; length: number; missing: string }) {
  return (
    <div className="exchange-said">
      <p className="exchange-mark">{what}</p>
      {said === null ? (
        <p className="exchange-withheld">{length === 0 ? missing : describeWithheld(length)}</p>
      ) : (
        <p className="exchange-words">{said}</p>
      )}
    </div>
  );
}

function Block({ band, open, onOpen }: { band: Band; open: boolean; onOpen: (band: Band) => void }) {
  const { exchange } = band;

  return (
    <li>
      <article className={`exchange${open ? ' is-open' : ''}`}>
        <button type="button" className="exchange-head" onClick={() => onOpen(band)}>
          <span className="exchange-count">{exchange.index + 1}</span>
          <span className="exchange-clock">{describeClock(band.startMs, true)}</span>
          <span className="exchange-figure">
            {describeCount(exchange.turns)} turns · {describeCount(exchange.toolCalls)} tool calls ·{' '}
            {describeMoney(exchange.cost)} · {describeStretch(exchange.lengthMs)}
          </span>
        </button>
        <Words what="Prompt" said={exchange.prompt} length={exchange.promptLength} missing="Nothing was recorded." />
        <Words what="Answer" said={exchange.answer} length={exchange.answerLength} missing="Nothing was answered." />
      </article>
    </li>
  );
}

// Every block and every figure here reads the brushed stretch alone, or the panel would answer a question nobody asked.
export function ConversationPanel({
  bands,
  range,
  opened,
  onOpen,
}: {
  bands: readonly Band[];
  range: Range | null;
  opened: number | null;
  onOpen: (band: Band) => void;
}) {
  const shown = inRange(bands, range);
  const figures = figuresOf(shown);

  return (
    <section className="session-panel" aria-label="Conversation">
      <header className="panel-head">
        <h2>Conversation</h2>
        <p className="micro panel-figure">
          {describeCount(figures.exchanges)} exchanges · {describeCount(figures.turns)} turns ·{' '}
          {describeCount(figures.toolCalls)} tool calls · {describeMoney(figures.cost)}
          {range === null ? '' : ' in the stretch in view'}
        </p>
      </header>

      {shown.length === 0 ? (
        <p className="session-word">Nobody typed into this stretch.</p>
      ) : (
        <ol className="exchange-list">
          {shown.map((band) => (
            <Block key={band.exchange.index} band={band} open={band.exchange.index === opened} onOpen={onOpen} />
          ))}
        </ol>
      )}
    </section>
  );
}
