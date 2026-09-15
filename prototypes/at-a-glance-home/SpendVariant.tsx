// PROTOTYPE — throwaway.
// Variant D, Spend: money first. An amber tactical instrument rail beside a treemap whose tile area is cost.

import { useLayoutEffect, useRef, useState } from 'react';
import type { Activation } from '../../activations/api/activations';
import type { SkillSummary } from '../api/skills';
import {
  ago,
  binCounts,
  callSign,
  compact,
  countTriggers,
  dayLabels,
  firingsOf,
  lastFired,
  money,
  partMarks,
  signalOf,
  signalWords,
  spanChoices,
  timeframeOf,
  tokensIn,
  totalsOf,
  triggerKeys,
  triggerMarks,
  type Signal,
  type TriggerCounts,
} from './glance';
import type { Glance } from './useGlance';
import './SpendVariant.css';

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

type Tile =
  | {
      kind: 'skill';
      key: string;
      skill: SkillSummary;
      cost: number;
      perFiring: number;
      heat: number;
      triggers: TriggerCounts;
      last: string | null;
      spark: number[];
    }
  | { kind: 'unnamed'; key: string; cost: number; tokens: number };

type Placed = Rect & { tile: Tile };

function worst(areas: number[], side: number): number {
  const sum = areas.reduce((total, area) => total + area, 0);
  const max = Math.max(...areas);
  const min = Math.min(...areas);

  return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min));
}

function squarify(tiles: Tile[], width: number, height: number): Placed[] {
  const total = tiles.reduce((sum, tile) => sum + tile.cost, 0);

  if (total <= 0 || width <= 0 || height <= 0) {
    return [];
  }

  const scale = (width * height) / total;
  const queue = tiles.toSorted((a, b) => b.cost - a.cost).map((tile) => ({ tile, area: tile.cost * scale }));
  const placed: Placed[] = [];
  let free: Rect = { x: 0, y: 0, w: width, h: height };
  let row: typeof queue = [];

  const lay = () => {
    const sum = row.reduce((running, entry) => running + entry.area, 0);

    if (free.w >= free.h) {
      const w = sum / free.h;
      let y = free.y;

      for (const entry of row) {
        const h = entry.area / w;
        placed.push({ x: free.x, y, w, h, tile: entry.tile });
        y += h;
      }

      free = { x: free.x + w, y: free.y, w: free.w - w, h: free.h };
    } else {
      const h = sum / free.w;
      let x = free.x;

      for (const entry of row) {
        const w = entry.area / h;
        placed.push({ x, y: free.y, w, h, tile: entry.tile });
        x += w;
      }

      free = { x: free.x, y: free.y + h, w: free.w, h: free.h - h };
    }

    row = [];
  };

  for (const entry of queue) {
    const side = Math.min(free.w, free.h);
    const areas = row.map((queued) => queued.area);

    if (row.length > 0 && worst([...areas, entry.area], side) > worst(areas, side)) {
      lay();
    }

    row.push(entry);
  }

  if (row.length > 0) {
    lay();
  }

  return placed;
}

const signalGlyphs: Record<Signal, string> = {
  live: '●',
  offline: '✕',
  dark: '○',
  unsure: '?',
  quiet: '—',
  clipped: '◐',
};

const lampWords = { working: 'OK', starting: 'BOOT', off: 'OFF', broken: 'FAIL' } as const;

const shortModel = (model: string) => model.replace(/^claude-/, '').replace(/-\d{8}$/, '');

const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

const dayOf = (day: string) => {
  const moment = new Date(`${day}T00:00:00Z`);

  return `${String(moment.getUTCDate()).padStart(2, '0')} ${months[moment.getUTCMonth()]}`;
};

function heatLevel(heat: number): 1 | 2 | 3 {
  if (heat > 0.66) {
    return 3;
  }

  return heat > 0.33 ? 2 : 1;
}

function topTriggers(counts: TriggerCounts): { glyph: string; label: string; count: number }[] {
  return triggerKeys
    .filter((key) => counts[key] > 0)
    .toSorted((a, b) => counts[b] - counts[a])
    .map((key) => ({ ...triggerMarks[key], count: counts[key] }));
}

function HeroMoney({ amount }: { amount: number | null }) {
  if (amount === null) {
    return <>—</>;
  }

  const [whole, cents] = amount.toFixed(2).split('.');

  return (
    <>
      ${Number(whole).toLocaleString('en-US')}
      <span className="spend-cents">.{cents}</span>
    </>
  );
}

function Systems({ glance }: { glance: Glance }) {
  const { health, healthFailure, recheck } = glance;

  return (
    <section className="spend-block" aria-label="Systems">
      <div className="spend-head">
        <span className="spend-micro">Sys</span>
        <button type="button" className="spend-icon" onClick={recheck} aria-label="Check again" title="Check again">
          ↻
        </button>
      </div>

      <ul className="spend-lamps">
        {healthFailure !== null && (
          <li className="spend-lamp is-broken" title={healthFailure}>
            <span className="spend-lamp-glyph" aria-hidden="true">
              ✕
            </span>
            <span>API</span>
            <span className="spend-lamp-state">FAIL</span>
            <span className="spend-sr">{healthFailure}</span>
          </li>
        )}

        {health === null && healthFailure === null && (
          <li className="spend-lamp is-starting">
            <span className="spend-lamp-glyph" aria-hidden="true">
              ◌
            </span>
            <span>Scan</span>
            <span className="spend-lamp-state">…</span>
          </li>
        )}

        {health?.parts.map((part) => {
          const said = part.action === null ? part.detail : `${part.detail} ${part.action}`;

          return (
            <li key={part.name} className={`spend-lamp is-${part.state}`} title={said}>
              <span className="spend-lamp-glyph" aria-hidden="true">
                {partMarks[part.state].glyph}
              </span>
              <span>{callSign(part)}</span>
              <span className="spend-lamp-state" aria-hidden="true">
                {lampWords[part.state]}
              </span>
              <span className="spend-sr">
                {partMarks[part.state].label}. {said}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Power({ glance }: { glance: Glance }) {
  const { telemetry, flipTelemetry } = glance;
  const [confirming, setConfirming] = useState(false);
  const on = telemetry?.emitting ?? false;
  const unreadable = telemetry !== null && !telemetry.readable;

  const press = () => {
    if (on) {
      flipTelemetry(false);
    } else {
      setConfirming((open) => !open);
    }
  };

  return (
    <section className="spend-block spend-power" aria-label="Telemetry switch">
      <button
        type="button"
        className={`spend-switch${on ? ' is-on' : ''}`}
        aria-pressed={on}
        aria-label="Telemetry"
        disabled={telemetry === null || unreadable}
        title={unreadable ? (telemetry.problem ?? telemetry.settingsPath) : undefined}
        onClick={press}
      >
        <span className="spend-switch-glyph" aria-hidden="true">
          ⏻
        </span>
        <span className="spend-micro">Telemetry</span>
        <span className="spend-track" aria-hidden="true">
          <span className="spend-knob" />
        </span>
        <span className="spend-switch-state" aria-hidden="true">
          {telemetry === null ? '…' : unreadable ? '⚠' : on ? 'ON' : 'OFF'}
        </span>
      </button>

      {confirming && !on && telemetry !== null && (
        <div
          className="spend-confirm"
          role="dialog"
          aria-label="Turn telemetry on"
          onKeyDown={(event) => event.key === 'Escape' && setConfirming(false)}
        >
          <span className="spend-micro">Write</span>
          <code className="spend-path">{telemetry.settingsPath}</code>
          <ul className="spend-changes">
            {telemetry.changes.map((change) => (
              <li key={change.name}>
                <code>{change.name}</code> <span aria-label="becomes">→</span> <code>{change.to}</code>
              </li>
            ))}
          </ul>
          <div className="spend-confirm-keys">
            <button
              type="button"
              className="spend-key is-go"
              // oxlint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              onClick={() => {
                flipTelemetry(true);
                setConfirming(false);
              }}
            >
              ⏻ On
            </button>
            <button type="button" className="spend-key" aria-label="Cancel" onClick={() => setConfirming(false)}>
              ✕
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function SpanKeys({ glance }: { glance: Glance }) {
  return (
    <section className="spend-block" aria-label="Span">
      <div className="spend-head">
        <span className="spend-micro">Span</span>
      </div>

      <div className="spend-keys" role="group" aria-label="Span">
        {spanChoices.map((choice) => (
          <button
            key={choice.key}
            type="button"
            className="spend-key"
            aria-pressed={glance.span === choice.key}
            onClick={() => glance.chooseSpan(choice.key)}
          >
            <span className="spend-key-mark" aria-hidden="true">
              ▸
            </span>
            {choice.label}
          </button>
        ))}
      </div>

      {glance.span === 'custom' && glance.skills !== null && (
        <p className="spend-custom">
          {dayOf(glance.skills.span.from)} ▸ {dayOf(glance.skills.span.to)}
        </p>
      )}
    </section>
  );
}

function Readout({ placed, width, height }: { placed: Placed; width: number; height: number }) {
  const panelWidth = 232;
  const panelHeight = 176;
  const { tile } = placed;

  if (tile.kind !== 'skill') {
    return null;
  }

  let left = placed.x + placed.w + 8;

  if (left + panelWidth > width) {
    left = placed.x - panelWidth - 8;
  }

  if (left < 0) {
    left = Math.max(0, Math.min(width - panelWidth, placed.x + placed.w / 2 - panelWidth / 2));
  }

  const top = Math.max(0, Math.min(height - panelHeight, placed.y));
  const { skill } = tile;

  return (
    <div className="spend-readout" style={{ left, top, width: panelWidth }} aria-hidden="true">
      <div className="spend-readout-name">{skill.name}</div>
      <dl>
        <dt>$/firing</dt>
        <dd>{money(tile.perFiring)}</dd>
        <dt>Tokens</dt>
        <dd>{compact(tokensIn(skill.spend))}</dd>
        <dt>Model</dt>
        <dd>{skill.models === null ? '?' : skill.models.map(shortModel).join(' ') || '—'}</dd>
        <dt>Effort</dt>
        <dd>{skill.efforts === null ? '?' : skill.efforts.join(' ') || '—'}</dd>
        <dt>Last</dt>
        <dd>{tile.last === null ? '—' : ago(tile.last)}</dd>
        <dt>Via</dt>
        <dd>
          {topTriggers(tile.triggers)
            .map((trigger) => `${trigger.glyph}${trigger.count}`)
            .join(' ') || '—'}
        </dd>
      </dl>
    </div>
  );
}

export function SpendVariant({ glance }: { glance: Glance }) {
  const { skills, skillsError, activations } = glance;
  const list = skills?.skills ?? [];
  const firings: Activation[] = activations?.activations ?? [];
  const signal = skills === null ? null : signalOf(skills.gap.kind);
  const totals = totalsOf(list);
  const unnamed = skills?.unnamedSpend ?? null;
  const unnamedCost = unnamed !== null && unnamed.cost > 0 ? unnamed.cost : 0;

  const mapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [probe, setProbe] = useState<string | null>(null);

  useLayoutEffect(() => {
    const map = mapRef.current;

    if (map === null) {
      return;
    }

    const observer = new ResizeObserver(([entry]) => {
      setSize({ w: entry.contentRect.width, h: entry.contentRect.height });
    });

    observer.observe(map);

    return () => observer.disconnect();
  }, []);

  const priced = list.filter((skill) => skill.spend !== null && skill.spend.cost > 0);
  const unpriced = list.filter((skill) => skill.spend === null || skill.spend.cost <= 0);
  const perFirings = priced.map((skill) => (skill.spend?.cost ?? 0) / Math.max(1, skill.activations));
  const maxPer = Math.max(0, ...perFirings);
  const minPer = perFirings.length === 0 ? 0 : Math.min(...perFirings);

  const frame = skills === null ? null : timeframeOf(skills.span);
  const bins = frame === null ? 0 : frame.days <= 1 ? 24 : frame.days <= 7 ? frame.days * 4 : frame.days;
  const sparks = new Map(priced.map((skill) => [skill.name, frame === null ? [] : binCounts(firingsOf(firings, skill.name), frame, bins)]));
  const sparkMax = Math.max(1, ...[...sparks.values()].flat());
  const daily = frame === null ? [] : binCounts(firings, frame, frame.days);
  const dailyMax = Math.max(1, ...daily);
  const days = frame === null ? [] : dayLabels(frame);

  const tiles: Tile[] = priced.map((skill, index) => ({
    kind: 'skill',
    key: skill.name,
    skill,
    cost: skill.spend?.cost ?? 0,
    perFiring: perFirings[index],
    heat: maxPer === 0 ? 0 : perFirings[index] / maxPer,
    triggers: countTriggers(firingsOf(firings, skill.name)),
    last: lastFired(firings, skill.name),
    spark: sparks.get(skill.name) ?? [],
  }));

  if (unnamed !== null && unnamedCost > 0) {
    tiles.push({ kind: 'unnamed', key: '∅unnamed', cost: unnamedCost, tokens: tokensIn(unnamed) });
  }

  const placed = squarify(tiles, size.w, size.h);
  const probed = placed.find((entry) => entry.tile.key === probe) ?? null;

  // An unreadable store is missing numbers, not zero ones.
  const unknown = skills === null || (list.length === 0 && (signal === 'offline' || signal === 'unsure'));
  const allCost = unknown ? null : totals.cost + unnamedCost;
  const allTokens = totals.tokens + (unnamed === null ? 0 : tokensIn(unnamed));

  let panel: { glyph: string; word: string; tone: string; note?: string; busy?: boolean } | null = null;

  if (skills === null && skillsError !== null) {
    panel = { glyph: '✕', word: 'No link', tone: 'red', note: skillsError };
  } else if (skills === null) {
    panel = { glyph: '◌', word: 'Acquiring', tone: 'hud', busy: true };
  } else if (list.length === 0 && signal === 'offline') {
    panel = { glyph: '✕', word: 'No signal', tone: 'red' };
  } else if (list.length === 0) {
    panel = { glyph: '—', word: signal === 'quiet' ? 'Quiet' : signal === 'dark' ? 'Telemetry off' : 'Nothing', tone: 'dim' };
  } else if (tiles.length === 0) {
    panel = { glyph: '$0', word: 'Free', tone: 'dim' };
  }

  return (
    <div className="spend">
      <aside className="spend-rail" aria-label="Instruments">
        <div className="spend-brand">
          <span className="spend-brand-mark" aria-hidden="true">
            ◢
          </span>
          <h1>Skillworks</h1>
        </div>

        <Systems glance={glance} />
        <Power glance={glance} />
        <SpanKeys glance={glance} />

        <section className="spend-block spend-totals-block" aria-label="Totals">
          <dl className="spend-totals">
            <div className="spend-total is-hero">
              <dt className="spend-micro">Cost</dt>
              <dd>
                <HeroMoney amount={allCost} />
              </dd>
            </div>
            <div className="spend-total">
              <dt className="spend-micro">Firings</dt>
              <dd>{unknown ? '—' : totals.firings}</dd>
            </div>
            <div className="spend-total">
              <dt className="spend-micro">Tokens</dt>
              <dd>{unknown ? '—' : compact(allTokens)}</dd>
            </div>
            <div className="spend-total">
              <dt className="spend-micro">$/Firing</dt>
              <dd>{unknown || totals.firings === 0 ? '—' : money(totals.cost / totals.firings)}</dd>
            </div>
          </dl>

          {daily.length > 0 && firings.length > 0 && (
            <figure className="spend-daily" aria-label={`Firings per day: ${daily.join(', ')}`}>
              <figcaption className="spend-micro">Firings / day</figcaption>
              <div className="spend-daily-bars" aria-hidden="true">
                {daily.map((count, day) => (
                  <div key={day} className="spend-daily-day" title={`${days[day]} ×${count}`}>
                    <span className="spend-daily-count">{daily.length <= 7 ? count : ''}</span>
                    <span className="spend-daily-track">
                      <i style={{ height: `${(count / dailyMax) * 100}%` }} />
                    </span>
                    <span className="spend-daily-label">{daily.length <= 7 ? days[day].slice(0, 2) : ''}</span>
                  </div>
                ))}
              </div>
            </figure>
          )}
        </section>
      </aside>

      <section className="spend-deck" aria-label="Spend by skill">
        <header className="spend-deck-head">
          {signal !== null && skills !== null && (
            <span className={`spend-signal is-${signal}`} title={skills.gap.missing ?? undefined}>
              <span aria-hidden="true">{signalGlyphs[signal]}</span> {signalWords[signal]}
              {skills.gap.missing !== null && <span className="spend-sr">. {skills.gap.missing}</span>}
            </span>
          )}

          {tiles.length > 0 && (
            <span className="spend-legend" aria-label={`Heat is cost per firing, ${money(minPer)} to ${money(maxPer)}`}>
              <span className="spend-micro">$/firing</span>
              <span className="spend-legend-value">{money(minPer)}</span>
              <span className="spend-legend-bar" />
              <span className="spend-legend-value">{money(maxPer)}</span>
            </span>
          )}

          {skills !== null && (
            <span className="spend-range">
              {dayOf(skills.span.from)} <span aria-hidden="true">▸</span>
              <span className="spend-sr">to</span> {dayOf(skills.span.to)}
            </span>
          )}
        </header>

        <div className="spend-frame">
          <span className="spend-corner is-tl" aria-hidden="true" />
          <span className="spend-corner is-tr" aria-hidden="true" />
          <span className="spend-corner is-bl" aria-hidden="true" />
          <span className="spend-corner is-br" aria-hidden="true" />

          <div className="spend-map" ref={mapRef}>
            {panel !== null && (
              <div
                className={`spend-panel is-${panel.tone}${panel.busy ? ' is-busy' : ''}`}
                role="status"
                title={skills?.gap.missing ?? undefined}
              >
                <div className="spend-panel-box">
                  <span className="spend-panel-glyph" aria-hidden="true">
                    {panel.glyph}
                  </span>
                  <span className="spend-panel-word">{panel.word}</span>
                  {panel.note !== undefined && <code className="spend-panel-note">{panel.note}</code>}
                  {skills?.gap.missing && <span className="spend-sr">{skills.gap.missing}</span>}
                </div>
              </div>
            )}

            {panel === null &&
              placed.map(({ x, y, w, h, tile }) => {
                const style = { left: x, top: y, width: w, height: h };

                if (tile.kind === 'unnamed') {
                  return (
                    <div
                      key={tile.key}
                      className="spend-tile is-unnamed"
                      style={style}
                      role="img"
                      aria-label={`Unnamed spend ${money(tile.cost)}`}
                      title="Spend from plugins outside Anthropic’s marketplaces. Claude Code does not name the skill."
                    >
                      <span className="spend-skin" aria-hidden="true">
                        <span className="spend-tile-top">
                          <span className="spend-tile-name is-unnamed">Unnamed</span>
                          <span className="spend-unnamed-glyph">∅</span>
                        </span>
                        <span className="spend-tile-cost">{money(tile.cost)}</span>
                        <span className="spend-tile-foot">
                          <span className="spend-tile-count">{compact(tile.tokens)} tok</span>
                        </span>
                      </span>
                    </div>
                  );
                }

                const { skill } = tile;
                const level = heatLevel(tile.heat);
                const triggers = topTriggers(tile.triggers);

                return (
                  <button
                    key={tile.key}
                    type="button"
                    className={`spend-tile is-heat-${level}${probe === tile.key ? ' is-probed' : ''}`}
                    style={{ ...style, ['--heat' as string]: tile.heat.toFixed(3) }}
                    aria-label={`${skill.name}: ${money(tile.cost)}, ${skill.activations} firings, ${money(tile.perFiring)} per firing`}
                    onClick={() => glance.openSkill(skill.name)}
                    onMouseEnter={() => setProbe(tile.key)}
                    onMouseLeave={() => setProbe((current) => (current === tile.key ? null : current))}
                    onFocus={() => setProbe(tile.key)}
                    onBlur={() => setProbe((current) => (current === tile.key ? null : current))}
                  >
                    <span className="spend-skin" aria-hidden="true">
                      <span className="spend-tile-top">
                        <span className="spend-tile-name">{skill.name}</span>
                        <span className="spend-heat" data-level={level}>
                          <i />
                          <i />
                          <i />
                        </span>
                      </span>
                      <span className="spend-tile-cost">{money(tile.cost)}</span>
                      {tile.spark.some((count) => count > 0) && (
                        <span className="spend-spark">
                          {tile.spark.map((count, bin) => (
                            <i key={bin} style={{ height: `${(count / sparkMax) * 100}%` }} data-lit={count > 0 || undefined} />
                          ))}
                        </span>
                      )}
                      {tile.spark.some((count) => count > 0) && days.length > 0 && (
                        <span className="spend-spark-axis">
                          <span>{days[0].slice(0, 2)}</span>
                          <span>{days[days.length - 1].slice(0, 2)}</span>
                        </span>
                      )}
                      <span className="spend-tile-foot">
                        <span className="spend-tile-count">×{skill.activations}</span>
                        <span className="spend-pips">
                          {Array.from({ length: Math.min(skill.activations, 40) }, (_, pip) => (
                            <i key={pip} />
                          ))}
                        </span>
                        <span className="spend-tile-trig">
                          {triggers.slice(0, 2).map((trigger) => (
                            <span key={trigger.glyph} title={trigger.label}>
                              {trigger.glyph}
                              {trigger.count}
                            </span>
                          ))}
                        </span>
                      </span>
                    </span>
                  </button>
                );
              })}

            {panel === null && probed !== null && <Readout placed={probed} width={size.w} height={size.h} />}
          </div>
        </div>

        {skills !== null && unpriced.length > 0 && (
          <div className="spend-strip" role="group" aria-label="No cost">
            <span className="spend-strip-label">
              <span aria-hidden="true">$0</span> <span className="spend-micro">Free</span>
            </span>
            {unpriced.map((skill) => (
              <button
                key={skill.name}
                type="button"
                className="spend-chip"
                aria-label={`${skill.name}: ${skill.spend === null ? 'cost not named' : 'no cost'}, ${skill.activations} firings`}
                onClick={() => glance.openSkill(skill.name)}
              >
                {skill.name}
                <span className="spend-chip-count" aria-hidden="true">
                  ×{skill.activations}
                  {skill.spend === null && ' ?'}
                </span>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
