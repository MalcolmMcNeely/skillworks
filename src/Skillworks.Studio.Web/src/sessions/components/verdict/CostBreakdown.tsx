import { describeMoney } from '../../../shared/figures/lib/figures';
import type { Exchange } from '../../lib/panels/conversation';
import { noExchangeWord, shareOf, type CostBar, type CostBreakdown as Breakdown } from '../../lib/panels/costBreakdown';

function Bar({
  bar,
  breakdown,
  onExchange,
  onSubagent,
}: {
  bar: CostBar;
  breakdown: Breakdown;
  onExchange: (exchange: Exchange) => void;
  onSubagent: (agent: string) => void;
}) {
  const { exchange } = bar;

  return (
    <li className="cost-row">
      <span className="cost-word" title={exchange?.prompt ?? undefined}>
        {bar.word}
      </span>
      <span className="cost-track">
        {exchange === null ? (
          <span className="cost-fill is-before" style={{ width: `${shareOf(bar.cost, breakdown) * 100}%` }} />
        ) : (
          <button
            type="button"
            className="cost-fill is-exchange"
            style={{ width: `${shareOf(bar.ownCost, breakdown) * 100}%` }}
            title={`${bar.word} · ${describeMoney(bar.ownCost)} by the main agent. Show it on the Timeline.`}
            aria-label={`Show ${bar.word} on the Timeline`}
            onClick={() => onExchange(exchange)}
          />
        )}
        {bar.subagents.map((subagent) => (
          <button
            key={subagent.agent}
            type="button"
            className="cost-fill is-subagent"
            style={{ width: `${shareOf(subagent.cost, breakdown) * 100}%` }}
            title={`${subagent.name} · ${describeMoney(subagent.cost)}. Show its Steps alone.`}
            aria-label={`Show the Steps of ${subagent.name} alone`}
            onClick={() => onSubagent(subagent.agent)}
          />
        ))}
      </span>
      <span className="cost-figure">{describeMoney(bar.cost)}</span>
    </li>
  );
}

export function CostBreakdown({
  breakdown,
  onExchange,
  onSubagent,
}: {
  breakdown: Breakdown | null;
  onExchange: (exchange: Exchange) => void;
  onSubagent: (agent: string) => void;
}) {
  return (
    <section className="session-panel" aria-label="Cost breakdown">
      <header className="panel-head">
        <h2>Cost breakdown</h2>
        {breakdown === null ? null : (
          <p className="micro panel-figure">{describeMoney(breakdown.total)} over the whole run</p>
        )}
      </header>

      {breakdown === null ? (
        <p className="session-word">{noExchangeWord}</p>
      ) : (
        <>
          <ul className="cost-rows">
            {breakdown.bars.map((bar) => (
              <Bar
                key={bar.exchange?.index ?? 'before'}
                bar={bar}
                breakdown={breakdown}
                onExchange={onExchange}
                onSubagent={onSubagent}
              />
            ))}
          </ul>
          <ul className="breakdown-legend">
            <li className="breakdown-key">
              <span className="breakdown-dot is-model" aria-hidden="true" />
              <span className="breakdown-word">Main agent</span>
            </li>
            <li className={`breakdown-key${breakdown.subagentsKnown ? '' : ' is-unknown'}`}>
              <span className="breakdown-dot is-subagents" aria-hidden="true" />
              <span className="breakdown-word">
                {breakdown.subagentsKnown ? 'Subagents' : 'Subagents: not known, as no Span named them'}
              </span>
            </li>
          </ul>
        </>
      )}
    </section>
  );
}
