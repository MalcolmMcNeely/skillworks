import { describeCount, describeMoney } from '../../figures/lib/figures';
import type { SkillsAnswer } from './answer';
import { describeEach, describeSpend, type SkillSummary, type TurnTotals } from './skills';

export type MapFigure = 'cost' | 'activations';

export type MapOrder = 'most' | 'least';

export const figureWords: Record<MapFigure, string> = { cost: 'Cost', activations: 'Activations' };

export type MapTile =
  | {
      kind: 'skill';
      key: string;
      rank: number;
      value: number;
      skill: SkillSummary;
      // Scaled to this map's lowest and highest Each, so the legend's two ends match the dimmest and brightest tile.
      heat: number | null;
    }
  | { kind: 'unnamed'; key: string; rank: number; value: number; spend: TurnTotals };

export type Sizing =
  | { kind: 'skill'; key: string; value: number; skill: SkillSummary }
  | { kind: 'unnamed'; key: string; value: number; spend: TurnTotals };

type EachRange = { lowest: number; highest: number } | null;

export const unnamedWord = 'Unnamed spend';

// Every tile gets at least this share of the map, so a skill ranked last is still big enough to read and to reach.
const floorShare = 0.02;

// Floored tiles take at most half the map at this count, so the figures still shape the other half.
const mapCap = 25;

export interface SkillTiles {
  tiles: MapTile[];
  unsized: SkillSummary[];
  beyond: Sizing[];
  each: EachRange;
}

export interface Size {
  width: number;
  height: number;
}

export interface PlacedTile extends Size {
  tile: MapTile;
  x: number;
  y: number;
}

interface Rectangle extends Size {
  x: number;
  y: number;
}

function rankedTile(sizing: Sizing, rank: number, range: EachRange): MapTile {
  if (sizing.kind === 'unnamed') {
    return { ...sizing, rank };
  }

  const own = sizing.skill.each;

  return {
    ...sizing,
    rank,
    heat:
      own === null || range === null
        ? null
        : range.highest === range.lowest
          ? 0
          : (own - range.lowest) / (range.highest - range.lowest),
  };
}

export function tilesOf(answer: Pick<SkillsAnswer, 'skills' | 'unnamedSpend'>, figure: MapFigure, order: MapOrder): SkillTiles {
  const valued = answer.skills.map((skill) => ({
    skill,
    value: figure === 'cost' ? (skill.spend?.cost ?? 0) : skill.activations,
  }));

  const sized: Sizing[] = valued
    .filter((entry) => entry.value > 0)
    .map(({ skill, value }) => ({ kind: 'skill', key: `skill:${skill.name}`, value, skill }));

  // Never shared out among skills, and it has no Activations, so it is sized only when the map shows Cost.
  if (figure === 'cost' && answer.unnamedSpend !== null && answer.unnamedSpend.cost > 0) {
    sized.push({ kind: 'unnamed', key: 'unnamed', value: answer.unnamedSpend.cost, spend: answer.unnamedSpend });
  }

  const ordered = sized.toSorted((a, b) =>
    a.value === b.value ? a.key.localeCompare(b.key) : order === 'most' ? b.value - a.value : a.value - b.value,
  );

  const drawn = ordered.slice(0, mapCap);
  const eaches = drawn.flatMap((sizing) => (sizing.kind === 'skill' ? (sizing.skill.each ?? []) : []));
  const each = eaches.length === 0 ? null : { lowest: Math.min(...eaches), highest: Math.max(...eaches) };

  return {
    tiles: drawn.map((sizing, index) => rankedTile(sizing, index + 1, each)),
    unsized: valued.filter((entry) => entry.value <= 0).map((entry) => entry.skill),
    beyond: ordered.slice(mapCap),
    each,
  };
}

// The whole reading in words, because a screen reader cannot see a tile's size, place or brightness.
export function describeTile(tile: MapTile): string {
  if (tile.kind === 'unnamed') {
    return `${tile.rank}. ${unnamedWord}. Cost ${describeMoney(tile.spend.cost)}.`;
  }

  const { skill } = tile;

  return `${tile.rank}. ${skill.name}. Cost ${describeSpend(skill.spend?.cost ?? null)}. Activations ${describeCount(skill.activations)}. Each ${describeEach(skill)}.`;
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
  const floored = new Set<number>();

  for (;;) {
    const spare = 1 - floorShare * floored.size;
    const unfloored = total - tiles.reduce((sum, tile, index) => sum + (floored.has(index) ? tile.value : 0), 0);
    const under = tiles.flatMap((tile, index) =>
      !floored.has(index) && (tile.value / unfloored) * spare < floorShare ? [index] : [],
    );

    if (under.length === 0) {
      return tiles.map((tile, index) => (floored.has(index) ? floorShare : (tile.value / unfloored) * spare));
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
export function layOut(tiles: readonly MapTile[], size: Size): PlacedTile[] {
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
