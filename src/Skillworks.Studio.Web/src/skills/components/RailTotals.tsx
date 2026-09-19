import { describeCount, describeMoney, describeTokens } from '../../figures/lib/figures';
import { missingWords } from '../../shared/gaps/lib/gaps';
import type { SkillsAnswer } from '../lib/answer';
import { describeEach } from '../lib/skills';

export function RailTotals({ answer, arriving }: { answer: SkillsAnswer | null; arriving: boolean }) {
  const totals = answer?.totals ?? null;

  return (
    <section className={`rail-block totals${arriving ? ' is-arriving' : ''}`} aria-label="Totals" aria-busy={arriving}>
      <dl>
        <div className="total is-hero">
          <dt>Cost</dt>
          <dd>{totals === null ? missingWords.noAnswer : describeMoney(totals.cost)}</dd>
        </div>
        <div className="total">
          <dt>Activations</dt>
          <dd>{totals === null ? missingWords.noAnswer : describeCount(totals.activations)}</dd>
        </div>
        <div className="total">
          <dt>Skills</dt>
          <dd>{totals === null ? missingWords.noAnswer : describeCount(totals.skills)}</dd>
        </div>
        <div className="total">
          <dt>Tokens</dt>
          <dd>{totals === null ? missingWords.noAnswer : describeTokens(totals.tokens)}</dd>
        </div>
        <div className="total">
          <dt>Each</dt>
          <dd>{describeEach(totals)}</dd>
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
