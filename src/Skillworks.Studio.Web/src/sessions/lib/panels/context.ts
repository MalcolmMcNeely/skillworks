import { missingWords } from '../../../shared/gaps/lib/gaps';

export interface ContextPoint {
  id: string;
  atUtc: string;
  lengthMs: number;
  tokens: number;
  writtenToCache: number;
  // Null both where no skill was in force and where Claude Code would not name the one that was.
  skill: string | null;
  unnamed: boolean;
  rebuilt: boolean;
}

export interface ContextPage {
  kind: 'context';
  points: ContextPoint[];
  // Null where the models a run named said nothing about the size of their window.
  limitTokens: number | null;
}

export interface Level {
  point: ContextPoint;
  startMs: number;
  endMs: number;
}

export function levelsOf(points: readonly ContextPoint[]): Level[] {
  return points.map((point) => {
    const startMs = Date.parse(point.atUtc);

    return { point, startMs, endMs: startMs + point.lengthMs };
  });
}

export function describeInForce(point: ContextPoint): string {
  return point.skill ?? (point.unnamed ? missingWords.notNamed : missingWords.none);
}

export interface ContextTally {
  turns: number;
  peakTokens: number;
  // Null where no limit is known, as a share of a limit nobody stated means nothing.
  peakShare: number | null;
  rebuilds: number;
}

export function tallyOf(levels: readonly Level[], limitTokens: number | null): ContextTally {
  const peakTokens = levels.reduce((peak, each) => Math.max(peak, each.point.tokens), 0);

  return {
    turns: levels.length,
    peakTokens,
    // Nothing to take a share of where no Turn ran, so an empty View never reads as nought percent.
    peakShare: limitTokens !== null && limitTokens > 0 && levels.length > 0 ? peakTokens / limitTokens : null,
    rebuilds: levels.filter((each) => each.point.rebuilt).length,
  };
}

// Drawing against the limit shows a run's headroom, and never below the peak, or a bar that broke the limit would clip.
export function ceilingOf(levels: readonly Level[], limitTokens: number | null): number {
  const peak = Math.max(1, ...levels.map((each) => each.point.tokens));

  return limitTokens === null || limitTokens <= 0 ? peak : Math.max(limitTokens, peak);
}

export interface InForce {
  label: string;
  // Places in the View, not moments, and both ends taken in.
  from: number;
  to: number;
}

// A long run would otherwise carry the same name on every point.
export function inForceBands(levels: readonly Level[]): InForce[] {
  const bands: InForce[] = [];

  levels.forEach((each, place) => {
    const label = describeInForce(each.point);
    const running = bands.at(-1);

    if (running !== undefined && running.label === label) {
      running.to = place;
    } else {
      bands.push({ label, from: place, to: place });
    }
  });

  return bands;
}
