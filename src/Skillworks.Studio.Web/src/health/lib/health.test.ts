import { describe, expect, it } from 'vitest';
import { describeHealth, describePart, troubled, type Part } from './health';

const working: Part = {
  name: 'Catalogue',
  state: 'working',
  detail: 'Reading skills from /home/me/skillworks/plugins.',
  action: null,
};

const down: Part = {
  name: 'Events store',
  state: 'broken',
  detail: 'http://localhost:3100/ could not be read: connection refused.',
  action: 'Start Studio’s containers with aspire run.',
};

const off: Part = {
  name: 'Claude Code telemetry',
  state: 'off',
  detail: 'Claude Code is not emitting telemetry.',
  action: 'Turn telemetry on in the Telemetry panel.',
};

describe('describePart', () => {
  it('says what is true and leaves it there when there is nothing to do', () => {
    expect(describePart(working)).toBe('✓ Catalogue: Reading skills from /home/me/skillworks/plugins.');
  });

  it('says what to do next when there is something to do', () => {
    expect(describePart(down)).toBe(
      '✕ Events store: http://localhost:3100/ could not be read: connection refused. ' +
        'Start Studio’s containers with aspire run.',
    );
  });

  it('marks a part that is deliberately off apart from one that is broken', () => {
    // Both empty the same screen, but only one is a fault worth looking for.
    expect(describePart(off).startsWith('○')).toBe(true);
    expect(describePart(down).startsWith('✕')).toBe(true);
  });

  it('marks a part that is still starting apart from one that has nothing to show', () => {
    expect(describePart({ ...working, state: 'starting' }).startsWith('…')).toBe(true);
  });
});

describe('troubled', () => {
  it('counts a part that is off among the ones that need attention', () => {
    // Nothing is broken, but a screen that listed only faults would leave the empty provenance column unexplained.
    expect(troubled([working, off])).toEqual([off]);
  });

  it('is empty when every part is doing its job', () => {
    expect(troubled([working])).toEqual([]);
  });
});

describe('describeHealth', () => {
  it('says so plainly when there is nothing to attend to', () => {
    expect(describeHealth([working])).toBe('Every part of Studio is working.');
  });

  it('names the one part that needs attention', () => {
    expect(describeHealth([working, down])).toBe('1 part of Studio needs attention: Events store.');
  });

  it('names every part that needs attention when more than one does', () => {
    expect(describeHealth([working, down, off])).toBe(
      '2 parts of Studio need attention: Events store, Claude Code telemetry.',
    );
  });
});
