import { describe, expect, it } from 'vitest';
import {
  breakdownLength,
  noBreakdownWord,
  shareOf,
  sharesOf,
  type Part,
  type PartSpell,
  type TimeBreakdownPage,
} from './timeBreakdown';

const at = (seconds: number) => new Date(seconds * 1_000).toISOString();

const spell = (part: Part, fromSeconds: number, toSeconds: number): PartSpell => ({
  part,
  atUtc: at(fromSeconds),
  lengthMs: (toSeconds - fromSeconds) * 1_000,
});

const page = (parts: PartSpell[], kinds: PartSpell[] = [], traced = true): TimeBreakdownPage => ({
  kind: 'timeBreakdown',
  traced,
  parts,
  kinds,
});

const msOf = (breakdown: TimeBreakdownPage, view: [number, number] | null = null) =>
  Object.fromEntries(
    sharesOf(breakdown, view)
      .filter((share) => share.ms > 0)
      .map((share) => [share.part, share.ms]),
  );

describe('sharesOf', () => {
  it('sums every part of a run and names all eight', () => {
    const breakdown = page([spell('model', 0, 5), spell('quiet', 5, 7), spell('tools', 7, 12)]);

    expect(sharesOf(breakdown, null)).toHaveLength(8);
    expect(msOf(breakdown)).toEqual({ model: 5_000, quiet: 2_000, tools: 5_000 });
  });

  // A row that comes and goes as a reader drags cannot be read across two Views of one run.
  it('names all eight even where a part took none of the run', () => {
    const shares = sharesOf(page([spell('model', 0, 10)]), null);

    expect(shares.map((share) => share.part)).toEqual([
      'waiting',
      'hooks',
      'tools',
      'model',
      'subagents',
      'side',
      'quiet',
      'yourTurn',
    ]);
  });

  it('breaks down only the View, clipping a spell that runs in and out of it', () => {
    const breakdown = page([spell('model', 0, 10), spell('tools', 10, 20)]);

    expect(msOf(breakdown, [5_000, 15_000])).toEqual({ model: 5_000, tools: 5_000 });
  });

  it('leaves out a spell the View does not reach', () => {
    const breakdown = page([spell('model', 0, 10), spell('tools', 20, 30)]);

    expect(msOf(breakdown, [0, 10_000])).toEqual({ model: 10_000 });
  });

  it('reads the overlapping sum of a kind beside the exclusive part', () => {
    const breakdown = page([spell('subagents', 0, 10)], [spell('subagents', 0, 30)]);
    const subagents = sharesOf(breakdown, null).find((share) => share.part === 'subagents');

    expect(subagents?.ms).toBe(10_000);
    expect(subagents?.overlapMs).toBe(30_000);
  });

  it('says the three parts only a span can tell are not known in a thin run', () => {
    const shares = sharesOf(page([spell('model', 0, 10)], [], false), null);
    const unknown = shares.filter((share) => !share.known).map((share) => share.part);

    expect(unknown).toEqual(['waiting', 'hooks', 'subagents']);
  });

  it('knows every part of a full run', () => {
    expect(sharesOf(page([spell('model', 0, 10)]), null).every((share) => share.known)).toBe(true);
  });

  it('knows no part at all before the Time breakdown has landed', () => {
    expect(sharesOf(null, null).every((share) => share.ms === 0 && !share.known)).toBe(true);
  });
});

describe('breakdownLength', () => {
  it('adds the parts up to the length of the run they break down', () => {
    const breakdown = page([spell('model', 0, 5), spell('quiet', 5, 7), spell('tools', 7, 12)]);

    expect(breakdownLength(sharesOf(breakdown, null))).toBe(12_000);
  });

  it('adds up to the View alone', () => {
    const breakdown = page([spell('model', 0, 10), spell('tools', 10, 20)]);

    expect(breakdownLength(sharesOf(breakdown, [2_000, 18_000]))).toBe(16_000);
  });
});

describe('noBreakdownWord', () => {
  it('says a run whose spans have not landed is still being read', () => {
    expect(noBreakdownWord(null)).toBe('Still reading the run.');
  });

  it('says a View nothing ran in held nothing', () => {
    expect(noBreakdownWord(page([]))).toBe('Nothing ran in view.');
  });
});

describe('shareOf', () => {
  it('reads a part as its share of the whole', () => {
    const shares = sharesOf(page([spell('model', 0, 5), spell('tools', 5, 20)]), null);
    const model = shares.find((share) => share.part === 'model')!;

    expect(shareOf(model, breakdownLength(shares))).toBe(0.25);
  });

  it('takes no share where nothing ran', () => {
    const shares = sharesOf(page([]), null);

    expect(shareOf(shares[0], breakdownLength(shares))).toBe(0);
  });
});
