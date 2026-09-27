import type { Tile } from '../../lib/verdict';

export function Tiles({ tiles }: { tiles: readonly Tile[] }) {
  return (
    <dl className="verdict-tiles" aria-label="The whole run">
      {tiles.map((tile) => (
        <div key={tile.name} className={`verdict-tile${tile.alarm ? ' is-alarm' : ''}`}>
          <dt>{tile.name}</dt>
          <dd className="verdict-figure">{tile.figure}</dd>
          {tile.note === null ? null : <dd className="micro verdict-note">{tile.note}</dd>}
        </div>
      ))}
    </dl>
  );
}
