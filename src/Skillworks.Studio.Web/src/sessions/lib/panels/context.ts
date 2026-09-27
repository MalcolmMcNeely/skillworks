import { describeShare, describeTokens } from '../../../shared/figures/lib/figures';
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

// A point carries the id of the Turn it was sent on, so the agents that name a Step name its point too.
export function levelsRanByOne(levels: readonly Level[], agents: Record<string, string>, agent: string | null): Level[] {
  return agent === null ? [...levels] : levels.filter((level) => agents[level.point.id] === agent);
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

export const limitNotKnown = 'limit not known';

// Claude Code starts cutting a run down as its window nears full, so the last fifth is where a reader should look.
const highShare = 0.8;

export interface PeakContext {
  figure: string;
  note: string | null;
  high: boolean;
}

// Said rather than guessed: a limit no model stated is unknown, and it is never read off the run's own peak.
export function peakContextOf(levels: readonly Level[], limitTokens: number | null): PeakContext {
  const tally = tallyOf(levels, limitTokens);
  const note = limitTokens === null ? limitNotKnown : `of ${describeTokens(limitTokens)} tokens`;

  if (tally.peakShare === null) {
    return { figure: `${describeTokens(tally.peakTokens)} tokens`, note, high: false };
  }

  return { figure: describeShare(tally.peakShare), note, high: tally.peakShare > highShare };
}
