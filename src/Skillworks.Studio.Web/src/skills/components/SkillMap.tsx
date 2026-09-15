import { useLayoutEffect, useRef, useState, type CSSProperties } from 'react';
import { describeDay } from '../../filters/lib/filters';
import { Keys } from '../../keys/components/Keys';
import { describeTile, heatStep, layOut, tilesOf, viewWords, type MapView, type PlacedTile } from '../lib/map';
import type { MapChoice } from '../lib/mapChoice';
import { mapPanelOf } from '../lib/mapPanel';
import { describeCount, describeMoney, notNamed, type SkillsAnswer, type SkillSummary } from '../lib/skills';

function Tile({ placed, view }: { placed: PlacedTile; view: MapView }) {
  const { tile, x, y, width, height } = placed;

  if (tile.kind === 'unnamed') {
    return (
      <li className="tile is-unnamed" style={{ left: x, top: y, width, height }}>
        <div className="tile-skin" role="img" tabIndex={0} aria-label={describeTile(tile)}>
          <span className="tile-top">
            <span className="tile-rank">{tile.rank}</span>
            <span className="tile-name">Unnamed spend</span>
          </span>
          <span className="tile-figure">{describeMoney(tile.spend.cost)}</span>
        </div>
      </li>
    );
  }

  const { skill } = tile;
  const cost = describeMoney(skill.spend?.cost ?? null);
  const activations = `×${describeCount(skill.activations)}`;

  return (
    <li
      className={`tile is-heat-${tile.heat === null ? 0 : heatStep(tile.heat)}`}
      style={{ left: x, top: y, width, height, '--heat': tile.heat ?? 0 } as CSSProperties}
    >
      {/* An image, not a button, as pressing a tile does nothing; an image's label is read out on focus. */}
      <div className="tile-skin" role="img" tabIndex={0} aria-label={describeTile(tile)}>
        <span className="tile-top">
          <span className="tile-rank">{tile.rank}</span>
          <span className="tile-name">{skill.name}</span>
          <span className="heat">
            <i />
            <i />
            <i />
          </span>
        </span>
        <span className="tile-figure">{view === 'cost' ? cost : activations}</span>
        <span className="tile-foot">{view === 'cost' ? activations : cost}</span>
      </div>
    </li>
  );
}

function Strip({ skills, view }: { skills: readonly SkillSummary[]; view: MapView }) {
  const word = `No ${viewWords[view]}`;

  return (
    <section className="strip" aria-label={`Skills with ${word}`}>
      <span className="strip-label" aria-hidden="true">
        {word}
      </span>
      <ul>
        {skills.map((skill) => (
          <li key={skill.name} className="chip">
            {skill.name}
            <span className="chip-figure">
              {view === 'cost'
                ? `×${describeCount(skill.activations)}${skill.spend === null ? ` · ${notNamed}` : ''}`
                : describeMoney(skill.spend?.cost ?? null)}
            </span>
          </li>
        ))}
      </ul>
    </section>
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

  const { tiles, unsized, each } = tilesOf(answer ?? { skills: [], unnamedSpend: null }, choice.view, choice.order);
  const panel = mapPanelOf({ answer, failure, tileCount: tiles.length, view: choice.view });

  return (
    <section className="deck" aria-label="Skills map">
      <header className="deck-head">
        <Keys label="Size by" pressed={choice.view} options={views} onPress={(view) => onChoose({ ...choice, view })} />
        <Keys label="Order" pressed={choice.order} options={orders} onPress={(order) => onChoose({ ...choice, order })} />

        {panel === null && each !== null && (
          <p className="legend">
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
          {panel === null ? (
            <ol className="tiles" aria-label={`Skills by ${viewWords[choice.view]}, ${choice.order} first`}>
              {layOut(tiles, size).map((placed) => (
                <Tile key={placed.tile.key} placed={placed} view={choice.view} />
              ))}
            </ol>
          ) : (
            <div className={`panel is-${panel.tone}${panel.busy ? ' is-busy' : ''}`} role="status">
              <div className="panel-box">
                <span className="panel-glyph" aria-hidden="true">
                  {panel.glyph}
                </span>
                <span className="panel-word">{panel.word}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {answer !== null && answer.gap.kind !== 'unreachable' && unsized.length > 0 && (
        <Strip skills={unsized} view={choice.view} />
      )}
    </section>
  );
}
