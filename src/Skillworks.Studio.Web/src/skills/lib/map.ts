import { describeCount, describeMoney, type SkillsAnswer, type SkillSummary, type TurnTotals } from './skills';

export type MapView = 'cost' | 'activations';

export type MapOrder = 'most' | 'least';

export const viewWords: Record<MapView, string> = { cost: 'Cost', activations: 'Activations' };

export type MapTile =
  | {
      kind: 'skill';
      key: string;
      rank: number;
      value: number;
      skill: SkillSummary;
      each: number | null;
      // Scaled to this map's lowest and highest Each, so the legend's two ends match the dimmest and brightest tile.
      heat: number | null;
    }
  | { kind: 'unnamed'; key: string; rank: number; value: number; spend: TurnTotals };

type Unranked<T> = T extends unknown ? Omit<T, 'rank'> : never;

// Every tile gets at least this share of the map, so a skill ranked last is still big enough to read and to reach.
const floorShare = 0.02;

// Raised tiles never take more than this much of the map, so a map of many skills is still sized by their figures.
const mostFloored = 0.5;

export interface SkillTiles {
  tiles: MapTile[];
  unsized: SkillSummary[];
  each: { lowest: number; highest: number } | null;
}

export interface PlacedTile {
  tile: MapTile;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Rectangle {
  x: number;
  y: number;
  width: number;
  height: number;
}

// The API counts an Each of nothing for a skill that spent but never fired, which would read as the cheapest on the map.
function eachOf(skill: SkillSummary): number | null {
  return skill.activations === 0 ? null : skill.averageCost;
}

export function tilesOf(answer: Pick<SkillsAnswer, 'skills' | 'unnamedSpend'>, view: MapView, order: MapOrder): SkillTiles {
  const valued = answer.skills.map((skill) => ({
    skill,
    value: view === 'cost' ? (skill.spend?.cost ?? 0) : skill.activations,
  }));

  const onMap = valued.filter((entry) => entry.value > 0);
  const eaches = onMap.flatMap((entry) => eachOf(entry.skill) ?? []);
  const each = eaches.length === 0 ? null : { lowest: Math.min(...eaches), highest: Math.max(...eaches) };

  const sized: Unranked<MapTile>[] = onMap.map(({ skill, value }) => {
    const skillEach = eachOf(skill);

    return {
      kind: 'skill',
      key: `skill:${skill.name}`,
      value,
      skill,
      each: skillEach,
      heat:
        skillEach === null || each === null
          ? null
          : each.highest === each.lowest
            ? 0
            : (skillEach - each.lowest) / (each.highest - each.lowest),
    };
  });

  // Never shared out among skills, and it has no Activations, so it is sized only when the map shows Cost.
  if (view === 'cost' && answer.unnamedSpend !== null && answer.unnamedSpend.cost > 0) {
    sized.push({ kind: 'unnamed', key: 'unnamed', value: answer.unnamedSpend.cost, spend: answer.unnamedSpend });
  }

  const ordered = sized.toSorted((a, b) =>
    a.value === b.value ? a.key.localeCompare(b.key) : order === 'most' ? b.value - a.value : a.value - b.value,
  );

  return {
    tiles: ordered.map((tile, index) => ({ ...tile, rank: index + 1 })),
    unsized: valued.filter((entry) => entry.value <= 0).map((entry) => entry.skill),
    each,
  };
}

// The whole reading in words, because a screen reader cannot see a tile's size, place or brightness.
export function describeTile(tile: MapTile): string {
  if (tile.kind === 'unnamed') {
    return `${tile.rank}. Unnamed spend. Cost ${describeMoney(tile.spend.cost)}.`;
  }

  const { skill } = tile;
  const read = `${tile.rank}. ${skill.name}. Cost ${describeMoney(skill.spend?.cost ?? null)}. Activations ${describeCount(skill.activations)}.`;

  return skill.activations === 0 ? read : `${read} Each ${describeMoney(tile.each)}.`;
}

// Steps as well as brightness, so a reader who cannot tell the shades apart can still count the heat.
export function heatStep(heat: number): 1 | 2 | 3 {
  if (heat > 2 / 3) {
    return 3;
  }

  return heat > 1 / 3 ? 2 : 1;
}

// Raising a small tile to the minimum shrinks the rest, which can push another under it, so this repeats until none is.
function sharesOf(tiles: readonly MapTile[], total: number): number[] {
  const floor = Math.min(floorShare, mostFloored / tiles.length);
  const floored = new Set<number>();

  for (;;) {
    const spare = 1 - floor * floored.size;
    const unfloored = total - tiles.reduce((sum, tile, index) => sum + (floored.has(index) ? tile.value : 0), 0);
    const under = tiles.flatMap((tile, index) =>
      !floored.has(index) && (tile.value / unfloored) * spare < floor ? [index] : [],
    );

    if (under.length === 0) {
      return tiles.map((tile, index) => (floored.has(index) ? floor : (tile.value / unfloored) * spare));
    }

    for (const index of under) {
      floored.add(index);
    }
  }
}

function worstAspectRatio(areas: readonly number[], side: number): number {
  const sum = areas.reduce((total, area) => total + area, 0);

  return Math.max((side * side * Math.max(...areas)) / (sum * sum), (sum * sum) / (side * side * Math.min(...areas)));
}

// Squarified, but in the order given rather than largest first, so the reader's order decides what sits top left.
export function layOut(tiles: readonly MapTile[], size: { width: number; height: number }): PlacedTile[] {
  const total = tiles.reduce((sum, tile) => sum + tile.value, 0);

  if (total <= 0 || size.width <= 0 || size.height <= 0) {
    return [];
  }

  const shares = sharesOf(tiles, total);
  const placed: PlacedTile[] = [];
  let remaining: Rectangle = { x: 0, y: 0, width: size.width, height: size.height };
  let row: { tile: MapTile; area: number }[] = [];

  const layRow = () => {
    const sum = row.reduce((running, entry) => running + entry.area, 0);

    if (remaining.width >= remaining.height) {
      const width = sum / remaining.height;
      let y = remaining.y;

      for (const entry of row) {
        const height = entry.area / width;
        placed.push({ tile: entry.tile, x: remaining.x, y, width, height });
        y += height;
      }

      remaining = { x: remaining.x + width, y: remaining.y, width: remaining.width - width, height: remaining.height };
    } else {
      const height = sum / remaining.width;
      let x = remaining.x;

      for (const entry of row) {
        const width = entry.area / height;
        placed.push({ tile: entry.tile, x, y: remaining.y, width, height });
        x += width;
      }

      remaining = { x: remaining.x, y: remaining.y + height, width: remaining.width, height: remaining.height - height };
    }

    row = [];
  };

  for (const [index, tile] of tiles.entries()) {
    const entry = { tile, area: shares[index] * size.width * size.height };
    const side = Math.min(remaining.width, remaining.height);
    const areas = row.map((queued) => queued.area);

    if (row.length > 0 && worstAspectRatio([...areas, entry.area], side) > worstAspectRatio(areas, side)) {
      layRow();
    }

    row.push(entry);
  }

  if (row.length > 0) {
    layRow();
  }

  return placed;
}
