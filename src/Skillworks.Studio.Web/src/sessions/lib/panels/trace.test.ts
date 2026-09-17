import { describe, expect, it } from 'vitest';
import { deepestOf, noTreeWord, treeOf } from './trace';

function mark(id: string, startMs: number) {
  return { step: { id }, startMs };
}

const shape = <T extends { step: { id: string } }>(rows: readonly { mark: T; level: number }[]) =>
  rows.map((row) => `${'-'.repeat(row.level)}${row.mark.step.id}`);

describe('treeOf', () => {
  it('nests a step inside the step it ran inside', () => {
    const rows = treeOf([mark('turn', 10), mark('tool', 20)], { tool: 'turn' });

    expect(shape(rows)).toEqual(['turn', '-tool']);
  });

  it('nests a whole subtree beneath the call that started it', () => {
    const rows = treeOf([mark('call', 10), mark('inner', 20), mark('deeper', 30)], {
      inner: 'call',
      deeper: 'inner',
    });

    expect(shape(rows)).toEqual(['call', '-inner', '--deeper']);
  });

  it('sorts roots and the steps inside one by when they started', () => {
    const rows = treeOf([mark('late', 30), mark('early', 10), mark('inner', 20)], { inner: 'early' });

    expect(shape(rows)).toEqual(['early', '-inner', 'late']);
  });

  it('puts a step whose outer step is out of view at the root, so nothing in view is hidden', () => {
    const rows = treeOf([mark('inner', 20)], { inner: 'call' });

    expect(shape(rows)).toEqual(['inner']);
  });

  it('leaves a step that ran inside nothing at the root', () => {
    const rows = treeOf([mark('one', 10), mark('other', 20)], {});

    expect(shape(rows)).toEqual(['one', 'other']);
  });

  it('draws every step even where two name each other round a ring', () => {
    const rows = treeOf([mark('one', 10), mark('other', 20)], { one: 'other', other: 'one' });

    expect(rows.map((row) => row.mark.step.id).toSorted()).toEqual(['one', 'other']);
  });

  it('draws a step that names itself once and at the root', () => {
    const rows = treeOf([mark('one', 10)], { one: 'one' });

    expect(shape(rows)).toEqual(['one']);
  });

  it('draws nothing for a run with no steps', () => {
    expect(treeOf([], { tool: 'turn' })).toEqual([]);
  });
});

describe('deepestOf', () => {
  it('counts how many levels the tree goes down', () => {
    const rows = treeOf([mark('call', 10), mark('inner', 20), mark('deeper', 30)], {
      inner: 'call',
      deeper: 'inner',
    });

    expect(deepestOf(rows)).toBe(3);
  });

  it('counts no level in an empty tree', () => {
    expect(deepestOf([])).toBe(0);
  });
});

describe('noTreeWord', () => {
  it('says a thin run cannot know the tree, rather than reading as a run that nested nothing', () => {
    expect(noTreeWord('thin')).toBe('A thin run cannot say what ran inside what.');
  });

  it('says a full run whose View holds nothing ran nothing in it', () => {
    expect(noTreeWord('full')).toBe('Nothing ran in view.');
  });
});
