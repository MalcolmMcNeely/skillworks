// PROTOTYPE — throwaway. Variant A, Deck: podium's cyan HUD, readouts over a trace over a ranked ladder.

import { useState } from 'react';
import type { Activation } from '../../activations/api/activations';
import type { SkillSummary } from '../api/skills';
import {
  ago,
  binCounts,
  callSign,
  compact,
  countTriggers,
  firingsOf,
  lastFired,
  money,
  partMarks,
  positionIn,
  signalOf,
  signalWords,
  spanChoices,
  timeframeOf,
  totalsOf,
  triggerKeys,
  triggerMarks,
  type Signal,
  type Timeframe,
} from './glance';
import type { Glance } from './useGlance';
import './DeckVariant.css';

type Rank = 'firings' | 'cost' | 'recent';

export function DeckVariant({ glance }: { glance: Glance }) {
  const answer = glance.skills;
  const signal: Signal | null =
    glance.skillsError !== null ? 'offline' : answer === null ? null : signalOf(answer.gap.kind);
  const skills = answer?.skills ?? [];
  const activations = glance.activations?.activations ?? [];
  const totals = totalsOf(skills);
  const unnamed = answer?.unnamedSpend?.cost ?? 0;
  const waiting = answer === null && glance.skillsError === null;
  const blank = signal === 'offline' && skills.length === 0;

  return (
    <div className="deck">
      <div className="deck-frame" aria-hidden="true">
        <span className="deck-corner tl" />
        <span className="deck-corner tr" />
        <span className="deck-corner bl" />
        <span className="deck-corner br" />
        <span className="deck-sweep" />
      </div>

      <header className="deck-head">
        <div className="deck-identity">
          <h1>Skillworks</h1>
          <SignalWord signal={signal} tooltip={glance.skillsError ?? answer?.gap.missing ?? null} />
        </div>

        <Keys glance={glance} />

        <div className="deck-systems">
          <Lamps glance={glance} />
          <Power glance={glance} />
        </div>
      </header>

      <section className="deck-readouts" aria-label="Totals">
        <Readout label="Firings" value={waiting || blank ? null : String(totals.firings)} />
        <Readout label="Cost" value={waiting || blank ? null : money(totals.cost)} />
        <Readout label="Skills" value={waiting || blank ? null : String(totals.skills)} />
        <Readout label="Tokens" value={waiting || blank ? null : compact(totals.tokens)} />
        {unnamed > 0 && <Readout label="Unnamed" value={money(unnamed)} tone="unnamed" />}
      </section>

      {blank ? (
        <section className="deck-nosignal" aria-live="polite">
          <p>No signal</p>
          <button type="button" className="deck-action" onClick={glance.recheck} aria-label="Check again">
            ↻
          </button>
        </section>
      ) : (
        <>
          <Trace glance={glance} activations={activations} />
          <Ladder glance={glance} skills={skills} activations={activations} busiest={totals.busiest} priciest={totals.priciest} />
        </>
      )}
    </div>
  );
}

function SignalWord({ signal, tooltip }: { signal: Signal | null; tooltip: string | null }) {
  if (signal === null) {
    return <span className="deck-signal is-waiting">···</span>;
  }

  // The power switch already says telemetry is off.
  if (signal === 'dark') {
    return null;
  }

  return (
    <span className={`deck-signal is-${signal}`} title={tooltip ?? undefined}>
      <span className="deck-signal-dot" aria-hidden="true" />
      {signalWords[signal]}
    </span>
  );
}

function Keys({ glance }: { glance: Glance }) {
  return (
    <div className="deck-keys" role="group" aria-label="Span">
      {spanChoices.map((choice) => (
        <button
          type="button"
          key={choice.key}
          className="deck-key"
          aria-pressed={glance.span === choice.key}
          onClick={() => glance.chooseSpan(choice.key)}
        >
          {choice.label}
        </button>
      ))}
    </div>
  );
}

function Lamps({ glance }: { glance: Glance }) {
  // The telemetry part is drawn as the power switch instead, so the one fact has one control.
  const parts = (glance.health?.parts ?? []).filter((part) => part.name !== 'Claude Code telemetry');

  return (
    <div className="deck-lamps">
      {glance.health === null && (
        <span className="deck-lamp is-unknown" title={glance.healthFailure ?? 'Asking'}>
          <span aria-hidden="true">?</span> Health
        </span>
      )}
      {parts.map((part) => (
        <span
          key={part.name}
          className={`deck-lamp is-${part.state}`}
          title={[part.detail, part.action].filter(Boolean).join(' ')}
        >
          <span className="deck-lamp-mark" aria-hidden="true">
            {partMarks[part.state].glyph}
          </span>
          <span className="deck-lamp-name">{callSign(part)}</span>
          <span className="deck-hidden">{partMarks[part.state].label}</span>
        </span>
      ))}
      <button type="button" className="deck-action" onClick={glance.recheck} aria-label="Check health again">
        ↻
      </button>
    </div>
  );
}

function Power({ glance }: { glance: Glance }) {
  const [arming, setArming] = useState(false);
  const telemetry = glance.telemetry;

  if (telemetry === null) {
    return null;
  }

  const press = () => {
    if (telemetry.emitting) {
      glance.flipTelemetry(false);
    } else if (telemetry.readable) {
      setArming((open) => !open);
    }
  };

  return (
    <div className="deck-power-wrap">
      <button
        type="button"
        className={`deck-power${telemetry.emitting ? ' is-on' : ''}`}
        aria-pressed={telemetry.emitting}
        aria-expanded={telemetry.emitting ? undefined : arming}
        disabled={!telemetry.readable}
        title={telemetry.readable ? telemetry.restartNote : (telemetry.problem ?? undefined)}
        onClick={press}
      >
        <span aria-hidden="true">⏻</span>
        <span className="deck-power-word">Telemetry</span>
        <span className="deck-power-state">{telemetry.emitting ? 'On' : 'Off'}</span>
      </button>

      {arming && !telemetry.emitting && (
        <div className="deck-arm" role="dialog" aria-label="Turn telemetry on">
          <span className="deck-micro">Write</span>
          <code className="deck-arm-path">{telemetry.settingsPath}</code>
          <ul>
            {telemetry.changes.map((change) => (
              <li key={change.name}>
                {change.name} <span aria-hidden="true">→</span> {change.to}
              </li>
            ))}
          </ul>
          <div className="deck-arm-actions">
            <button
              type="button"
              className="deck-action is-primary"
              onClick={() => {
                glance.flipTelemetry(true);
                setArming(false);
              }}
            >
              ⏻ On
            </button>
            <button type="button" className="deck-action" onClick={() => setArming(false)} aria-label="Cancel">
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Readout({ label, value, tone }: { label: string; value: string | null; tone?: 'unnamed' }) {
  return (
    <div className={`deck-readout${tone ? ` is-${tone}` : ''}`}>
      <span className="deck-readout-value">{value ?? '—'}</span>
      <span className="deck-micro">{label}</span>
    </div>
  );
}

function tickLabels(frame: Timeframe): { at: number; text: string }[] {
  const hour = 60 * 60 * 1000;
  const step = frame.days === 1 ? 6 * hour : frame.days <= 7 ? 24 * hour : 7 * 24 * hour;
  const labels: { at: number; text: string }[] = [];

  for (let moment = frame.start; moment < frame.end; moment += step) {
    const date = new Date(moment);
    const text =
      frame.days === 1
        ? date.toISOString().slice(11, 13)
        : frame.days <= 7
          ? date.toLocaleDateString('en-GB', { weekday: 'short', timeZone: 'UTC' })
          : date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' });

    labels.push({ at: (moment - frame.start) / (frame.end - frame.start), text });
  }

  return labels;
}

function Trace({ glance, activations }: { glance: Glance; activations: Activation[] }) {
  const span = glance.skills?.span ?? glance.activations?.span;

  if (span === undefined) {
    return <div className="deck-trace is-waiting" aria-hidden="true" />;
  }

  const frame = timeframeOf(span);
  const bins = frame.days === 1 ? 24 : frame.days <= 7 ? frame.days * 4 : frame.days;
  const counts = binCounts(activations, frame, bins);
  const peak = Math.max(1, ...counts);
  const now = positionIn(frame, new Date().toISOString());

  return (
    <section className="deck-trace" aria-label={`${activations.length} firings, ${span.from} to ${span.to}`}>
      <div className="deck-trace-plot">
        {counts.map((count, index) => (
          <span
            key={index}
            className={`deck-trace-bar${count === 0 ? ' is-idle' : ''}`}
            style={{ height: count === 0 ? undefined : `${Math.max(8, (count / peak) * 100)}%` }}
            title={String(count)}
          />
        ))}
        {now < 1 && <span className="deck-trace-now" style={{ left: `${now * 100}%` }} aria-hidden="true" />}
      </div>
      <div className="deck-trace-axis" aria-hidden="true">
        {tickLabels(frame).map((tick) => (
          <span key={tick.at} style={{ left: `${tick.at * 100}%` }}>
            {tick.text}
          </span>
        ))}
      </div>
    </section>
  );
}

function Ladder({
  glance,
  skills,
  activations,
  busiest,
  priciest,
}: {
  glance: Glance;
  skills: SkillSummary[];
  activations: Activation[];
  busiest: number;
  priciest: number;
}) {
  const [rank, setRank] = useState<Rank>('firings');

  if (glance.skills === null) {
    return <div className="deck-ladder is-waiting" aria-hidden="true" />;
  }

  if (skills.length === 0) {
    return (
      <section className="deck-nosignal is-quiet">
        <p>Quiet</p>
      </section>
    );
  }

  const latest = new Map(skills.map((skill) => [skill.name, lastFired(activations, skill.name)]));
  const ranked = skills.toSorted((a, b) => {
    if (rank === 'cost') {
      return (b.spend?.cost ?? -1) - (a.spend?.cost ?? -1);
    }

    if (rank === 'recent') {
      return (latest.get(b.name) ?? '').localeCompare(latest.get(a.name) ?? '');
    }

    return b.activations - a.activations;
  });

  const sorter = (key: Rank, label: string) => (
    <button type="button" className="deck-sort" aria-pressed={rank === key} onClick={() => setRank(key)}>
      {label}
      <span aria-hidden="true">{rank === key ? ' ▾' : ''}</span>
    </button>
  );

  return (
    <section className="deck-ladder" aria-label="Skills">
      <div className="deck-ladder-head" aria-hidden="false">
        <span />
        <span className="deck-micro">Skill</span>
        {sorter('firings', 'Firings')}
        <span className="deck-micro deck-col-triggers">
          {triggerKeys
            .filter((key) => key !== 'unknown')
            .map((key) => (
              <span key={key} title={triggerMarks[key].label} className={`deck-trigger-key is-${key}`}>
                {triggerMarks[key].glyph}
              </span>
            ))}
        </span>
        {sorter('cost', 'Cost')}
        <span className="deck-micro deck-col-each">Each</span>
        {sorter('recent', 'Last')}
      </div>

      <ol className="deck-rows">
        {ranked.map((skill, index) => {
          const fired = firingsOf(activations, skill.name);
          const triggers = countTriggers(fired);
          const last = latest.get(skill.name) ?? null;
          const cost = skill.spend?.cost ?? null;

          return (
            <li key={skill.name}>
              <button
                type="button"
                className="deck-row"
                onClick={() => glance.openSkill(skill.name)}
                aria-label={`${skill.name}: ${skill.activations} firings, ${money(cost)}${last ? `, last ${ago(last)} ago` : ''}`}
              >
                <span className="deck-rank">{String(index + 1).padStart(2, '0')}</span>
                <span className="deck-name">{skill.name}</span>

                <span className="deck-firings">
                  <span className="deck-track">
                    <span className="deck-fill" style={{ width: `${(skill.activations / Math.max(1, busiest)) * 100}%` }}>
                      {triggerKeys.map((key) =>
                        triggers[key] === 0 ? null : (
                          <span key={key} className={`deck-segment is-${key}`} style={{ flexGrow: triggers[key] }} />
                        ),
                      )}
                    </span>
                  </span>
                  <span className="deck-count">{skill.activations}</span>
                </span>

                <span className="deck-col-triggers deck-triggers">
                  {triggerKeys.map((key) =>
                    key === 'unknown' ? null : (
                      <span key={key} className={`deck-trigger is-${key}${triggers[key] === 0 ? ' is-none' : ''}`}>
                        {triggers[key] === 0 ? '·' : triggers[key]}
                      </span>
                    ),
                  )}
                </span>

                <span className="deck-cost">
                  <span className="deck-cost-track">
                    <span className="deck-cost-fill" style={{ width: `${((cost ?? 0) / Math.max(0.0001, priciest)) * 100}%` }} />
                  </span>
                  <span className="deck-cost-value" title={cost === null ? 'Not named' : undefined}>
                    {money(cost)}
                  </span>
                </span>

                <span className="deck-col-each deck-each">{money(skill.averageCost)}</span>
                <span className="deck-last">{last === null ? '—' : ago(last)}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
