import { describeCount, describeLength } from '../../../figures/lib/figures';
import { triggerMark } from '../../../provenance/lib/triggers';
import { madeIn, type Range } from '../../lib/view';
import { tallyOf, type ActivationSpell } from '../../lib/panels/activations';
import { describeClock } from '../../lib/steps';

function Row({
  spell,
  open,
  onOpen,
}: {
  spell: ActivationSpell;
  open: boolean;
  onOpen: (spell: ActivationSpell) => void;
}) {
  const { activation } = spell;
  const mark = triggerMark(activation.trigger);

  return (
    <li>
      <button type="button" className={`call-row${open ? ' is-open' : ''}`} onClick={() => onOpen(spell)}>
        <span className="call-clock">{describeClock(spell.atMs, true)}</span>
        <span className="call-name">{activation.skill}</span>
        <span className="call-trigger" aria-hidden="true">
          {mark.glyph}
        </span>
        <span className="visually-hidden">{mark.word}</span>
        <span className="call-spell">{describeLength(activation.followedMs)}</span>
      </button>
    </li>
  );
}

// Every row and every figure here reads the View alone, or the panel would answer a question nobody asked.
export function ActivationPanel({
  spells,
  view,
  opened,
  onOpen,
}: {
  spells: readonly ActivationSpell[];
  view: Range | null;
  opened: string | null;
  onOpen: (spell: ActivationSpell) => void;
}) {
  const shown = madeIn(spells, view);
  const tally = tallyOf(shown);

  return (
    <section className="session-panel" aria-label="Activations">
      <header className="panel-head">
        <h2>Activations</h2>
        <p className="micro panel-figure">
          {describeCount(tally.activations)} activations · {describeCount(tally.skills)} skills
          {view === null ? '' : ' in view'}
        </p>
      </header>

      {shown.length === 0 ? (
        <p className="session-word">{spells.length === 0 ? 'No skill fired in this run.' : 'No skill fired in view.'}</p>
      ) : (
        <ol className="call-list">
          {shown.map((spell) => (
            <Row
              key={spell.activation.id}
              spell={spell}
              open={spell.activation.id === opened}
              onOpen={onOpen}
            />
          ))}
        </ol>
      )}
    </section>
  );
}
