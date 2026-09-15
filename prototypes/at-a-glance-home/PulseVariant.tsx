// PROTOTYPE — throwaway. Variant C, Pulse: every firing on a time lane, drawn as a light hardware console.

import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import type { Activation } from '../../activations/api/activations';
import { activationPath } from '../../activations/lib/activations';
import type { Part } from '../../health/lib/health';
import type { SkillSummary } from '../api/skills';
import {
  binCounts,
  callSign,
  compact,
  countTriggers,
  dayLabels,
  money,
  partMarks,
  positionIn,
  signalOf,
  signalWords,
  spanChoices,
  timeframeOf,
  totalsOf,
  triggerKeys,
  triggerOf,
  type Signal,
  type Timeframe,
  type TriggerCounts,
  type TriggerKey,
} from './glance';
import type { Glance } from './useGlance';
import './PulseVariant.css';

const dayMs = 24 * 60 * 60 * 1000;

const shapes: Record<TriggerKey, string> = {
  'claude-proactive': 'dot',
  'user-slash': 'ring',
  'nested-skill': 'square',
  'agent-preload': 'diamond',
  unknown: 'cross',
};

const words: Record<TriggerKey, string> = {
  'claude-proactive': 'Claude',
  'user-slash': 'Typed',
  'nested-skill': 'Skill',
  'agent-preload': 'Agent',
  unknown: 'Unknown',
};

const signalGlyphs: Record<Signal, string> = {
  live: '●',
  offline: '✕',
  dark: '○',
  unsure: '?',
  quiet: '–',
  clipped: '◐',
};

// Until the first answer names its span, the lookback it will almost certainly name.
function lookbackFrame(): Timeframe {
  const today = Date.parse(`${new Date().toISOString().slice(0, 10)}T00:00:00Z`);

  return { start: today - 6 * dayMs, end: today + dayMs, days: 7 };
}

interface Band {
  left: number;
  width: number;
  label: string;
}

function bandsOf(frame: Timeframe): Band[] {
  if (frame.days <= 1) {
    return [0, 6, 12, 18].map((hour) => ({ left: hour / 24, width: 0.25, label: String(hour).padStart(2, '0') }));
  }

  return dayLabels(frame).map((weekday, day) => {
    const date = String(new Date(frame.start + day * dayMs).getUTCDate());
    const label = frame.days <= 10 ? weekday : frame.days <= 16 || day % 2 === 0 ? date : '';

    return { left: day / frame.days, width: 1 / frame.days, label };
  });
}

function binsFor(frame: Timeframe): number {
  if (frame.days <= 1) {
    return 24;
  }

  return frame.days <= 14 ? frame.days * 4 : frame.days;
}

function when(moment: number | string): string {
  const date = new Date(moment);
  const day = date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', timeZone: 'UTC' });

  return `${day} ${date.toISOString().slice(11, 16)}`;
}

function percent(fraction: number): string {
  return `${(fraction * 100).toFixed(3)}%`;
}

export function PulseVariant({ glance }: { glance: Glance }) {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const span = glance.skills?.span ?? glance.activations?.span ?? null;
  const frame = span === null ? lookbackFrame() : timeframeOf(span);
  const skills = glance.skills?.skills ?? [];
  const activations = glance.activations?.activations ?? [];
  const signal = glance.skills === null ? null : signalOf(glance.skills.gap.kind);
  const gapTitle = glance.skills?.gap.missing ?? undefined;

  const loading = glance.skills === null && glance.skillsError === null;
  const empty = glance.skills !== null && skills.length === 0;
  // Nothing answered is missing, not none, so it must never read as a zero.
  const missing = loading || glance.skillsError !== null || (empty && signal !== 'quiet' && signal !== 'live');

  const [openedAt] = useState(() => Date.now());
  const bands = bandsOf(frame);
  const now = (openedAt - frame.start) / (frame.end - frame.start);
  const showNow = now >= 0 && now <= 1;

  const lanes = skills.toSorted((a, b) => b.activations - a.activations || a.name.localeCompare(b.name));
  const bySkill = new Map<string, Activation[]>();

  for (const activation of activations) {
    bySkill.set(activation.skill, [...(bySkill.get(activation.skill) ?? []), activation]);
  }

  const openFiring = (id: string) => navigate(activationPath(params.toString(), id));

  return (
    <div className="pulse">
      <header className="pulse-header">
        <h1 className="pulse-title">skillworks</h1>

        <Display glance={glance} signal={signal} gapTitle={gapTitle} missing={missing} />

        <div className="pulse-controls">
          <SpanKeys glance={glance} />
          <Leds glance={glance} />
          <TelemetryToggle glance={glance} />
        </div>
      </header>

      <section className="pulse-panel" aria-label="Firings over time" aria-busy={loading}>
        <div className="pulse-panel-top">
          <Legend counts={missing ? null : countTriggers(activations)} />
          {signal === 'clipped' && (
            <span className="pulse-chip" title={gapTitle} tabIndex={0}>
              ◐ {signalWords.clipped}
            </span>
          )}
        </div>

        <div className="pulse-scroll">
          <div className="pulse-grid">
            <div className="pulse-bands" aria-hidden="true">
              {bands.map((band, index) => (
                <span
                  key={band.left}
                  className={`pulse-band ${index % 2 === 1 ? 'is-alt' : ''}`}
                  style={{ left: percent(band.left), width: percent(band.width) }}
                />
              ))}
              {showNow && <span className="pulse-now" title="Now" style={{ left: percent(now) }} />}
            </div>

            <div className="pulse-row pulse-axis" aria-hidden="true">
              <span />
              <div className="pulse-ticks">
                {bands.map((band) => (
                  <span
                    key={band.left}
                    className={`pulse-tick ${frame.days <= 1 ? 'is-hour' : ''}`}
                    style={{ left: percent(band.left), width: percent(band.width) }}
                  >
                    {band.label}
                  </span>
                ))}
              </div>
              <span className="pulse-head">#</span>
              <span className="pulse-head">$</span>
            </div>

            <div className="pulse-row pulse-all">
              <span className="pulse-all-label">All</span>
              <Histogram activations={activations} frame={frame} loading={loading} />
              <span />
              <span />
            </div>

            {loading && (
              <ol className="pulse-lanes" aria-hidden="true">
                {['a', 'b', 'c', 'd', 'e', 'f'].map((key) => (
                  <li key={key} className="pulse-row pulse-lane is-skeleton">
                    <span className="pulse-skeleton" />
                    <span className="pulse-track is-empty" />
                    <span />
                    <span />
                  </li>
                ))}
              </ol>
            )}

            {glance.skillsError !== null && <Flatline glyph="✕" word="Error" title={glance.skillsError} alarm />}

            {empty && signal !== null && (
              <Flatline
                glyph={signalGlyphs[signal]}
                word={signal === 'live' || signal === 'clipped' ? signalWords.quiet : signalWords[signal]}
                title={gapTitle}
                alarm={signal === 'offline'}
              />
            )}

            {lanes.length > 0 && (
              <ol className="pulse-lanes" aria-label="Skills by firings">
                {lanes.map((skill) => (
                  <Lane
                    key={skill.name}
                    skill={skill}
                    firings={bySkill.get(skill.name) ?? []}
                    frame={frame}
                    onOpen={glance.openSkill}
                    onFiring={openFiring}
                  />
                ))}
              </ol>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function Display({
  glance,
  signal,
  gapTitle,
  missing,
}: {
  glance: Glance;
  signal: Signal | null;
  gapTitle: string | undefined;
  missing: boolean;
}) {
  const totals = totalsOf(glance.skills?.skills ?? []);
  const unnamed = glance.skills?.unnamedSpend?.cost ?? 0;
  const blank = missing;

  let status = { key: 'loading', glyph: '…', word: 'Wait', title: undefined as string | undefined };

  if (glance.skillsError !== null) {
    status = { key: 'error', glyph: '✕', word: 'Error', title: glance.skillsError };
  } else if (signal !== null) {
    status = { key: signal, glyph: signalGlyphs[signal], word: signalWords[signal], title: gapTitle };
  }

  return (
    <div className="pulse-display" role="group" aria-label="Totals">
      <p className={`pulse-status is-${status.key}`} title={status.title} tabIndex={status.title ? 0 : undefined}>
        <span className="pulse-status-glyph" aria-hidden="true">
          {status.glyph}
        </span>
        {status.word}
      </p>

      <dl className="pulse-counters">
        <div className="is-hero">
          <dt>Firings</dt>
          <dd>{blank ? '--' : totals.firings}</dd>
        </div>
        <div>
          <dt>Cost</dt>
          <dd>{blank ? '--' : money(totals.cost)}</dd>
        </div>
        <div>
          <dt>Tokens</dt>
          <dd>{blank ? '--' : compact(totals.tokens)}</dd>
        </div>
        {unnamed > 0 && (
          <div className="is-unnamed" title="Spend Claude Code would not name a skill for" tabIndex={0}>
            <dt>Unnamed</dt>
            <dd>{money(unnamed)}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}

function SpanKeys({ glance }: { glance: Glance }) {
  const keys = useRef<(HTMLButtonElement | null)[]>([]);
  const chosen = spanChoices.findIndex((choice) => choice.key === glance.span);
  const resting = chosen < 0 ? 1 : chosen;

  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') {
      return;
    }

    event.preventDefault();

    const next = (resting + (event.key === 'ArrowRight' ? 1 : -1) + spanChoices.length) % spanChoices.length;

    glance.chooseSpan(spanChoices[next].key);
    keys.current[next]?.focus();
  };

  return (
    <div className="pulse-keys" role="radiogroup" aria-label="Span" onKeyDown={onKey}>
      {spanChoices.map((choice, index) => (
        <button
          key={choice.key}
          ref={(key) => {
            keys.current[index] = key;
          }}
          type="button"
          role="radio"
          aria-checked={glance.span === choice.key}
          tabIndex={index === resting ? 0 : -1}
          className="pulse-key"
          onClick={() => glance.chooseSpan(choice.key)}
        >
          {choice.label}
        </button>
      ))}
      {glance.span === 'custom' && (
        <span className="pulse-custom">
          {glance.filter.from || '…'}–{glance.filter.to || '…'}
        </span>
      )}
    </div>
  );
}

function Leds({ glance }: { glance: Glance }) {
  return (
    <div className="pulse-leds">
      {glance.health === null && glance.healthFailure === null && (
        <span className="pulse-led-group" role="img" aria-label="Health: asking">
          <span className="pulse-led is-starting" />
          <span className="pulse-led-label">…</span>
        </span>
      )}

      {glance.healthFailure !== null && (
        <span
          className="pulse-led-group"
          role="img"
          tabIndex={0}
          aria-label={`API: broken. ${glance.healthFailure}`}
          title={glance.healthFailure}
        >
          <span className="pulse-led is-broken">✕</span>
          <span className="pulse-led-label">API</span>
        </span>
      )}

      {glance.health?.parts
        .filter((part) => part !== telemetryPart(glance))
        .map((part) => <Led key={part.name} part={part} />)}

      <button type="button" className="pulse-recheck" aria-label="Check health again" onClick={glance.recheck}>
        ↻
      </button>
    </div>
  );
}

// The switch already says whether telemetry is on, so its health part lights the switch rather than a lamp of its own.
function telemetryPart(glance: Glance): Part | undefined {
  return glance.telemetry === null ? undefined : glance.health?.parts.find((part) => callSign(part) === 'Telemetry');
}

function said(part: Part): string {
  return part.action === null ? part.detail : `${part.detail} ${part.action}`;
}

function Led({ part }: { part: Part }) {

  return (
    <span
      className="pulse-led-group"
      role="img"
      tabIndex={0}
      aria-label={`${callSign(part)}: ${partMarks[part.state].label}. ${said(part)}`}
      title={said(part)}
    >
      <span className={`pulse-led is-${part.state}`}>{part.state === 'broken' ? '✕' : ''}</span>
      <span className="pulse-led-label">{callSign(part)}</span>
    </span>
  );
}

function TelemetryToggle({ glance }: { glance: Glance }) {
  const [asking, setAsking] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const write = useRef<HTMLButtonElement>(null);
  const telemetry = glance.telemetry;
  const on = telemetry?.emitting ?? false;
  const unreadable = telemetry !== null && !telemetry.readable;
  const part = telemetryPart(glance);
  const alarm = part !== undefined && (part.state === 'broken' || part.state === 'starting');

  useEffect(() => {
    if (!asking) {
      return;
    }

    write.current?.focus();

    const away = (event: PointerEvent) => {
      if (!wrap.current?.contains(event.target as Node)) {
        setAsking(false);
      }
    };

    document.addEventListener('pointerdown', away);

    return () => document.removeEventListener('pointerdown', away);
  }, [asking]);

  const press = () => {
    if (on) {
      glance.flipTelemetry(false);
    } else {
      setAsking((open) => !open);
    }
  };

  return (
    <div
      ref={wrap}
      className="pulse-toggle-wrap"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          setAsking(false);
        }
      }}
    >
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label="Telemetry"
        aria-description={part === undefined ? undefined : said(part)}
        className={`pulse-toggle ${on ? 'is-on' : ''}`}
        disabled={telemetry === null || (unreadable && !on)}
        title={unreadable ? (telemetry.problem ?? telemetry.settingsPath) : part === undefined ? undefined : said(part)}
        onClick={press}
      >
        <span className="pulse-toggle-knob" />
      </button>
      <span className="pulse-led-label" aria-hidden="true">
        {alarm && <span className={`pulse-led is-${part.state} is-inline`}>{part.state === 'broken' ? '✕' : ''}</span>}
        Telemetry
      </span>

      {asking && telemetry !== null && (
        <div className="pulse-confirm" role="dialog" aria-label="Turn telemetry on">
          <code className="pulse-confirm-path">{telemetry.settingsPath}</code>
          <ul>
            {telemetry.changes.map((change) => (
              <li key={change.name}>
                <code>{change.name}</code>
                <span aria-hidden="true"> → </span>
                <span className="pulse-sr"> becomes </span>
                <code className="pulse-confirm-to">{change.to}</code>
              </li>
            ))}
          </ul>
          <div className="pulse-confirm-keys">
            <button
              ref={write}
              type="button"
              className="pulse-key is-write"
              onClick={() => {
                glance.flipTelemetry(true);
                setAsking(false);
              }}
            >
              Write
            </button>
            <button type="button" className="pulse-key" aria-label="Cancel" onClick={() => setAsking(false)}>
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Legend({ counts }: { counts: TriggerCounts | null }) {
  return (
    <ul className="pulse-legend" aria-label="Triggers">
      {triggerKeys.map((key) => (
        <li key={key} className={counts !== null && counts[key] === 0 ? 'is-none' : ''}>
          <span className={`pulse-shape is-${shapes[key]}`} aria-hidden="true" />
          {words[key]}
          {counts !== null && <span className="pulse-legend-count">{counts[key]}</span>}
        </li>
      ))}
    </ul>
  );
}

function Histogram({
  activations,
  frame,
  loading,
}: {
  activations: readonly Activation[];
  frame: Timeframe;
  loading: boolean;
}) {
  const bins = binsFor(frame);
  const counts = binCounts(activations, frame, bins);
  const peak = Math.max(0, ...counts);
  const width = (frame.end - frame.start) / bins;
  const stretches = counts.map((count, index) => ({ at: frame.start + index * width, count }));

  return (
    <div
      className={`pulse-bars ${loading ? 'is-loading' : ''}`}
      role="img"
      aria-label={loading ? 'Loading' : `${activations.length} firings, at most ${peak} in one stretch`}
    >
      {loading && <span className="pulse-seek" />}
      {stretches.map(({ at, count }) => (
        <span
          key={at}
          className={`pulse-bar ${count === 0 ? 'is-empty' : ''}`}
          title={`${when(at)} · ${count}`}
          style={count === 0 ? undefined : { height: `${Math.max(10, (count / peak) * 100)}%` }}
        />
      ))}
    </div>
  );
}

function Flatline({ glyph, word, title, alarm = false }: { glyph: string; word: string; title?: string; alarm?: boolean }) {
  return (
    <div className={`pulse-flat ${alarm ? 'is-alarm' : ''}`} title={title}>
      <span className="pulse-flat-line" aria-hidden="true" />
      <p className="pulse-flat-word" role="status">
        <span className="pulse-flat-glyph" aria-hidden="true">
          {glyph}
        </span>
        {word}
      </p>
    </div>
  );
}

// One tab stop per lane: arrows walk its firings, so eighty-nine marks do not cost eighty-nine presses of Tab.
function walk(event: KeyboardEvent<HTMLDivElement>) {
  const marks = [...event.currentTarget.querySelectorAll<HTMLButtonElement>('.pulse-fire')];
  const at = marks.indexOf(document.activeElement as HTMLButtonElement);
  const steps: Record<string, number> = { ArrowLeft: at - 1, ArrowRight: at + 1, Home: 0, End: marks.length - 1 };

  if (at < 0 || !(event.key in steps)) {
    return;
  }

  event.preventDefault();
  // The variant switcher listens on the window for the same arrows.
  event.stopPropagation();

  const next = Math.min(marks.length - 1, Math.max(0, steps[event.key]));

  marks.forEach((mark, index) => {
    mark.tabIndex = index === next ? 0 : -1;
  });
  marks[next].focus();
}

function Lane({
  skill,
  firings,
  frame,
  onOpen,
  onFiring,
}: {
  skill: SkillSummary;
  firings: readonly Activation[];
  frame: Timeframe;
  onOpen: (skill: string) => void;
  onFiring: (id: string) => void;
}) {
  const inOrder = firings.toSorted((a, b) => a.timestampUtc.localeCompare(b.timestampUtc));

  return (
    <li className={`pulse-row pulse-lane ${skill.activations === 0 ? 'is-zero' : ''}`}>
      <button type="button" className="pulse-name" onClick={() => onOpen(skill.name)}>
        {skill.name}
      </button>

      <div
        className={`pulse-track ${inOrder.length === 0 ? 'is-empty' : ''}`}
        role="group"
        aria-label={`${skill.name} firings`}
        onKeyDown={walk}
      >
        {inOrder.map((activation, index) => {
          const at = positionIn(frame, activation.timestampUtc);
          const trigger = triggerOf(activation);
          const tip = `${when(activation.timestampUtc)} · ${words[trigger]}`;
          const edge = at > 0.85 ? 'tip-end' : at < 0.15 ? 'tip-start' : '';

          return (
            <button
              key={activation.id}
              type="button"
              tabIndex={index === 0 ? 0 : -1}
              className={`pulse-fire ${edge}`}
              style={{ left: percent(at) }}
              data-tip={tip}
              aria-label={`${tip} UTC`}
              onClick={() => onFiring(activation.id)}
            >
              <span className={`pulse-shape is-${shapes[trigger]}`} />
            </button>
          );
        })}
      </div>

      <span className="pulse-count">{skill.activations}</span>
      <span className="pulse-cost">{money(skill.spend?.cost ?? null)}</span>
    </li>
  );
}
