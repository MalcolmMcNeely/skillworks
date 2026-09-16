import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from 'react';
import { describeCount, describeMoney } from '../../figures/lib/figures';
import { describeDay } from '../../filters/lib/filters';
import { Keys } from '../../keys/components/Keys';
import { triggerMarks } from '../../provenance/lib/triggers';
import { showsFigures, type SkillsAnswer } from '../lib/answer';
import { describeTile, heatStep, layOut, tilesOf, unnamedWord, viewWords, type MapView, type PlacedTile, type Sizing } from '../lib/map';
import type { MapChoice } from '../lib/mapChoice';
import { mapNoticeOf } from '../lib/mapNotice';
import { describeSpend, missingWords, type SkillSummary } from '../lib/skills';
import type { StripSlice } from '../lib/strip';
import { TileReadout } from './TileReadout';

// One scale across the whole map, so a busy hour on one tile is not drawn the height of a quiet one on another.
function Spark({ counts, slices, peak }: { counts: readonly number[]; slices: readonly StripSlice[]; peak: number }) {
  if (counts.every((count) => count === 0)) {
    return null;
  }

  return (
    <span className="tile-spark" aria-hidden="true">
      {counts.map((count, slice) => {
        const state = slices[slice]?.state ?? 'landed';

        // A slice the store has not given carries no count, so it is drawn as a dash rather than as a quiet hour.
        return state === 'landed' ? (
          // oxlint-disable-next-line react/no-array-index-key
          <i key={slice} className={count === 0 ? 'is-idle' : ''} style={{ height: `${(count / peak) * 100}%` }} />
        ) : (
          // oxlint-disable-next-line react/no-array-index-key
          <i key={slice} className={`is-${state}`} />
        );
      })}
    </span>
  );
}

function Tile({
  placed,
  view,
  pinned,
  slices,
  peak,
  onPin,
  onProbe,
}: {
  placed: PlacedTile;
  view: MapView;
  pinned: boolean;
  slices: readonly StripSlice[];
  peak: number;
  onPin: () => void;
  onProbe: (probing: boolean) => void;
}) {
  const { tile, x, y, width, height } = placed;

  if (tile.kind === 'unnamed') {
    return (
      <li className="tile is-unnamed" style={{ left: x, top: y, width, height }}>
        {/* An image, not a button: Unnamed spend belongs to no skill, so there is no readout to pin. */}
        <div className="tile-skin" role="img" tabIndex={0} aria-label={describeTile(tile)}>
          <span className="tile-top">
            <span className="tile-rank">{tile.rank}</span>
            <span className="tile-name">{unnamedWord}</span>
          </span>
          <span className="tile-figure">{describeMoney(tile.spend.cost)}</span>
        </div>
      </li>
    );
  }

  const { skill } = tile;
  const cost = describeSpend(skill.spend?.cost ?? null);
  const activations = `×${describeCount(skill.activations)}`;

  return (
    <li
      className={`tile is-heat-${tile.heat === null ? 0 : heatStep(tile.heat)}${pinned ? ' is-pinned' : ''}`}
      style={{ left: x, top: y, width, height, '--heat': tile.heat ?? 0 } as CSSProperties}
    >
      {/* A button, so Enter and Space pin the readout as a click does, with no key handler of its own. */}
      <button
        type="button"
        className="tile-skin"
        aria-pressed={pinned}
        aria-label={describeTile(tile)}
        onClick={onPin}
        onMouseEnter={() => onProbe(true)}
        onMouseLeave={() => onProbe(false)}
        onFocus={() => onProbe(true)}
        onBlur={() => onProbe(false)}
      >
        <span className="tile-top" aria-hidden="true">
          <span className="tile-rank">{tile.rank}</span>
          <span className="tile-name">{skill.name}</span>
          <span className="heat">
            <i />
            <i />
            <i />
          </span>
        </span>
        <span className="tile-figure" aria-hidden="true">
          {view === 'cost' ? cost : activations}
        </span>
        <Spark counts={skill.spark} slices={slices} peak={peak} />
        <span className="tile-foot" aria-hidden="true">
          {view === 'cost' ? activations : cost}
          <span className="tile-triggers">
            {triggerMarks(skill.triggers).map((mark) => (
              <span key={mark.word} className="trigger">
                {mark.glyph}
                {describeCount(mark.activations)}
              </span>
            ))}
          </span>
        </span>
      </button>
    </li>
  );
}

interface Chip {
  key: string;
  name: string;
  figure: string;
}

// One shape for both rows, so the two reasons a skill is off the map never drift apart on screen.
function OffMap({ word, label, chips }: { word: string; label: string; chips: readonly Chip[] }) {
  return (
    <section className="offmap" aria-label={label}>
      <span className="offmap-label" aria-hidden="true">
        {word}
      </span>
      <ul>
        {chips.map((chip) => (
          <li key={chip.key} className="chip">
            {chip.name}
            <span className="chip-figure">{chip.figure}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Unsized({ skills, view }: { skills: readonly SkillSummary[]; view: MapView }) {
  const word = `No ${viewWords[view]}`;

  return (
    <OffMap
      word={word}
      label={`Skills with ${word}`}
      chips={skills.map((skill) => ({
        key: skill.name,
        name: skill.name,
        figure:
          view === 'cost'
            ? `×${describeCount(skill.activations)}${skill.spend === null ? ` · ${missingWords.notNamed}` : ''}`
            : describeSpend(skill.spend?.cost ?? null),
      }))}
    />
  );
}

// Having a figure and missing the map is a different fact from having no figure at all.
function Beyond({ sized, view }: { sized: readonly Sizing[]; view: MapView }) {
  return (
    <OffMap
      word="Did not fit"
      label="Skills that did not fit the map"
      chips={sized.map((sizing) => ({
        key: sizing.key,
        name: sizing.kind === 'skill' ? sizing.skill.name : unnamedWord,
        figure: view === 'cost' ? describeMoney(sizing.value) : `×${describeCount(sizing.value)}`,
      }))}
    />
  );
}

const views = [
  { key: 'cost', glyph: '$', word: viewWords.cost },
  { key: 'activations', glyph: '×', word: viewWords.activations },
] as const;

const orders = [
  { key: 'most', glyph: '▼', word: 'Most' },
  { key: 'least', glyph: '▲', word: 'Least' },
] as const;

const minute = 60 * 1000;

export function SkillMap({
  answer,
  failure,
  arriving,
  choice,
  onChoose,
}: {
  answer: SkillsAnswer | null;
  failure: string | null;
  arriving: boolean;
  choice: MapChoice;
  onChoose: (choice: MapChoice) => void;
}) {
  const field = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [pinned, setPinned] = useState<string | null>(null);
  const [probed, setProbed] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  // Measured, as a squarified layout needs the map's shape in pixels and only the browser knows it.
  useLayoutEffect(() => {
    const measured = field.current;

    if (measured === null) {
      return;
    }

    const observer = new ResizeObserver(([entry]) =>
      setSize({ width: entry.contentRect.width, height: entry.contentRect.height }),
    );

    observer.observe(measured);

    return () => observer.disconnect();
  }, []);

  // Ticking, so a readout left pinned does not keep saying the skill last fired an hour ago.
  useEffect(() => {
    const ticking = setInterval(() => setNow(Date.now()), minute);

    return () => clearInterval(ticking);
  }, []);

  // On the window, so Escape lets go wherever the focus has moved to since the tile was pinned.
  useEffect(() => {
    if (pinned === null) {
      return;
    }

    const letGo = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setPinned(null);
      }
    };

    window.addEventListener('keydown', letGo);

    return () => window.removeEventListener('keydown', letGo);
  }, [pinned]);

  const { tiles, unsized, beyond, each } = tilesOf(answer ?? { skills: [], unnamedSpend: null }, choice.view, choice.order);
  const notice = mapNoticeOf({ answer, failure, tileCount: tiles.length, view: choice.view });
  const placed = layOut(tiles, size);
  const shown = placed.find((entry) => entry.tile.key === (probed ?? pinned)) ?? null;
  const slices = answer?.slices ?? [];
  const peak = Math.max(1, ...tiles.flatMap((tile) => (tile.kind === 'skill' ? tile.skill.spark : [])));

  return (
    <section className="deck" aria-label="Skills map">
      <header className="deck-head">
        <Keys label="Size by" pressed={choice.view} options={views} onPress={(view) => onChoose({ ...choice, view })} />
        <Keys label="Order" pressed={choice.order} options={orders} onPress={(order) => onChoose({ ...choice, order })} />

        {notice === null && each !== null && (
          <p className={`legend${arriving ? ' is-arriving' : ''}`}>
            <span className="micro">Each</span>
            <span className="legend-figure">{describeMoney(each.lowest)}</span>
            <span className="legend-bar" aria-hidden="true" />
            <span className="visually-hidden">to</span>
            <span className="legend-figure">{describeMoney(each.highest)}</span>
          </p>
        )}

        {/* From the answer, not the address, so it names the days the API actually counted. */}
        {answer !== null && (
          <p className="range">
            {describeDay(answer.span.from)}
            {answer.span.to !== answer.span.from && (
              <>
                {' '}
                <span aria-hidden="true">→</span>
                <span className="visually-hidden">to</span> {describeDay(answer.span.to)}
              </>
            )}{' '}
            UTC
          </p>
        )}
      </header>

      <div className="frame">
        <div className={`field${arriving ? ' is-arriving' : ''}`} ref={field} aria-busy={arriving}>
          {notice === null ? (
            <>
              <ol className="tiles" aria-label={`Skills by ${viewWords[choice.view]}, ${choice.order} first`}>
                {placed.map((entry) => (
                  <Tile
                    key={entry.tile.key}
                    placed={entry}
                    view={choice.view}
                    pinned={pinned === entry.tile.key}
                    slices={slices}
                    peak={peak}
                    onPin={() => setPinned((current) => (current === entry.tile.key ? null : entry.tile.key))}
                    onProbe={(probing) =>
                      setProbed((current) => (probing ? entry.tile.key : current === entry.tile.key ? null : current))
                    }
                  />
                ))}
              </ol>

              {shown !== null && (
                <TileReadout placed={shown} map={size} pinned={pinned === shown.tile.key} now={now} />
              )}
            </>
          ) : (
            <div className={`map-notice is-${notice.tone}${notice.busy ? ' is-busy' : ''}`} role="status">
              <div className="map-notice-box">
                <span className="map-notice-glyph" aria-hidden="true">
                  {notice.glyph}
                </span>
                <span className="map-notice-word">{notice.word}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {showsFigures(answer) && unsized.length > 0 && <Unsized skills={unsized} view={choice.view} />}
      {showsFigures(answer) && beyond.length > 0 && <Beyond sized={beyond} view={choice.view} />}
    </section>
  );
}
