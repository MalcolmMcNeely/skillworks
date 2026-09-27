import { describe, expect, it } from 'vitest';
import type { Finding } from './findings';
import type { TimeBreakdownPage } from './timeBreakdown';
import type { Subagent } from '../timeline/agents';
import type { ContextPoint } from '../timeline/context';
import type { Exchange } from '../timeline/conversation';
import type { Session } from '../sessions';
import { foldSessionLine, type SessionAnswer, type Step } from '../steps';
import { headlinesOf, verdictOf } from './verdict';

const run: Session = {
  id: '8f1c0a9e-0000-4000-8000-000000000001',
  startedUtc: '2026-09-14T09:00:00+00:00',
  repository: 'malcolmania/skillworks',
  person: 'ada@acme.test',
  name: 'Fixing the failing build',
  lengthMs: 2_460_000,
  running: false,
  toolCalls: 42,
  cost: 1.25,
  faults: 3,
  friction: 2,
};

function step(id: string, fields: Partial<Step> = {}): Step {
  return {
    id,
    kind: 'tool',
    atUtc: '2026-09-14T09:00:00.000Z',
    lengthMs: 0,
    tool: 'Bash',
    fault: false,
    words: null,
    skill: null,
    unnamed: false,
    skillKnown: true,
    cost: 0,
    ...fields,
  };
}

function point(id: string, tokens: number): ContextPoint {
  return {
    id,
    atUtc: '2026-09-14T09:00:00.000Z',
    lengthMs: 2_000,
    tokens,
    writtenToCache: 0,
    skill: null,
    unnamed: false,
    rebuilt: false,
  };
}

const finding = (figure: number | null, over: Partial<Finding> = {}): Finding => ({
  kind: 'failingAgain',
  subject: null,
  figure,
  bar: 3,
  step: null,
  atUtc: '2026-09-14T09:00:00.000Z',
  lengthMs: 5_000,
  ...over,
});

function answerOf({
  steps = [],
  points = [],
  limitTokens = null,
  findings,
}: {
  steps?: Step[];
  points?: ContextPoint[];
  limitTokens?: number | null;
  findings?: Finding[];
}): SessionAnswer {
  const opened = foldSessionLine(null, { kind: 'head', session: run });
  const stepped = foldSessionLine(opened, { kind: 'steps', steps });
  const measured = foldSessionLine(stepped, { kind: 'context', points, limitTokens });

  return findings === undefined ? measured : foldSessionLine(measured, { kind: 'findings', findings });
}

const headline = (answer: SessionAnswer, name: string) => headlinesOf(answer).find((each) => each.name === name);

describe('headlinesOf', () => {
  it('shows the headlines in the order a reader scans a run', () => {
    expect(headlinesOf(answerOf({ findings: [] })).map((each) => each.name)).toEqual([
      'Length',
      'Cost',
      'Tool calls',
      'Faults',
      'Peak context',
      'Findings',
    ]);
  });

  it('reads the length, the cost and the tool calls off the run', () => {
    const answer = answerOf({ findings: [] });

    expect(headline(answer, 'Length')?.figure).toBe('41m');
    expect(headline(answer, 'Cost')?.figure).toBe('$1.25');
    expect(headline(answer, 'Tool calls')?.figure).toBe('42');
  });

  it('counts the steps with a fault, and raises the alarm for one', () => {
    const answer = answerOf({ steps: [step('1', { fault: true }), step('2'), step('3', { kind: 'fault', tool: null, fault: true })] });

    expect(headline(answer, 'Faults')).toMatchObject({ figure: '2', alarm: true });
  });

  it('keeps a run with no fault calm', () => {
    expect(headline(answerOf({ steps: [step('1')] }), 'Faults')).toMatchObject({ figure: '0', alarm: false });
  });

  it('keeps a refused call out of the faults, as somebody chose it', () => {
    expect(headline(answerOf({ steps: [step('1', { kind: 'refused' })] }), 'Faults')?.figure).toBe('0');
  });

  it('reads the peak context as a share of a stated limit, and raises the alarm above four fifths of it', () => {
    const answer = answerOf({ points: [point('1', 850_000)], limitTokens: 1_000_000 });

    expect(headline(answer, 'Peak context')).toMatchObject({ figure: '85%', alarm: true });
  });

  it('reads the peak context in tokens where no limit was stated, and says so beneath', () => {
    const answer = answerOf({ points: [point('1', 850_000)] });

    expect(headline(answer, 'Peak context')).toEqual({
      name: 'Peak context',
      figure: '850K tokens',
      note: 'limit not known',
      alarm: false,
    });
  });

  it('counts the findings that were measured, and raises the alarm for one', () => {
    const answer = answerOf({ findings: [finding(4), finding(null, { kind: 'hooks' })] });

    expect(headline(answer, 'Findings')).toMatchObject({ figure: '1', alarm: true });
  });

  it('keeps a run whose only finding nobody could measure calm, as it crossed no bar anyone saw', () => {
    expect(headline(answerOf({ findings: [finding(null)] }), 'Findings')).toMatchObject({ figure: '0', alarm: false });
  });

  it('says the findings are not known before they land, rather than reading as none', () => {
    expect(headline(answerOf({}), 'Findings')).toMatchObject({ figure: 'Not known', alarm: false });
  });

  it('shows no headline for a run the store does not hold', () => {
    expect(headlinesOf(foldSessionLine(null, { kind: 'head', session: null }))).toEqual([]);
  });
});

describe('verdictOf', () => {
  const exchange: Exchange = {
    index: 0,
    atUtc: '2026-09-14T09:00:10.000Z',
    lengthMs: 60_000,
    prompt: 'Fix the build',
    promptLength: 13,
    answer: 'Fixed',
    answerLength: 5,
    turns: 3,
    toolCalls: 4,
    cost: 1,
    subagents: [{ agent: 'a1', cost: 0.4 }],
  };

  const subagent: Subagent = {
    id: 'a1',
    name: 'Explore',
    type: 'Explore',
    atUtc: '2026-09-14T09:00:20.000Z',
    lengthMs: 20_000,
    toolCalls: 2,
    cost: 0.4,
    faults: 0,
    brief: null,
    report: null,
  };

  const breakdown: TimeBreakdownPage = { kind: 'timeBreakdown', traced: true, parts: [], kinds: [] };

  function fullAnswer(): SessionAnswer {
    const measured = answerOf({
      steps: [step('1', { fault: true })],
      points: [point('1', 850_000)],
      limitTokens: 1_000_000,
      findings: [finding(4, { step: '1' })],
    });
    const exchanged = foldSessionLine(measured, { kind: 'exchanges', exchanges: [exchange], beforeFirstPrompt: 0.25 });
    const agented = foldSessionLine(exchanged, {
      kind: 'agents',
      depth: 'full',
      traced: true,
      agents: { '1': 'a1' },
      subagents: [subagent],
    });

    return foldSessionLine(agented, breakdown);
  }

  it('gives every figure of the Verdict from the answer alone, with no View to pass', () => {
    const answer = fullAnswer();

    const verdict = verdictOf(answer);

    expect(verdict.headlines.map((each) => [each.name, each.figure])).toEqual([
      ['Length', '41m'],
      ['Cost', '$1.25'],
      ['Tool calls', '42'],
      ['Faults', '1'],
      ['Peak context', '85%'],
      ['Findings', '1'],
    ]);
    expect(verdict.findings).toEqual(answer.findings);
    expect(verdict.timeBreakdown).toBe(breakdown);
    expect(verdict.costs?.bars.map((bar) => [bar.word, bar.cost, bar.ownCost])).toEqual([
      ['Exchange 1', 1, 0.6],
      ['Before the first Prompt', 0.25, 0.25],
    ]);
    expect(verdict.costs?.bars[0].subagents).toEqual([{ agent: 'a1', name: 'Explore', cost: 0.4 }]);
  });

  it('reads the whole run, as it takes no View a drag could change', () => {
    expect(verdictOf).toHaveLength(1);
  });

  it('has no Cost breakdown for a run with no Exchange', () => {
    expect(verdictOf(answerOf({})).costs).toBeNull();
  });

  it('has no Time breakdown and no Findings before the spans land, rather than empty ones', () => {
    const verdict = verdictOf(answerOf({}));

    expect(verdict.timeBreakdown).toBeNull();
    expect(verdict.findings).toBeNull();
  });
});
