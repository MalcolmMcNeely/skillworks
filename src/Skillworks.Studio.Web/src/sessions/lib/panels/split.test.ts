import { describe, expect, it } from 'vitest';
import type { Depth } from './agents';
import { noSplitWord, shareOf, sharesOf, splitLength, type Spell, type SplitPage, type SplitPart } from './split';

const at = (seconds: number) => new Date(seconds * 1_000).toISOString();

const spell = (part: SplitPart, fromSeconds: number, toSeconds: number): Spell => ({
  part,
  atUtc: at(fromSeconds),
  lengthMs: (toSeconds - fromSeconds) * 1_000,
});

const page = (parts: Spell[], kinds: Spell[] = [], depth: Depth = 'full'): SplitPage => ({
  kind: 'split',
  depth,
  parts,
  kinds,
});

const msOf = (split: SplitPage, range: [number, number] | null = null) =>
  Object.fromEntries(
    sharesOf(split, range)
      .filter((share) => share.ms > 0)
      .map((share) => [share.part, share.ms]),
  );

describe('sharesOf', () => {
  it('sums every part of a run and names all eight', () => {
    const split = page([spell('model', 0, 5), spell('quiet', 5, 7), spell('tools', 7, 12)]);

    expect(sharesOf(split, null)).toHaveLength(8);
    expect(msOf(split)).toEqual({ model: 5_000, quiet: 2_000, tools: 5_000 });
  });

  // A row that comes and goes as a reader brushes cannot be read across two stretches of one run.
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

  it('splits only the brushed stretch, clipping a spell that runs in and out of it', () => {
    const split = page([spell('model', 0, 10), spell('tools', 10, 20)]);

    expect(msOf(split, [5_000, 15_000])).toEqual({ model: 5_000, tools: 5_000 });
  });

  it('leaves out a spell the brushed stretch does not reach', () => {
    const split = page([spell('model', 0, 10), spell('tools', 20, 30)]);

    expect(msOf(split, [0, 10_000])).toEqual({ model: 10_000 });
  });

  it('reads the overlapping sum of a kind beside the exclusive part', () => {
    const split = page([spell('subagents', 0, 10)], [spell('subagents', 0, 30)]);
    const subagents = sharesOf(split, null).find((share) => share.part === 'subagents');

    expect(subagents?.ms).toBe(10_000);
    expect(subagents?.overlapMs).toBe(30_000);
  });

  it('says the three parts only a span can tell are not known in a thin run', () => {
    const shares = sharesOf(page([spell('model', 0, 10)], [], 'thin'), null);
    const unknown = shares.filter((share) => !share.known).map((share) => share.part);

    expect(unknown).toEqual(['waiting', 'hooks', 'subagents']);
  });

  it('knows every part of a full run', () => {
    expect(sharesOf(page([spell('model', 0, 10)]), null).every((share) => share.known)).toBe(true);
  });

  it('knows no part at all before the split has landed', () => {
    expect(sharesOf(null, null).every((share) => share.ms === 0 && !share.known)).toBe(true);
  });
});

describe('splitLength', () => {
  it('adds the parts up to the length of the stretch they split', () => {
    const split = page([spell('model', 0, 5), spell('quiet', 5, 7), spell('tools', 7, 12)]);

    expect(splitLength(sharesOf(split, null))).toBe(12_000);
  });

  it('adds up to the brushed stretch alone', () => {
    const split = page([spell('model', 0, 10), spell('tools', 10, 20)]);

    expect(splitLength(sharesOf(split, [2_000, 18_000]))).toBe(16_000);
  });
});

describe('noSplitWord', () => {
  it('says a run whose spans have not landed is still being read', () => {
    expect(noSplitWord(null)).toBe('Still reading the run.');
  });

  it('says a stretch nothing ran in held nothing', () => {
    expect(noSplitWord(page([]))).toBe('Nothing ran in this stretch.');
  });
});

describe('shareOf', () => {
  it('reads a part as its share of the stretch', () => {
    const shares = sharesOf(page([spell('model', 0, 5), spell('tools', 5, 20)]), null);
    const model = shares.find((share) => share.part === 'model')!;

    expect(shareOf(model, splitLength(shares))).toBe(0.25);
  });

  it('takes no share of a stretch nothing ran in', () => {
    const shares = sharesOf(page([]), null);

    expect(shareOf(shares[0], splitLength(shares))).toBe(0);
  });
});
