import { describe, expect, it } from 'vitest';
import { describeTile, heatStep, layOut, tilesOf, type MapTile, type PlacedTile } from './map';
import type { SkillSummary } from './skills';

function skill(name: string, cost: number, activations: number): SkillSummary {
  return {
    name,
    activations,
    repositories: [],
    models: [],
    efforts: [],
    spend: { cost, inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, cacheCreationTokens: 0 },
    averageCost: activations === 0 ? 0 : cost / activations,
    origins: [],
  };
}

const size = { width: 400, height: 300 };

function overlap(a: PlacedTile, b: PlacedTile): number {
  const across = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
  const down = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);

  return Math.max(0, across) * Math.max(0, down);
}

const answered = [skill('alpha', 10, 40), skill('beta', 30, 10), skill('gamma', 20, 25)];

function nameOf(tile: MapTile | undefined): string | undefined {
  return tile?.kind === 'skill' ? tile.skill.name : undefined;
}

function names(tiles: readonly MapTile[]): (string | undefined)[] {
  return tiles.map(nameOf);
}

describe('tilesOf', () => {
  it('puts the skill with the most Cost first when the reader asks for most', () => {
    const { tiles } = tilesOf({ skills: answered, unnamedSpend: null }, 'cost', 'most');

    expect(names(tiles)).toEqual(['beta', 'gamma', 'alpha']);
  });

  it('puts the skill with the least Cost first when the reader asks for least', () => {
    const { tiles } = tilesOf({ skills: answered, unnamedSpend: null }, 'cost', 'least');

    expect(names(tiles)).toEqual(['alpha', 'gamma', 'beta']);
  });

  it('sizes by Activations when the reader asks for them', () => {
    const { tiles } = tilesOf({ skills: answered, unnamedSpend: null }, 'activations', 'most');

    expect(tiles.map((tile) => [nameOf(tile), tile.value])).toEqual([
      ['alpha', 40],
      ['gamma', 25],
      ['beta', 10],
    ]);
  });

  it('breaks a tie by skill name, whichever order the reader chose', () => {
    const tied = [skill('gamma', 5, 1), skill('alpha', 5, 1), skill('beta', 5, 1)];

    expect(names(tilesOf({ skills: tied, unnamedSpend: null }, 'cost', 'most').tiles)).toEqual(['alpha', 'beta', 'gamma']);
    expect(names(tilesOf({ skills: tied, unnamedSpend: null }, 'cost', 'least').tiles)).toEqual(['alpha', 'beta', 'gamma']);
  });

  it('leaves a skill with no Cost off the Cost map, and lists it under the map instead', () => {
    const unnamed = { ...skill('delta', 0, 7), spend: null, averageCost: null };
    const skills = [skill('alpha', 0, 3), skill('beta', 2, 1), unnamed];

    const { tiles, unsized } = tilesOf({ skills, unnamedSpend: null }, 'cost', 'most');

    expect(names(tiles)).toEqual(['beta']);
    expect(unsized.map((each) => each.name)).toEqual(['alpha', 'delta']);
  });

  it('leaves a skill with no Activations off the Activations map, and lists it under the map instead', () => {
    const skills = [skill('alpha', 4, 0), skill('beta', 2, 1)];

    const { tiles, unsized } = tilesOf({ skills, unnamedSpend: null }, 'activations', 'most');

    expect(names(tiles)).toEqual(['beta']);
    expect(unsized.map((each) => each.name)).toEqual(['alpha']);
  });

  it('gives Unnamed spend a tile of its own on the Cost map, ranked by its Cost', () => {
    const unnamedSpend = { cost: 15, inputTokens: 1, outputTokens: 2, cacheReadTokens: 3, cacheCreationTokens: 4 };

    const { tiles } = tilesOf({ skills: answered, unnamedSpend }, 'cost', 'most');

    expect(tiles.map((tile) => [tile.kind, nameOf(tile), tile.rank, tile.value])).toEqual([
      ['skill', 'beta', 1, 30],
      ['skill', 'gamma', 2, 20],
      ['unnamed', undefined, 3, 15],
      ['skill', 'alpha', 4, 10],
    ]);
  });

  it('leaves Unnamed spend off the Activations map, as it has no Activations to size it by', () => {
    const unnamedSpend = { cost: 15, inputTokens: 1, outputTokens: 2, cacheReadTokens: 3, cacheCreationTokens: 4 };

    const { tiles } = tilesOf({ skills: answered, unnamedSpend }, 'activations', 'most');

    expect(tiles.map((tile) => tile.kind)).toEqual(['skill', 'skill', 'skill']);
  });

  it('gives Unnamed spend no tile when it cost nothing', () => {
    const unnamedSpend = { cost: 0, inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, cacheCreationTokens: 0 };

    const { tiles } = tilesOf({ skills: answered, unnamedSpend }, 'cost', 'most');

    expect(tiles.map((tile) => tile.kind)).toEqual(['skill', 'skill', 'skill']);
  });

  it('heats each tile by its Each, from the lowest on the map to the highest', () => {
    const skills = [skill('alpha', 10, 10), skill('beta', 30, 10), skill('gamma', 20, 10)];

    const { tiles, each } = tilesOf({ skills, unnamedSpend: null }, 'cost', 'most');

    expect(tiles.map((tile) => (tile.kind === 'skill' ? [tile.skill.name, tile.each, tile.heat] : null))).toEqual([
      ['beta', 3, 1],
      ['gamma', 2, 0.5],
      ['alpha', 1, 0],
    ]);
    expect(each).toEqual({ lowest: 1, highest: 3 });
  });

  it('leaves a tile unheated, and off the legend, when its spend was not named', () => {
    const unnamed = { ...skill('delta', 0, 90), spend: null, averageCost: null };
    const skills = [skill('alpha', 10, 10), skill('beta', 30, 10), unnamed];

    const { tiles, each } = tilesOf({ skills, unnamedSpend: null }, 'activations', 'most');

    expect(tiles.map((tile) => (tile.kind === 'skill' ? [tile.skill.name, tile.each, tile.heat] : null))).toEqual([
      ['delta', null, null],
      ['alpha', 1, 0],
      ['beta', 3, 1],
    ]);
    expect(each).toEqual({ lowest: 1, highest: 3 });
  });

  it('gives a skill that spent but never fired no Each, rather than an Each of nothing', () => {
    const skills = [skill('alpha', 10, 10), skill('beta', 30, 10), skill('gamma', 5, 0)];

    const { tiles, each } = tilesOf({ skills, unnamedSpend: null }, 'cost', 'most');

    expect(tiles.map((tile) => (tile.kind === 'skill' ? [tile.skill.name, tile.each, tile.heat] : null))).toEqual([
      ['beta', 3, 1],
      ['alpha', 1, 0],
      ['gamma', null, null],
    ]);
    expect(each).toEqual({ lowest: 1, highest: 3 });
  });

  it('keeps every tile cool when every Each is the same', () => {
    const skills = [skill('alpha', 10, 10), skill('beta', 20, 20)];

    const { tiles } = tilesOf({ skills, unnamedSpend: null }, 'cost', 'most');

    expect(tiles.map((tile) => tile.kind === 'skill' && tile.heat)).toEqual([0, 0]);
  });

  it('has no legend when no tile has an Each', () => {
    expect(tilesOf({ skills: [], unnamedSpend: null }, 'cost', 'most').each).toBeNull();
  });

  it('ranks every tile by its place in the chosen order', () => {
    const { tiles } = tilesOf({ skills: answered, unnamedSpend: null }, 'cost', 'least');

    expect(tiles.map((tile) => tile.rank)).toEqual([1, 2, 3]);
  });
});

describe('describeTile', () => {
  it('announces a skill tile by rank, name, Cost, Activations and Each', () => {
    const skills = [skill('grilling', 1.2, 1400), skill('tdd', 0.3, 1)];

    const [first] = tilesOf({ skills, unnamedSpend: null }, 'cost', 'most').tiles;

    expect(first && describeTile(first)).toBe('1. grilling. Cost $1.20. Activations 1,400. Each $0.0009.');
  });

  it('says not named, never free, for a skill whose spend Claude Code did not name', () => {
    const skills = [{ ...skill('probe', 0, 3), spend: null, averageCost: null }];

    const [first] = tilesOf({ skills, unnamedSpend: null }, 'activations', 'most').tiles;

    expect(first && describeTile(first)).toBe('1. probe. Cost Not named. Activations 3. Each Not named.');
  });

  it('leaves Each out for a skill that spent but never fired, as there is nothing to share its Cost across', () => {
    const [first] = tilesOf({ skills: [skill('gamma', 5, 0)], unnamedSpend: null }, 'cost', 'most').tiles;

    expect(first && describeTile(first)).toBe('1. gamma. Cost $5.00. Activations 0.');
  });

  it('announces Unnamed spend by rank and Cost, as it has no Activations', () => {
    const unnamedSpend = { cost: 15, inputTokens: 1, outputTokens: 2, cacheReadTokens: 3, cacheCreationTokens: 4 };

    const [first] = tilesOf({ skills: [], unnamedSpend }, 'cost', 'most').tiles;

    expect(first && describeTile(first)).toBe('1. Unnamed spend. Cost $15.00.');
  });
});

describe('heatStep', () => {
  it('marks the coolest third with one step, the middle with two and the hottest with three', () => {
    expect([0, 0.33, 0.34, 0.66, 0.67, 1].map(heatStep)).toEqual([1, 1, 2, 2, 3, 3]);
  });
});

describe('layOut', () => {
  it('lays the first tile in the chosen order in the top left corner', () => {
    const { tiles } = tilesOf({ skills: answered, unnamedSpend: null }, 'cost', 'least');

    const [first] = layOut(tiles, size);

    expect([nameOf(first?.tile), first?.x, first?.y]).toEqual(['alpha', 0, 0]);
  });

  for (const order of ['most', 'least'] as const) {
    it(`gives every tile at least 2% of the map when ordered ${order} first`, () => {
      const skills = [skill('alpha', 1000, 1), skill('beta', 1, 1), skill('gamma', 1, 1), skill('delta', 0.5, 1)];

      const placed = layOut(tilesOf({ skills, unnamedSpend: null }, 'cost', order).tiles, size);

      for (const tile of placed) {
        expect(tile.width * tile.height).toBeGreaterThanOrEqual(0.02 * 400 * 300 - 1e-6);
      }
    });
  }

  it('keeps a bigger tile bigger once the smallest are raised to the minimum', () => {
    const skills = [skill('alpha', 1000, 1), skill('beta', 100, 1), skill('gamma', 1, 1)];

    const placed = layOut(tilesOf({ skills, unnamedSpend: null }, 'cost', 'most').tiles, size);

    const [alpha, beta, gamma] = placed.map((tile) => tile.width * tile.height);
    expect(alpha).toBeGreaterThan(beta ?? 0);
    expect(beta).toBeGreaterThan(gamma ?? 0);
  });

  it('still sizes tiles by their figures on a map of more than fifty skills', () => {
    const skills = Array.from({ length: 60 }, (_, index) => skill(`skill-${String(index).padStart(2, '0')}`, index === 0 ? 500 : 0.01, 1));

    const placed = layOut(tilesOf({ skills, unnamedSpend: null }, 'cost', 'most').tiles, size);

    const [biggest, smallest] = [placed[0], placed.at(-1)].map((tile) => (tile ? tile.width * tile.height : 0));
    expect(biggest).toBeGreaterThan(10 * (smallest ?? 0));
  });

  it('lays out nothing when there is nothing to size', () => {
    const { tiles, unsized } = tilesOf({ skills: [], unnamedSpend: null }, 'cost', 'most');

    expect([tiles, unsized, layOut(tiles, size)]).toEqual([[], [], []]);
  });

  it('lays out nothing on a map with no room, as before the screen has measured it', () => {
    const { tiles } = tilesOf({ skills: answered, unnamedSpend: null }, 'cost', 'most');

    expect(layOut(tiles, { width: 0, height: 300 })).toEqual([]);
    expect(layOut(tiles, { width: 400, height: 0 })).toEqual([]);
  });

  it('fills the map with tiles that never overlap', () => {
    // Arrange
    const skills = [skill('alpha', 50, 5), skill('beta', 30, 3), skill('gamma', 10, 2), skill('delta', 6, 1), skill('epsilon', 4, 1)];

    // Act
    const placed = layOut(tilesOf({ skills, unnamedSpend: null }, 'cost', 'most').tiles, size);

    // Assert
    const area = placed.reduce((sum, tile) => sum + tile.width * tile.height, 0);
    expect(placed).toHaveLength(5);
    expect(area).toBeCloseTo(400 * 300, 6);

    for (const tile of placed) {
      expect(tile.x).toBeGreaterThanOrEqual(-1e-9);
      expect(tile.y).toBeGreaterThanOrEqual(-1e-9);
      expect(tile.x + tile.width).toBeLessThanOrEqual(400 + 1e-9);
      expect(tile.y + tile.height).toBeLessThanOrEqual(300 + 1e-9);
    }

    for (const [index, tile] of placed.entries()) {
      for (const other of placed.slice(index + 1)) {
        expect(overlap(tile, other)).toBeCloseTo(0, 6);
      }
    }
  });
});
