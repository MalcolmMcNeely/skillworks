import { describe, expect, it } from 'vitest';
import type { Activation } from './panels/activations';
import type { ContextPoint } from './panels/context';
import type { Exchange } from './panels/conversation';
import type { Session } from './sessions';
import {
  describeClock,
  foldSessionLine,
  lanes,
  lanesOf,
  marksOf,
  noteOf,
  runSpan,
  titleOf,
  toneOf,
  type SessionAnswer,
  type Step,
} from './steps';

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

function step(fields: Partial<Step> & Pick<Step, 'id' | 'kind' | 'atUtc'>): Step {
  return { lengthMs: 0, tool: null, fault: false, words: null, ...fields };
}

const prompt = step({ id: '1', kind: 'prompt', atUtc: '2026-09-14T09:00:00.000Z', words: 'Fix the build' });

const said: Exchange = {
  index: 0,
  atUtc: '2026-09-14T09:00:00.000Z',
  lengthMs: 10_000,
  prompt: 'Fix the build',
  promptLength: 13,
  answer: 'Built.',
  answerLength: 6,
  turns: 1,
  toolCalls: 2,
  cost: 0.42,
};

const fired: Activation = {
  id: '7',
  skill: 'tdd',
  atUtc: '2026-09-14T09:00:00.000Z',
  followedMs: 300_000,
  trigger: 'user-slash',
};

const sent: ContextPoint = {
  id: '9',
  atUtc: '2026-09-14T09:00:00.000Z',
  lengthMs: 2_000,
  tokens: 420_000,
  writtenToCache: 0,
  skill: 'tdd',
  unnamed: false,
  rebuilt: false,
};

const opened: SessionAnswer = foldSessionLine(null, { kind: 'head', session: run });

describe('foldSessionLine', () => {
  it('opens on the run, so the crumb and the figures draw before the steps land', () => {
    expect(opened.session).toEqual(run);
    expect(opened.steps).toEqual([]);
    expect(opened.landed).toBe(false);
    expect(opened.arriving).toBe(true);
  });

  it('takes the steps and marks them landed, so the timeline draws before the answer ends', () => {
    const answer = foldSessionLine(opened, { kind: 'steps', steps: [prompt] });

    expect(answer.steps).toEqual([prompt]);
    expect(answer.landed).toBe(true);
    expect(answer.arriving).toBe(true);
  });

  it('marks a run with no steps landed too, so an empty timeline is told apart from one still to come', () => {
    expect(foldSessionLine(opened, { kind: 'steps', steps: [] }).landed).toBe(true);
  });

  it('takes the exchanges, so the conversation reads what the timeline is already drawing', () => {
    const answer = foldSessionLine(foldSessionLine(opened, { kind: 'steps', steps: [prompt] }), {
      kind: 'exchanges',
      exchanges: [said],
    });

    expect(answer.exchanges).toEqual([said]);
    expect(answer.steps).toEqual([prompt]);
  });

  it('takes the activations, so the panel reads what the timeline is already drawing', () => {
    const answer = foldSessionLine(foldSessionLine(opened, { kind: 'steps', steps: [prompt] }), {
      kind: 'activations',
      activations: [fired],
    });

    expect(answer.activations).toEqual([fired]);
    expect(answer.steps).toEqual([prompt]);
  });

  it('takes the context and the limit, so the panel reads what the timeline is already drawing', () => {
    const answer = foldSessionLine(foldSessionLine(opened, { kind: 'steps', steps: [prompt] }), {
      kind: 'context',
      points: [sent],
      limitTokens: 1_000_000,
    });

    expect(answer.context).toEqual([sent]);
    expect(answer.limitTokens).toBe(1_000_000);
    expect(answer.steps).toEqual([prompt]);
  });

  it('keeps a limit no model named out of the answer, so a share is never read off a guess', () => {
    const answer = foldSessionLine(opened, { kind: 'context', points: [sent], limitTokens: null });

    expect(answer.limitTokens).toBeNull();
  });

  it('opens thin, so a panel that needs a span never reads a missing figure as a zero', () => {
    expect(opened.depth).toBe('thin');
    expect(opened.agents).toEqual({});
  });

  it('takes which agent ran each step and raises the run to full, as the second part of one read', () => {
    const answer = foldSessionLine(foldSessionLine(opened, { kind: 'steps', steps: [prompt] }), {
      kind: 'agents',
      depth: 'full',
      agents: { '4': 'agent-a' },
      subagents: [],
    });

    expect(answer.depth).toBe('full');
    expect(answer.agents).toEqual({ '4': 'agent-a' });
    expect(answer.steps).toEqual([prompt]);
    expect(answer.arriving).toBe(true);
  });

  it('ends the answer and keeps a gap for each store', () => {
    const answer = foldSessionLine(opened, {
      kind: 'end',
      events: { kind: 'complete', missing: null },
      traces: { kind: 'quiet', missing: 'The trace store holds nothing for this run.' },
    });

    expect(answer.arriving).toBe(false);
    expect(answer.events).toEqual({ kind: 'complete', missing: null });
    expect(answer.traces?.kind).toBe('quiet');
  });

  it('carries no run where the store holds none, so a mistyped address says so', () => {
    expect(foldSessionLine(null, { kind: 'head', session: null }).session).toBeNull();
  });

  it('refuses a line before the head, as a step with no run says nothing about where it sat', () => {
    expect(() => foldSessionLine(null, { kind: 'steps', steps: [prompt] })).toThrow(/starts with its head/);
  });
});

describe('marksOf', () => {
  it('places a step by when it began and how long it took', () => {
    const [mark] = marksOf([step({ id: '2', kind: 'tool', atUtc: '2026-09-14T09:00:06.000Z', lengthMs: 4_000 })]);

    expect(mark.startMs).toBe(Date.parse('2026-09-14T09:00:06.000Z'));
    expect(mark.endMs).toBe(Date.parse('2026-09-14T09:00:10.000Z'));
  });
});

describe('runSpan', () => {
  it('covers the whole run, from the first step to the end of the last', () => {
    const marks = marksOf([
      prompt,
      step({ id: '2', kind: 'tool', atUtc: '2026-09-14T09:00:06.000Z', lengthMs: 4_000 }),
    ]);

    expect(runSpan(marks)).toEqual([Date.parse('2026-09-14T09:00:00.000Z'), Date.parse('2026-09-14T09:00:10.000Z')]);
  });

  it('covers a step that started before the one written before it', () => {
    const marks = marksOf([
      step({ id: '1', kind: 'tool', atUtc: '2026-09-14T09:00:09.000Z', lengthMs: 1_000 }),
      step({ id: '2', kind: 'turn', atUtc: '2026-09-14T09:00:02.000Z', lengthMs: 2_000 }),
    ]);

    expect(runSpan(marks)?.[0]).toBe(Date.parse('2026-09-14T09:00:02.000Z'));
  });

  it('says a run with no steps has no bounds to draw', () => {
    expect(runSpan([])).toBeNull();
  });
});

describe('lanesOf', () => {
  it('puts a prompt in the prompts lane', () => {
    expect(lanesOf(prompt)).toEqual(['prompt']);
  });

  it('puts a turn and an answer in the model lane', () => {
    expect(lanesOf(step({ id: '2', kind: 'turn', atUtc: '2026-09-14T09:00:01.000Z' }))).toEqual(['model']);
    expect(lanesOf(step({ id: '3', kind: 'answer', atUtc: '2026-09-14T09:00:02.000Z' }))).toEqual(['model']);
  });

  it('puts a tool call in the lane of what the tool does', () => {
    const laneOf = (tool: string) => lanesOf(step({ id: '4', kind: 'tool', atUtc: '2026-09-14T09:00:03.000Z', tool }));

    expect(laneOf('Bash')).toEqual(['shell']);
    expect(laneOf('Write')).toEqual(['edit']);
    expect(laneOf('Grep')).toEqual(['read']);
  });

  it('puts a tool nobody has named in other tools, as Studio never guesses what a tool does', () => {
    expect(lanesOf(step({ id: '5', kind: 'tool', atUtc: '2026-09-14T09:00:04.000Z', tool: 'Artifact' }))).toEqual(['tool']);
    expect(lanesOf(step({ id: '6', kind: 'tool', atUtc: '2026-09-14T09:00:04.000Z' }))).toEqual(['tool']);
  });

  it('puts a failed tool call in its own lane and in faults, so the faults lane alone says what went wrong', () => {
    const failed = step({ id: '7', kind: 'tool', atUtc: '2026-09-14T09:00:05.000Z', tool: 'Bash', fault: true });

    expect(lanesOf(failed)).toEqual(['shell', 'fault']);
  });

  it('puts a model fault in faults alone', () => {
    expect(lanesOf(step({ id: '8', kind: 'fault', atUtc: '2026-09-14T09:00:06.000Z', fault: true }))).toEqual(['fault']);
  });

  it('keeps a refused tool call out of faults, as somebody chose it', () => {
    const refused = step({ id: '9', kind: 'refused', atUtc: '2026-09-14T09:00:07.000Z', tool: 'Bash' });

    expect(lanesOf(refused)).toEqual(['shell']);
  });

  it('names a lane for every key a step can sit in', () => {
    const keys = lanes.map((lane) => lane.key);

    expect(keys).toEqual(['prompt', 'model', 'shell', 'edit', 'read', 'tool', 'fault']);
    expect(lanes.every((lane) => lane.label !== '')).toBe(true);
  });
});

describe('toneOf', () => {
  it('draws a turn and an answer as the model, and a tool call as a tool', () => {
    expect(toneOf(step({ id: '1', kind: 'turn', atUtc: '2026-09-14T09:00:00.000Z' }))).toBe('model');
    expect(toneOf(step({ id: '2', kind: 'answer', atUtc: '2026-09-14T09:00:00.000Z' }))).toBe('model');
    expect(toneOf(step({ id: '3', kind: 'tool', atUtc: '2026-09-14T09:00:00.000Z', tool: 'Bash' }))).toBe('tool');
  });

  it('draws a failed tool call as a fault in its own lane too, so it reads failed where it happened', () => {
    const failed = step({ id: '4', kind: 'tool', atUtc: '2026-09-14T09:00:00.000Z', tool: 'Bash', fault: true });

    expect(toneOf(failed)).toBe('fault');
    expect(lanesOf(failed)).toEqual(['shell', 'fault']);
  });

  it('draws a model fault as a fault', () => {
    expect(toneOf(step({ id: '5', kind: 'fault', atUtc: '2026-09-14T09:00:00.000Z', fault: true }))).toBe('fault');
  });

  it('draws a refusal apart from a fault, as somebody chose it', () => {
    expect(toneOf(step({ id: '6', kind: 'refused', atUtc: '2026-09-14T09:00:00.000Z', tool: 'Bash' }))).toBe('refused');
  });

  it('draws a prompt as a tool rather than as nothing, so no mark is ever unpainted', () => {
    expect(toneOf(prompt)).toBe('tool');
  });
});

describe('the words on a mark', () => {
  it('names a tool call by its tool', () => {
    expect(titleOf(step({ id: '1', kind: 'tool', atUtc: '2026-09-14T09:00:00.000Z', tool: 'Bash' }))).toBe('Bash');
  });

  it('names a step with no tool by what kind of step it was', () => {
    expect(titleOf(prompt)).toBe('Prompt');
    expect(titleOf(step({ id: '2', kind: 'fault', atUtc: '2026-09-14T09:00:00.000Z', fault: true }))).toBe('Model fault');
  });

  it('says a tool call failed, and says a refused one was refused', () => {
    expect(noteOf(step({ id: '1', kind: 'tool', atUtc: '2026-09-14T09:00:00.000Z', tool: 'Bash', fault: true }))).toBe('Failed');
    expect(noteOf(step({ id: '2', kind: 'refused', atUtc: '2026-09-14T09:00:00.000Z', tool: 'Bash' }))).toBe('Refused');
  });

  it('says nothing about a step that went well', () => {
    expect(noteOf(prompt)).toBeNull();
  });
});

describe('describeClock', () => {
  it('shows the UTC time, so a step and the day it sits in count the same hours', () => {
    expect(describeClock(Date.parse('2026-09-14T09:07:03.000Z'))).toBe('09:07');
  });

  it('shows the seconds when a reader is looking at one step', () => {
    expect(describeClock(Date.parse('2026-09-14T09:07:03.000Z'), true)).toBe('09:07:03');
  });
});
