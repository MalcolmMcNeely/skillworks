import { describeCount, describeMoney, describeTokens, type SkillsAnswer } from '../lib/skills';
import { totalsOf } from '../lib/totals';

// A dash, not a zero, while there is no answer to count, so an outage never reads as a quiet week.
const noAnswer = '—';

export function RailTotals({ answer, arriving }: { answer: SkillsAnswer | null; arriving: boolean }) {
  const totals = answer === null ? null : totalsOf(answer);

  return (
    <section className={`rail-block totals${arriving ? ' is-arriving' : ''}`} aria-label="Totals" aria-busy={arriving}>
      <dl>
        <div className="total is-hero">
          <dt>Cost</dt>
          <dd>{totals === null ? noAnswer : describeMoney(totals.cost)}</dd>
        </div>
        <div className="total">
          <dt>Activations</dt>
          <dd>{totals === null ? noAnswer : describeCount(totals.activations)}</dd>
        </div>
        <div className="total">
          <dt>Skills</dt>
          <dd>{totals === null ? noAnswer : describeCount(totals.skills)}</dd>
        </div>
        <div className="total">
          <dt>Tokens</dt>
          <dd>{totals === null ? noAnswer : describeTokens(totals.tokens)}</dd>
        </div>
        <div className="total">
          <dt>Each</dt>
          <dd>{totals?.each == null ? noAnswer : describeMoney(totals.each)}</dd>
        </div>
        {totals?.unnamedSpend != null && (
          <div className="total is-unnamed">
            <dt>Unnamed spend</dt>
            <dd>{describeMoney(totals.unnamedSpend)}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}
