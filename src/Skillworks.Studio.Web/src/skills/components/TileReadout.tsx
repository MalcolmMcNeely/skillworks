import type { PlacedTile, Size } from '../lib/map';
import { readoutAt, readoutRows, readoutSize } from '../lib/readout';

export function TileReadout({
  placed,
  map,
  pinned,
  now,
}: {
  placed: PlacedTile;
  map: Size;
  pinned: boolean;
  now: number;
}) {
  if (placed.tile.kind !== 'skill') {
    return null;
  }

  const { skill } = placed.tile;

  return (
    <section
      className={`readout${pinned ? ' is-pinned' : ''}`}
      style={{ ...readoutAt(placed, map), width: readoutSize.width }}
      aria-label={`${skill.name} readout`}
    >
      <p className="readout-name">
        {skill.name}
        {pinned && (
          <span className="readout-pin" aria-hidden="true">
            ◆
          </span>
        )}
      </p>
      <dl>
        {readoutRows(skill, now).map((row) => (
          <div key={row.label} className="readout-row">
            <dt>{row.label}</dt>
            <dd>
              <span aria-hidden={row.reading === null ? undefined : true}>{row.value}</span>
              {row.reading !== null && <span className="visually-hidden">{row.reading}</span>}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
