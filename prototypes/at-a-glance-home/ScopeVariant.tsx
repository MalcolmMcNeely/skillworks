// PROTOTYPE — throwaway. Variant B, Scope: every skill a bubble on a phosphor CRT, sized by firings, ringed by cost.

import { useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import type { Activation } from '../../activations/api/activations';
import type { Part, PartState } from '../../health/lib/health';
import type { SkillSummary } from '../api/skills';
import {
  ago,
  callSign,
  compact,
  countTriggers,
  firingsOf,
  lastFired,
  money,
  partMarks,
  signalOf,
  signalWords,
  spanChoices,
  tokensIn,
  totalsOf,
  triggerKeys,
  triggerMarks,
  type Signal,
  type TriggerKey,
} from './glance';
import type { Glance } from './useGlance';
import './ScopeVariant.css';

const labelGap = 22;
const charWidth = 6.8;
const hotWindowMs = 3 * 60 * 60 * 1000;
const telemetryPart = 'Claude Code telemetry';

const signalGlyphs: Record<Signal, string> = {
  live: '●',
  offline: '✕',
  dark: '○',
  unsure: '◌',
  quiet: '·',
  clipped: '◐',
};

const triggerWords: Record<TriggerKey, string> = {
  'claude-proactive': 'Claude',
  'user-slash': 'Typed',
  'nested-skill': 'Skill',
  'agent-preload': 'Agent',
  unknown: '?',
};

const spanNames: Record<string, string> = {
  '1d': 'Last 24 hours',
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
};

interface Bubble {
  skill: SkillSummary;
  r: number;
  x: number;
  y: number;
}

function labelHalf(name: string): number {
  return (name.length * charWidth) / 2 + 4;
}

// The name hangs under the circle, so a bubble claims a circle wide enough to hold its label too.
function reachOf(r: number, name: string): number {
  return Math.max(r + 8, Math.hypot(labelHalf(name), r + labelGap));
}

function pack(skills: readonly SkillSummary[], rMax: number, rMin: number, aspect: number): Bubble[] {
  const busiest = Math.max(1, ...skills.map((skill) => skill.activations));
  const items = skills
    .map((skill) => ({
      skill,
      r: skill.activations === 0 ? rMin * 0.8 : Math.max(rMin, Math.sqrt(skill.activations / busiest) * rMax),
    }))
    .toSorted((a, b) => b.r - a.r || a.skill.name.localeCompare(b.skill.name));

  const placed: (Bubble & { reach: number })[] = [];
  const gap = 6;
  const steps = 72;

  for (const item of items) {
    const reach = reachOf(item.r, item.skill.name);

    if (placed.length === 0) {
      placed.push({ ...item, x: 0, y: 0, reach });
      continue;
    }

    let best = { x: 0, y: 0, score: Number.POSITIVE_INFINITY };

    for (const anchor of placed) {
      const distance = anchor.reach + reach + gap;

      for (let step = 0; step < steps; step++) {
        const angle = (step / steps) * Math.PI * 2;
        const x = anchor.x + Math.cos(angle) * distance;
        const y = anchor.y + Math.sin(angle) * distance;
        // Stretched by the field's aspect, so a wide screen gets a wide cluster rather than a ball.
        const score = (x / aspect) ** 2 + y ** 2;

        if (score < best.score && placed.every((other) => Math.hypot(other.x - x, other.y - y) >= other.reach + reach + gap - 0.01)) {
          best = { x, y, score };
        }
      }
    }

    placed.push({ ...item, x: best.x, y: best.y, reach });
  }

  return placed;
}

function boundsOf(bubbles: readonly Bubble[]) {
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  for (const bubble of bubbles) {
    const half = Math.max(bubble.r, labelHalf(bubble.skill.name));
    minX = Math.min(minX, bubble.x - half);
    maxX = Math.max(maxX, bubble.x + half);
    minY = Math.min(minY, bubble.y - bubble.r);
    maxY = Math.max(maxY, bubble.y + bubble.r + labelGap);
  }

  return { minX, minY, w: maxX - minX, h: maxY - minY };
}

function arrange(skills: readonly SkillSummary[], width: number, height: number): Bubble[] {
  if (skills.length === 0 || width <= 0 || height <= 0) {
    return [];
  }

  const rMin = width < 560 ? 15 : 22;
  const aspect = Math.max(0.6, Math.min(2.4, width / height));
  const fits = (bubbles: Bubble[]) => {
    const box = boundsOf(bubbles);
    return box.w <= width && box.h <= height;
  };

  let low = rMin;
  let high = Math.min(170, Math.min(width, height) * 0.42);
  let chosen = pack(skills, low, rMin, aspect);

  if (fits(chosen)) {
    for (let round = 0; round < 14; round++) {
      const middle = (low + high) / 2;
      const bubbles = pack(skills, middle, rMin, aspect);

      if (fits(bubbles)) {
        low = middle;
        chosen = bubbles;
      } else {
        high = middle;
      }
    }
  }

  const box = boundsOf(chosen);
  const offsetX = (width - box.w) / 2 - box.minX;
  const offsetY = (height - box.h) / 2 - box.minY;

  return chosen.map((bubble) => ({ ...bubble, x: bubble.x + offsetX, y: bubble.y + offsetY }));
}

function firedLately(timestampUtc: string): boolean {
  return Date.now() - Date.parse(timestampUtc) < hotWindowMs;
}

function shortModel(model: string): string {
  return model.replace(/^claude-/, '').replace(/-\d{8}$/, '');
}

function listed(values: readonly string[] | null, shorten = (value: string) => value): string {
  return values === null || values.length === 0 ? '—' : values.map(shorten).join(' ');
}

function useSize() {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
    const element = ref.current;

    if (element === null) {
      return;
    }

    const observer = new ResizeObserver(([entry]) => {
      setSize({ width: Math.round(entry.contentRect.width), height: Math.round(entry.contentRect.height) });
    });

    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  return [ref, size] as const;
}

export function ScopeVariant({ glance }: { glance: Glance }) {
  const answer = glance.skills;
  const skills = answer?.skills ?? [];
  const signal = answer === null ? null : signalOf(answer.gap.kind);
  const totals = totalsOf(skills);
  const firings = glance.activations?.activations ?? null;
  const blank = answer === null || signal === 'offline' || skills.length === 0;
  const unnamed = answer?.unnamedSpend ?? null;

  return (
    <div className="scope">
      <div className="scope-scan" aria-hidden="true" />

      <header className="scope-top">
        <div>
          <h1 className="scope-brand">
            Skillworks<span className="scope-cursor" aria-hidden="true">▮</span>
          </h1>

          <dl className="scope-totals">
            <div>
              <dt>Firings</dt>
              <dd>{blank ? '—' : totals.firings}</dd>
            </div>
            <div>
              <dt>Cost</dt>
              <dd>{blank ? '—' : money(totals.cost)}</dd>
            </div>
            <div>
              <dt>Tokens</dt>
              <dd>{blank ? '—' : compact(totals.tokens)}</dd>
            </div>
            <div>
              <dt>Skills</dt>
              <dd>{blank ? '—' : totals.skills}</dd>
            </div>
          </dl>
        </div>

        <div className="scope-top-right">
          <div className="scope-span" role="group" aria-label="Span">
            {spanChoices.map((choice) => (
              <button
                key={choice.key}
                type="button"
                className="scope-key"
                aria-pressed={glance.span === choice.key}
                aria-label={spanNames[choice.key]}
                onClick={() => glance.chooseSpan(choice.key)}
              >
                {choice.label}
              </button>
            ))}
          </div>

          {glance.span === 'custom' && answer !== null && (
            <p className="scope-custom">
              {answer.span.from} → {answer.span.to}
            </p>
          )}

          {signal !== null && (
            <p className={`scope-signal is-${signal}`} title={answer?.gap.missing ?? undefined}>
              <span aria-hidden="true">{signalGlyphs[signal]}</span> {signalWords[signal]}
              {answer?.gap.missing && <span className="scope-vh">. {answer.gap.missing}</span>}
            </p>
          )}
        </div>
      </header>

      <section className="scope-stage" aria-label="Skills">
        <Stage glance={glance} signal={signal} skills={skills} firings={firings} totalCost={totals.cost} />
      </section>

      <footer className="scope-bottom">
        <Systems glance={glance} />

        {!blank && <Legend firings={firings} />}

        <div className="scope-unnamed-slot">
          {unnamed !== null && unnamed.cost > 0 && (
            <p className="scope-unnamed" title="Spend Claude Code will not name to a skill">
              <span className="scope-unnamed-mark" aria-hidden="true">
                ?
              </span>
              <span className="scope-micro">Unnamed</span>
              <span className="scope-unnamed-cost">{money(unnamed.cost)}</span>
            </p>
          )}
        </div>
      </footer>
    </div>
  );
}

function Stage({
  glance,
  signal,
  skills,
  firings,
  totalCost,
}: {
  glance: Glance;
  signal: Signal | null;
  skills: SkillSummary[];
  firings: Activation[] | null;
  totalCost: number;
}) {
  if (glance.skillsError !== null) {
    return (
      <div className="scope-center is-alarm" role="status" title={glance.skillsError}>
        <p className="scope-big scope-flicker">No link</p>
        <p className="scope-micro">API</p>
        <span className="scope-vh">{glance.skillsError}</span>
      </div>
    );
  }

  if (glance.skills === null) {
    return (
      <div className="scope-center" role="status">
        <p className="scope-big">
          Scanning<span className="scope-cursor" aria-hidden="true">▮</span>
        </p>
      </div>
    );
  }

  if (signal === 'offline') {
    return (
      <div className="scope-center is-alarm" role="status" title={glance.skills.gap.missing ?? undefined}>
        <p className="scope-big scope-flicker">No signal</p>
        <p className="scope-micro">Store</p>
      </div>
    );
  }

  if (skills.length === 0) {
    return (
      <div className="scope-center is-quiet" role="status" title={glance.skills.gap.missing ?? undefined}>
        <p className="scope-big">No firings</p>
        <div className="scope-flatline" aria-hidden="true" />
      </div>
    );
  }

  return <Field skills={skills} firings={firings} totalCost={totalCost} onOpen={glance.openSkill} />;
}

function Field({
  skills,
  firings,
  totalCost,
  onOpen,
}: {
  skills: SkillSummary[];
  firings: Activation[] | null;
  totalCost: number;
  onOpen: (skill: string) => void;
}) {
  const [ref, { width, height }] = useSize();
  const bubbles = useMemo(() => arrange(skills, width, height), [skills, width, height]);
  const [focused, setFocused] = useState<string | null>(null);
  const shown = bubbles.find((bubble) => bubble.skill.name === focused) ?? null;

  return (
    <div className="scope-field" ref={ref}>
      {bubbles.map((bubble) => {
        const { skill, r } = bubble;
        const cost = skill.spend?.cost ?? 0;
        const share = totalCost > 0 ? cost / totalCost : 0;
        const own = firings === null ? [] : firingsOf(firings, skill.name);
        const counts = countTriggers(own);
        const latest = lastFired(own, skill.name);
        const hot = latest !== null && firedLately(latest);
        const ringRadius = r - 3;
        const circumference = 2 * Math.PI * ringRadius;
        // A cost too small to see still gets a dot, so "cheap" never reads as "free".
        const arc = cost > 0 ? Math.max(2, share * circumference) : 0;
        const style = {
          left: bubble.x - r,
          top: bubble.y - r,
          width: r * 2,
          height: r * 2,
          '--scope-count-size': `${Math.max(12, Math.min(56, r * 0.6))}px`,
        } as CSSProperties;

        return (
          <button
            key={skill.name}
            type="button"
            className={`scope-bubble${skill.activations === 0 ? ' is-zero' : ''}${focused === skill.name ? ' is-focus' : ''}`}
            style={style}
            aria-label={`${skill.name}: ${skill.activations} firings, ${money(skill.spend?.cost)}, ${Math.round(share * 100)}% of cost${
              latest === null ? '' : `, last ${ago(latest)} ago`
            }`}
            onClick={() => onOpen(skill.name)}
            onMouseEnter={() => setFocused(skill.name)}
            onMouseLeave={() => setFocused((current) => (current === skill.name ? null : current))}
            onFocus={() => setFocused(skill.name)}
            onBlur={() => setFocused((current) => (current === skill.name ? null : current))}
          >
            <svg className="scope-ring" width={r * 2} height={r * 2} viewBox={`0 0 ${r * 2} ${r * 2}`} aria-hidden="true">
              <circle className="scope-ring-track" cx={r} cy={r} r={ringRadius} />
              {arc > 0 && (
                <circle
                  className="scope-ring-arc"
                  cx={r}
                  cy={r}
                  r={ringRadius}
                  strokeDasharray={`${arc} ${circumference}`}
                  transform={`rotate(-90 ${r} ${r})`}
                />
              )}
            </svg>

            {hot && <span className="scope-hot" aria-hidden="true" />}

            <span className="scope-count" aria-hidden="true">
              {skill.activations}
            </span>

            {r >= 38 && (
              <span className="scope-pips" aria-hidden="true">
                {triggerKeys
                  .filter((key) => counts[key] > 0)
                  .map((key) => (
                    <span key={key}>
                      <span className="scope-pip-glyph">{triggerMarks[key].glyph}</span>
                      {counts[key]}
                    </span>
                  ))}
              </span>
            )}

            {r >= 64 && (
              <span className="scope-cost" aria-hidden="true">
                {money(skill.spend?.cost)}
              </span>
            )}

            <span className="scope-name" aria-hidden="true">
              {skill.name}
            </span>
          </button>
        );
      })}

      {shown !== null && (
        <Readout
          bubble={shown}
          width={width}
          height={height}
          firings={firings === null ? null : firingsOf(firings, shown.skill.name)}
          totalCost={totalCost}
        />
      )}
    </div>
  );
}

function Readout({
  bubble,
  width,
  height,
  firings,
  totalCost,
}: {
  bubble: Bubble;
  width: number;
  height: number;
  firings: Activation[] | null;
  totalCost: number;
}) {
  const { skill, x, y, r } = bubble;
  const boxWidth = 240;
  const boxHeight = 215;
  const reach = Math.max(r, labelHalf(skill.name)) + 16;
  const fitsRight = x + reach + boxWidth <= width;
  const fitsLeft = x - reach - boxWidth >= 0;
  const clampTop = (top: number) => Math.max(0, Math.min(height - boxHeight, top));

  let left: number;
  let top: number;

  if (fitsRight || fitsLeft) {
    left = fitsRight ? x + reach : x - reach - boxWidth;
    top = clampTop(y - boxHeight / 2);
  } else {
    left = Math.max(0, Math.min(width - boxWidth, x - boxWidth / 2));
    top = y + r + labelGap + boxHeight + 8 <= height ? y + r + labelGap + 8 : Math.max(0, y - r - boxHeight - 8);
  }

  const cost = skill.spend?.cost ?? 0;
  const counts = firings === null ? null : countTriggers(firings);
  const latest = firings === null ? null : lastFired(firings, skill.name);

  return (
    <div className="scope-readout" style={{ left, top, width: boxWidth }} aria-hidden="true">
      <p className="scope-readout-name">{skill.name}</p>

      <dl>
        <dt>Fired</dt>
        <dd>{skill.activations}</dd>
        <dt>Last</dt>
        <dd>{latest === null ? '—' : ago(latest)}</dd>
        <dt>Cost</dt>
        <dd>
          {money(skill.spend?.cost)}
          <span className="scope-readout-share"> {totalCost > 0 ? Math.round((cost / totalCost) * 100) : 0}%</span>
        </dd>
        <dt>Each</dt>
        <dd>{money(skill.averageCost)}</dd>
        <dt>Tokens</dt>
        <dd>{skill.spend === null ? '—' : compact(tokensIn(skill.spend))}</dd>
        <dt>Model</dt>
        <dd>{listed(skill.models, shortModel)}</dd>
        <dt>Effort</dt>
        <dd>{listed(skill.efforts)}</dd>
      </dl>

      {counts !== null && (
        <p className="scope-readout-triggers">
          {triggerKeys
            .filter((key) => counts[key] > 0)
            .map((key) => (
              <span key={key}>
                <span className="scope-pip-glyph">{triggerMarks[key].glyph}</span>
                {counts[key]} {triggerWords[key]}
              </span>
            ))}
        </p>
      )}
    </div>
  );
}

function Legend({ firings }: { firings: Activation[] | null }) {
  const counts = firings === null ? null : countTriggers(firings);

  return (
    <ul className="scope-legend" aria-label="Key">
      <li>
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
          <circle cx="8" cy="8" r="6.5" className="scope-legend-body" />
          <text x="8" y="11.2" textAnchor="middle" className="scope-legend-digit">
            9
          </text>
        </svg>
        Firings
      </li>
      <li>
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
          <circle cx="8" cy="8" r="6" className="scope-legend-track" />
          <circle
            cx="8"
            cy="8"
            r="6"
            className="scope-legend-arc"
            strokeDasharray={`${2 * Math.PI * 6 * 0.35} 100`}
            transform="rotate(-90 8 8)"
          />
        </svg>
        Cost
      </li>
      {counts !== null &&
        triggerKeys
          .filter((key) => counts[key] > 0)
          .map((key) => (
            <li key={key} title={triggerMarks[key].label}>
              <span className="scope-pip-glyph" aria-hidden="true">
                {triggerMarks[key].glyph}
              </span>
              {triggerWords[key]}
            </li>
          ))}
    </ul>
  );
}

function Systems({ glance }: { glance: Glance }) {
  const { health, healthFailure, recheck, telemetry, flipTelemetry } = glance;
  const [asking, setAsking] = useState(false);
  const write = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (asking) {
      write.current?.focus();
    }
  }, [asking]);

  // The switch is the fresher reading, so the lamp follows it rather than the last health check.
  const stateOf = (part: Part): PartState =>
    part.name === telemetryPart && telemetry !== null ? (telemetry.emitting ? 'working' : 'off') : part.state;

  const power =
    telemetry === null ? null : (
      <button
        type="button"
        className="scope-power"
        aria-pressed={telemetry.emitting}
        aria-label={telemetry.emitting ? 'Turn telemetry off' : 'Turn telemetry on'}
        title={telemetry.readable ? undefined : (telemetry.problem ?? undefined)}
        disabled={!telemetry.readable}
        onClick={() => (telemetry.emitting ? flipTelemetry(false) : setAsking(true))}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
          <path d="M4.2 3.4a4.8 4.8 0 1 0 5.6 0" />
          <path d="M7 1.2v5.4" />
        </svg>
      </button>
    );

  const hasTelemetryPart = health?.parts.some((part) => part.name === telemetryPart) ?? false;

  return (
    <div className="scope-systems">
      {asking && telemetry !== null && (
        <div
          className="scope-confirm"
          role="dialog"
          aria-label="Turn telemetry on"
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              setAsking(false);
            }
          }}
        >
          <p className="scope-micro">Write</p>
          <p className="scope-path">{telemetry.settingsPath}</p>
          <ul className="scope-changes">
            {telemetry.changes.map((change) => (
              <li key={change.name}>
                {change.name}
                <span aria-hidden="true"> → </span>
                <span className="scope-vh"> to </span>
                <span className="scope-change-to">{change.to}</span>
              </li>
            ))}
          </ul>
          <p className="scope-micro" title={telemetry.restartNote}>
            <span aria-hidden="true">↻ </span>Restart Claude
          </p>
          <div className="scope-confirm-actions">
            <button
              ref={write}
              type="button"
              className="scope-key is-go"
              onClick={() => {
                flipTelemetry(true);
                setAsking(false);
              }}
            >
              Write
            </button>
            <button type="button" className="scope-key" onClick={() => setAsking(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <ul className="scope-lamps" aria-label="Systems">
        {health === null && healthFailure === null && (
          <li className="scope-lamp is-starting">
            <span className="scope-lamp-glyph" aria-hidden="true">
              ◌
            </span>
            Systems
          </li>
        )}

        {healthFailure !== null && (
          <li className="scope-lamp is-broken" title={healthFailure}>
            <span className="scope-lamp-glyph" aria-hidden="true">
              ✕
            </span>
            API
            <span className="scope-vh">: {healthFailure}</span>
          </li>
        )}

        {health?.parts.map((part) => {
          const state = stateOf(part);
          const detail = [part.detail, part.action].filter(Boolean).join(' ');

          return (
            <li key={part.name} className={`scope-lamp is-${state}`} title={detail}>
              <span className="scope-lamp-glyph" aria-hidden="true">
                {partMarks[state].glyph}
              </span>
              {callSign(part)}
              <span className="scope-vh">
                : {partMarks[state].label}. {detail}
              </span>
              {part.name === telemetryPart && power}
            </li>
          );
        })}

        {!hasTelemetryPart && power !== null && <li className="scope-lamp">{power}</li>}
      </ul>

      <button type="button" className="scope-power" aria-label="Check systems again" title="Check again" onClick={recheck}>
        <span aria-hidden="true">↻</span>
      </button>
    </div>
  );
}
