// PROTOTYPE — throwaway.
// Variant E, Map: D's instrument rail and treemap, in A's cyan HUD, with A's trace across the top. Round two.

import { useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react';
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
  tokensIn,
  totalsOf,
  triggerKeys,
  triggerMarks,
  type Signal,
  type Timeframe,
  type TriggerCounts,
} from './glance';
import type { Glance } from './useGlance';
import './MapVariant.css';

type Measure = 'spend' | 'usage';
type Order = 'most' | 'least';

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
      value: number;
      cost: number;
      perFiring: number;
      heat: number;
      triggers: TriggerCounts;
      last: string | null;
      spark: number[];
    }
  | { kind: 'unnamed'; key: string; value: number; cost: number; tokens: number };

type Placed = Rect & { tile: Tile; rank: number };

// Every tile gets at least this share of the map, so "least first" still has something to read.
const floorShare = 0.02;

function worst(areas: number[], side: number): number {
  const sum = areas.reduce((total, area) => total + area, 0);

  return Math.max((side * side * Math.max(...areas)) / (sum * sum), (sum * sum) / (side * side * Math.min(...areas)));
}

// Squarified, but in the order given rather than largest first, so the order control decides what sits top-left.
function squarify(tiles: Tile[], width: number, height: number): Placed[] {
  const total = tiles.reduce((sum, tile) => sum + tile.value, 0);

  if (total <= 0 || width <= 0 || height <= 0) {
    return [];
  }

  const floor = total * floorShare;
  const weights = tiles.map((tile) => Math.max(tile.value, floor));
  const scale = (width * height) / weights.reduce((sum, weight) => sum + weight, 0);
  const queue = tiles.map((tile, index) => ({ tile, rank: index + 1, area: weights[index] * scale }));
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
        placed.push({ x: free.x, y, w, h, tile: entry.tile, rank: entry.rank });
        y += h;
      }

      free = { x: free.x + w, y: free.y, w: free.w - w, h: free.h };
    } else {
      const h = sum / free.w;
      let x = free.x;

      for (const entry of row) {
        const w = entry.area / h;
        placed.push({ x, y: free.y, w, h, tile: entry.tile, rank: entry.rank });
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

const perFiring = (skill: SkillSummary) => (skill.spend?.cost ?? 0) / Math.max(1, skill.activations);

const shortModel = (model: string) => model.replace(/^claude-/, '').replace(/-\d{8}$/, '');

const dayOf = (day: string) =>
  new Date(`${day}T00:00:00Z`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' });

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

function Lamps({ glance }: { glance: Glance }) {
  // The telemetry part is the power switch below, so the one fact has one control.
  const parts = (glance.health?.parts ?? []).filter((part) => part.name !== 'Claude Code telemetry');

  return (
    <div className="map-lamps">
      {glance.health === null && (
        <span className={`map-lamp ${glance.healthFailure === null ? 'is-starting' : 'is-broken'}`} title={glance.healthFailure ?? undefined}>
          <span className="map-lamp-mark" aria-hidden="true">
            {glance.healthFailure === null ? '◌' : '✕'}
          </span>
          API
        </span>
      )}
      {parts.map((part) => (
        <span key={part.name} className={`map-lamp is-${part.state}`} title={[part.detail, part.action].filter(Boolean).join(' ')}>
          <span className="map-lamp-mark" aria-hidden="true">
            {partMarks[part.state].glyph}
          </span>
          {callSign(part)}
          <span className="map-hidden">{partMarks[part.state].label}</span>
        </span>
      ))}
      <button type="button" className="map-icon" onClick={glance.recheck} aria-label="Check health again" title="Check again">
        ↻
      </button>
    </div>
  );
}

function Power({ glance }: { glance: Glance }) {
  const { telemetry } = glance;
  const [confirming, setConfirming] = useState(false);
  const on = telemetry?.emitting ?? false;
  const unreadable = telemetry !== null && !telemetry.readable;

  return (
    <div className="map-power">
      <button
        type="button"
        className={`map-switch${on ? ' is-on' : ''}`}
        aria-pressed={on}
        disabled={telemetry === null || unreadable}
        title={unreadable ? (telemetry.problem ?? telemetry.settingsPath) : telemetry?.restartNote}
        onClick={() => (on ? glance.flipTelemetry(false) : setConfirming((open) => !open))}
      >
        <span className="map-switch-glyph" aria-hidden="true">
          ⏻
        </span>
        <span className="map-switch-word">Telemetry</span>
        <span className="map-track" aria-hidden="true">
          <span className="map-knob" />
        </span>
        <span className="map-switch-state">{telemetry === null ? '…' : unreadable ? '⚠' : on ? 'On' : 'Off'}</span>
      </button>

      {confirming && !on && telemetry !== null && (
        <div className="map-confirm" role="dialog" aria-label="Turn telemetry on" onKeyDown={(event) => event.key === 'Escape' && setConfirming(false)}>
          <span className="map-micro">Write</span>
          <code className="map-path">{telemetry.settingsPath}</code>
          <ul className="map-changes">
            {telemetry.changes.map((change) => (
              <li key={change.name}>
                <code>{change.name}</code> <span aria-label="becomes">→</span> <code>{change.to}</code>
              </li>
            ))}
          </ul>
          <div className="map-confirm-keys">
            <button
              type="button"
              className="map-key is-go"
              onClick={() => {
                glance.flipTelemetry(true);
                setConfirming(false);
              }}
            >
              ⏻ On
            </button>
            <button type="button" className="map-key" aria-label="Cancel" onClick={() => setConfirming(false)}>
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Repository({ glance }: { glance: Glance }) {
  const none = glance.repositories.length === 0;

  return (
    <label className="map-select" title={none ? 'No session has named a repository' : undefined}>
      <span className="map-select-glyph" aria-hidden="true">
        ⌥
      </span>
      <span className="map-hidden">Repository</span>
      <select value={glance.filter.repository} disabled={none} onChange={(event) => glance.chooseRepository(event.target.value)}>
        <option value="">All repositories</option>
        {glance.repositories.map((repository) => (
          <option key={repository} value={repository}>
            {repository}
          </option>
        ))}
      </select>
    </label>
  );
}

function Trace({ glance, firings }: { glance: Glance; firings: Activation[] }) {
  const span = glance.skills?.span ?? glance.activations?.span;

  if (span === undefined) {
    return <div className="map-trace is-waiting" aria-hidden="true" />;
  }

  const frame = timeframeOf(span);
  const bins = frame.days === 1 ? 24 : frame.days <= 7 ? frame.days * 4 : frame.days;
  const counts = binCounts(firings, frame, bins);
  const peak = Math.max(1, ...counts);
  const now = positionIn(frame, new Date().toISOString());

  return (
    <section className={`map-trace${glance.pending ? ' is-pending' : ''}`} aria-label={`${firings.length} firings, ${span.from} to ${span.to}`}>
      <div className="map-trace-plot">
        {counts.map((count, bin) => (
          <span
            // oxlint-disable-next-line react/no-array-index-key
            key={bin}
            className={`map-trace-bar${count === 0 ? ' is-idle' : ''}`}
            style={{ height: count === 0 ? undefined : `${Math.max(8, (count / peak) * 100)}%` }}
            title={String(count)}
          />
        ))}
        {now < 1 && <span className="map-trace-now" style={{ left: `${now * 100}%` }} aria-hidden="true" />}
      </div>
      <div className="map-trace-axis" aria-hidden="true">
        {tickLabels(frame).map((tick) => (
          <span key={tick.at} style={{ left: `${tick.at * 100}%` }}>
            {tick.text}
          </span>
        ))}
      </div>
    </section>
  );
}

function Readout({ placed, width, height, pinned }: { placed: Placed; width: number; height: number; pinned: boolean }) {
  const panelWidth = 236;
  const panelHeight = 236;
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
    <div className={`map-readout${pinned ? ' is-pinned' : ''}`} style={{ left, top, width: panelWidth }} aria-hidden="true">
      <div className="map-readout-name">
        {skill.name}
        {pinned && <span aria-hidden="true">◆</span>}
      </div>
      <dl>
        <dt>Cost</dt>
        <dd>{money(tile.cost)}</dd>
        <dt>Firings</dt>
        <dd>{skill.activations}</dd>
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
        <dt>Repos</dt>
        <dd>{skill.repositories.length === 0 ? '—' : skill.repositories.map((repository) => repository.split('/').pop()).join(' ')}</dd>
      </dl>
    </div>
  );
}

function Toggle<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { key: T; text: string; hint: string }[];
  onChange: (next: T) => void;
}) {
  return (
    <div className="map-toggle" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          className="map-toggle-key"
          aria-pressed={value === option.key}
          title={option.hint}
          onClick={() => onChange(option.key)}
        >
          {option.text}
        </button>
      ))}
    </div>
  );
}

export function MapVariant({ glance }: { glance: Glance }) {
  const { skills, skillsError, activations } = glance;
  const list = skills?.skills ?? [];
  const firings: Activation[] = activations?.activations ?? [];
  const signal: Signal | null = skillsError !== null && skills === null ? 'offline' : skills === null ? null : signalOf(skills.gap.kind);
  const totals = totalsOf(list);
  const unnamed = skills?.unnamedSpend ?? null;
  const unnamedCost = unnamed !== null && unnamed.cost > 0 ? unnamed.cost : 0;

  const [measure, setMeasure] = useState<Measure>('spend');
  const [order, setOrder] = useState<Order>('most');
  const [probe, setProbe] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string | null>(null);

  const mapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useLayoutEffect(() => {
    const map = mapRef.current;

    if (map === null) {
      return;
    }

    const observer = new ResizeObserver(([entry]) => setSize({ w: entry.contentRect.width, h: entry.contentRect.height }));

    observer.observe(map);

    return () => observer.disconnect();
  }, []);

  const valueOf = (skill: SkillSummary) => (measure === 'spend' ? (skill.spend?.cost ?? 0) : skill.activations);
  const sized = list.filter((skill) => valueOf(skill) > 0);
  const unsized = list.filter((skill) => valueOf(skill) <= 0);

  const perFirings = sized.map(perFiring);
  const maxPer = Math.max(0, ...perFirings);
  const minPer = perFirings.length === 0 ? 0 : Math.min(...perFirings);

  const frame = skills === null ? null : timeframeOf(skills.span);
  const bins = frame === null ? 0 : frame.days <= 1 ? 24 : frame.days <= 7 ? frame.days * 4 : frame.days;
  const sparks = new Map(sized.map((skill) => [skill.name, frame === null ? [] : binCounts(firingsOf(firings, skill.name), frame, bins)]));
  const sparkMax = Math.max(1, ...[...sparks.values()].flat());

  const tiles: Tile[] = sized.map((skill) => ({
    kind: 'skill',
    key: skill.name,
    skill,
    value: valueOf(skill),
    cost: skill.spend?.cost ?? 0,
    perFiring: perFiring(skill),
    heat: maxPer === 0 ? 0 : perFiring(skill) / maxPer,
    triggers: countTriggers(firingsOf(firings, skill.name)),
    last: lastFired(firings, skill.name),
    spark: sparks.get(skill.name) ?? [],
  }));

  // Unnamed spend has a cost but no firings, so it only has an area when the map measures money.
  if (measure === 'spend' && unnamed !== null && unnamedCost > 0) {
    tiles.push({ kind: 'unnamed', key: '∅unnamed', value: unnamedCost, cost: unnamedCost, tokens: tokensIn(unnamed) });
  }

  const ordered = tiles.toSorted((a, b) =>
    a.value === b.value ? a.key.localeCompare(b.key) : order === 'most' ? b.value - a.value : a.value - b.value,
  );
  const placed = squarify(ordered, size.w, size.h);
  const shownKey = probe ?? pinned;
  const shown = placed.find((entry) => entry.tile.key === shownKey) ?? null;

  const unknown = skills === null || (list.length === 0 && (signal === 'offline' || signal === 'unsure'));

  let panel: { glyph: string; word: string; tone: string; busy?: boolean } | null = null;

  if (skills === null && skillsError !== null) {
    panel = { glyph: '✕', word: 'No link', tone: 'red' };
  } else if (skills === null) {
    panel = { glyph: '◌', word: 'Scanning', tone: 'hud', busy: true };
  } else if (list.length === 0 && signal === 'offline') {
    panel = { glyph: '✕', word: 'No signal', tone: 'red' };
  } else if (list.length === 0) {
    panel = { glyph: '—', word: signal === 'quiet' ? 'Quiet' : 'Nothing', tone: 'dim' };
  } else if (tiles.length === 0) {
    panel = { glyph: '0', word: measure === 'spend' ? 'Free' : 'Unfired', tone: 'dim' };
  }

  const onMapKey = (event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      setPinned(null);
    }
  };

  return (
    <div className="map">
      <aside className="map-rail" aria-label="Instruments">
        <div className="map-brand">
          <h1>Skillworks</h1>
          {signal !== null && signal !== 'dark' && (
            <span className={`map-signal is-${signal}`} title={skillsError ?? skills?.gap.missing ?? undefined}>
              <span className="map-signal-dot" aria-hidden="true" />
              {signalWords[signal]}
            </span>
          )}
        </div>

        <section className="map-block" aria-label="Systems">
          <Lamps glance={glance} />
          <Power glance={glance} />
        </section>

        <section className="map-block" aria-label="Narrow">
          <div className="map-keys" role="group" aria-label="Span">
            {spanChoices.map((choice) => (
              <button
                key={choice.key}
                type="button"
                className="map-key"
                aria-pressed={glance.span === choice.key}
                onClick={() => glance.chooseSpan(choice.key)}
              >
                {choice.label}
              </button>
            ))}
          </div>
          <Repository glance={glance} />
        </section>

        <section className={`map-block map-totals${glance.pending ? ' is-pending' : ''}`} aria-label="Totals" aria-busy={glance.pending}>
          <div className="map-total is-hero">
            <span className="map-micro">Cost</span>
            <span className="map-total-value">{unknown ? '—' : money(totals.cost + unnamedCost)}</span>
          </div>
          <div className="map-total">
            <span className="map-micro">Firings</span>
            <span className="map-total-value">{unknown ? '—' : totals.firings}</span>
          </div>
          <div className="map-total">
            <span className="map-micro">Skills</span>
            <span className="map-total-value">{unknown ? '—' : totals.skills}</span>
          </div>
          <div className="map-total">
            <span className="map-micro">Tokens</span>
            <span className="map-total-value">{unknown ? '—' : compact(totals.tokens + (unnamed === null ? 0 : tokensIn(unnamed)))}</span>
          </div>
          <div className="map-total">
            <span className="map-micro">$/firing</span>
            <span className="map-total-value">{unknown || totals.firings === 0 ? '—' : money(totals.cost / totals.firings)}</span>
          </div>
          {unnamedCost > 0 && (
            <div className="map-total is-unnamed" title="Spend from plugins outside Anthropic’s marketplaces. Claude Code does not name the skill.">
              <span className="map-micro">Unnamed</span>
              <span className="map-total-value">{money(unnamedCost)}</span>
            </div>
          )}
        </section>
      </aside>

      <section className="map-deck" aria-label="Skills map">
        <Trace glance={glance} firings={firings} />

        <header className="map-deck-head">
          <Toggle
            label="Size by"
            value={measure}
            onChange={setMeasure}
            options={[
              { key: 'spend', text: '$ Spend', hint: 'Tile area is cost' },
              { key: 'usage', text: '× Usage', hint: 'Tile area is firings' },
            ]}
          />
          <Toggle
            label="Order"
            value={order}
            onChange={setOrder}
            options={[
              { key: 'most', text: '▼ Most', hint: 'Largest first' },
              { key: 'least', text: '▲ Least', hint: 'Smallest first' },
            ]}
          />

          {tiles.length > 0 && (
            <span className="map-legend" aria-label={`Brightness is cost per firing, ${money(minPer)} to ${money(maxPer)}`}>
              <span className="map-micro">$/firing</span>
              <span className="map-legend-value">{money(minPer)}</span>
              <span className="map-legend-bar" />
              <span className="map-legend-value">{money(maxPer)}</span>
            </span>
          )}

          {skills !== null && (
            <span className="map-range">
              {dayOf(skills.span.from)} <span aria-hidden="true">→</span>
              <span className="map-hidden">to</span> {dayOf(skills.span.to)}
            </span>
          )}
        </header>

        <div className="map-frame">
          <span className="map-corner is-tl" aria-hidden="true" />
          <span className="map-corner is-tr" aria-hidden="true" />
          <span className="map-corner is-bl" aria-hidden="true" />
          <span className="map-corner is-br" aria-hidden="true" />

          {/* A click on the ground, not on a tile, lets go of the pinned readout. */}
          {/* oxlint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
          <div
            className={`map-field${glance.pending ? ' is-pending' : ''}`}
            ref={mapRef}
            onClick={(event) => event.target === event.currentTarget && setPinned(null)}
            onKeyDown={onMapKey}
          >
            {panel !== null && (
              <div className={`map-panel is-${panel.tone}${panel.busy ? ' is-busy' : ''}`} role="status" title={skills?.gap.missing ?? skillsError ?? undefined}>
                <div className="map-panel-box">
                  <span className="map-panel-glyph" aria-hidden="true">
                    {panel.glyph}
                  </span>
                  <span className="map-panel-word">{panel.word}</span>
                </div>
              </div>
            )}

            {panel === null &&
              placed.map(({ x, y, w, h, tile, rank }) => {
                const style = { left: x, top: y, width: w, height: h };

                if (tile.kind === 'unnamed') {
                  return (
                    <div
                      key={tile.key}
                      className="map-tile is-unnamed"
                      style={style}
                      role="img"
                      aria-label={`Unnamed spend ${money(tile.cost)}`}
                      title="Spend from plugins outside Anthropic’s marketplaces. Claude Code does not name the skill."
                    >
                      <span className="map-skin" aria-hidden="true">
                        <span className="map-tile-top">
                          <span className="map-rank">{rank}</span>
                          <span className="map-tile-name">Unnamed</span>
                        </span>
                        <span className="map-tile-big">{money(tile.cost)}</span>
                        <span className="map-tile-foot">
                          <span className="map-tile-small">{compact(tile.tokens)} tok</span>
                        </span>
                      </span>
                    </div>
                  );
                }

                const { skill } = tile;
                const triggers = topTriggers(tile.triggers);
                const isPinned = pinned === tile.key;

                return (
                  <button
                    key={tile.key}
                    type="button"
                    className={`map-tile is-heat-${heatLevel(tile.heat)}${shownKey === tile.key ? ' is-probed' : ''}${isPinned ? ' is-pinned' : ''}`}
                    style={{ ...style, ['--heat' as string]: tile.heat.toFixed(3) }}
                    aria-pressed={isPinned}
                    aria-label={`${rank}. ${skill.name}: ${money(tile.cost)}, ${skill.activations} firings, ${money(tile.perFiring)} per firing`}
                    onClick={() => setPinned((current) => (current === tile.key ? null : tile.key))}
                    onMouseEnter={() => setProbe(tile.key)}
                    onMouseLeave={() => setProbe((current) => (current === tile.key ? null : current))}
                    onFocus={() => setProbe(tile.key)}
                    onBlur={() => setProbe((current) => (current === tile.key ? null : current))}
                  >
                    <span className="map-skin" aria-hidden="true">
                      <span className="map-tile-top">
                        <span className="map-rank">{rank}</span>
                        <span className="map-tile-name">{skill.name}</span>
                        <span className="map-heat" data-level={heatLevel(tile.heat)}>
                          <i />
                          <i />
                          <i />
                        </span>
                      </span>
                      <span className="map-tile-big">{measure === 'spend' ? money(tile.cost) : `×${skill.activations}`}</span>
                      {tile.spark.some((count) => count > 0) && (
                        <span className="map-spark">
                          {tile.spark.map((count, bin) => (
                            // oxlint-disable-next-line react/no-array-index-key
                            <i key={bin} style={{ height: `${(count / sparkMax) * 100}%` }} data-lit={count > 0 || undefined} />
                          ))}
                        </span>
                      )}
                      <span className="map-tile-foot">
                        <span className="map-tile-small">{measure === 'spend' ? `×${skill.activations}` : money(tile.cost)}</span>
                        <span className="map-tile-trig">
                          {triggers.slice(0, 3).map((trigger) => (
                            <span key={trigger.glyph} className="map-trig">
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

            {panel === null && shown !== null && (
              <Readout placed={shown} width={size.w} height={size.h} pinned={pinned === shown.tile.key && probe === null} />
            )}
          </div>
        </div>

        {skills !== null && unsized.length > 0 && (
          <div className="map-strip" aria-label={measure === 'spend' ? 'No cost' : 'No firings'}>
            <span className="map-strip-label">{measure === 'spend' ? '$0' : '×0'}</span>
            {unsized.map((skill) => (
              <span key={skill.name} className="map-chip" title={skill.spend === null ? 'Cost not named' : undefined}>
                {skill.name}
                <span className="map-chip-count">{measure === 'spend' ? `×${skill.activations}` : money(skill.spend?.cost)}</span>
              </span>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
