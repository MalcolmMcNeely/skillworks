import { describeCount } from '../../../figures/lib/figures';
import { triggerMark } from '../../../provenance/lib/triggers';
import { madeIn } from '../../lib/brush';
import { tallyOf, type Firing } from '../../lib/skillCalls';
import { describeClock, describeSpell, type Range } from '../../lib/steps';

function Row({ firing, open, onOpen }: { firing: Firing; open: boolean; onOpen: (firing: Firing) => void }) {
  const { call } = firing;
  const mark = triggerMark(call.trigger);

  return (
    <li>
      <button type="button" className={`call-row${open ? ' is-open' : ''}`} onClick={() => onOpen(firing)}>
        <span className="call-clock">{describeClock(firing.atMs, true)}</span>
        <span className="call-name">{call.skill}</span>
        <span className="call-trigger" aria-hidden="true">
          {mark.glyph}
        </span>
        <span className="visually-hidden">{mark.word}</span>
        <span className="call-spell">{describeSpell(call.followedMs)}</span>
      </button>
    </li>
  );
}

// Every row and every figure here reads the brushed stretch alone, or the panel would answer a question nobody asked.
export function SkillCallPanel({
  firings,
  range,
  opened,
  onOpen,
}: {
  firings: readonly Firing[];
  range: Range | null;
  opened: string | null;
  onOpen: (firing: Firing) => void;
}) {
  const shown = madeIn(firings, range);
  const tally = tallyOf(shown);

  return (
    <section className="session-panel" aria-label="Skill calls">
      <header className="panel-head">
        <h2>Skill calls</h2>
        <p className="micro panel-figure">
          {describeCount(tally.calls)} calls · {describeCount(tally.skills)} skills
          {range === null ? '' : ' in the stretch in view'}
        </p>
      </header>

      {shown.length === 0 ? (
        <p className="session-word">{firings.length === 0 ? 'No skill fired in this run.' : 'No skill fired in this stretch.'}</p>
      ) : (
        <ol className="call-list">
          {shown.map((firing) => (
            <Row key={firing.call.id} firing={firing} open={firing.call.id === opened} onOpen={onOpen} />
          ))}
        </ol>
      )}
    </section>
  );
}
