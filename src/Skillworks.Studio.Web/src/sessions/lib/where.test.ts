import { describe, expect, it } from 'vitest';
import { readFilter } from '../../shared/filters/lib/filters';
import { nowhere, readWhere, sessionAddress, withWhere } from './where';

const run = '8f1c0a9e-0000-4000-8000-000000000001';

describe('readWhere', () => {
  it('reads the exchange, the activation, the step and the subagent a link named', () => {
    expect(readWhere(new URLSearchParams('exchange=2&activation=7&step=41&agent=agent-a'))).toEqual({
      exchange: 2,
      activation: '7',
      step: '41',
      agent: 'agent-a',
    });
  });

  it('opens no activation for an older link that still names one the old way', () => {
    expect(readWhere(new URLSearchParams('call=7')).activation).toBeNull();
  });

  it('reads nothing where the address names nothing, so an unopened run reads as the whole run', () => {
    expect(readWhere(new URLSearchParams(''))).toEqual(nowhere);
  });

  it('refuses an exchange a hand-typed address got wrong, rather than opening the first one', () => {
    expect(readWhere(new URLSearchParams('exchange=second')).exchange).toBeNull();
    expect(readWhere(new URLSearchParams('exchange=-1')).exchange).toBeNull();
    expect(readWhere(new URLSearchParams('exchange=1.5')).exchange).toBeNull();
  });

  it('reads the first exchange, as counting from nought is how the answer counts them', () => {
    expect(readWhere(new URLSearchParams('exchange=0')).exchange).toBe(0);
  });

  it('leaves the repository to the Filter, which is the one thing that reads it', () => {
    const shown = new URLSearchParams('repository=acme%2Fxi&step=41');

    expect(readFilter(shown).repository).toBe('acme/xi');
    expect(Object.keys(readWhere(shown))).toEqual(['exchange', 'activation', 'step', 'agent']);
  });
});

describe('withWhere', () => {
  it('writes where the reader is, so a reload lands in the same place', () => {
    const where = { exchange: 2, activation: '7', step: '41', agent: 'agent-a' };

    expect(readWhere(withWhere(new URLSearchParams(''), where))).toEqual(where);
  });

  it('takes a step, an activation and a subagent off the address when the reader closes them', () => {
    expect(withWhere(new URLSearchParams('step=41&exchange=2&activation=7&agent=agent-a'), nowhere).toString()).toBe('');
  });

  it('keeps the parameters it was given, so opening a step never throws the span or the repository away', () => {
    const written = withWhere(new URLSearchParams('from=2026-09-14&repository=acme%2Fxi'), {
      ...nowhere,
      step: '41',
    });

    expect(written.get('from')).toBe('2026-09-14');
    expect(written.get('repository')).toBe('acme/xi');
    expect(written.get('step')).toBe('41');
  });
});

describe('sessionAddress', () => {
  it('names the run in the path and carries the table the reader came from in the query', () => {
    const address = sessionAddress(run, nowhere, new URLSearchParams('from=2026-09-14&to=2026-09-14'));

    expect(address).toBe(`/sessions/${run}?from=2026-09-14&to=2026-09-14`);
  });

  it('leaves the query off when there is nothing to say, so an opened run has a clean address to share', () => {
    expect(sessionAddress(run, nowhere, new URLSearchParams(''))).toBe(`/sessions/${run}`);
  });
});
