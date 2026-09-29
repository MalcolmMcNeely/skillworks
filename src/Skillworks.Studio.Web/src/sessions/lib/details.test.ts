import { describe, expect, it } from 'vitest';
import {
  describeAttempt,
  describeModel,
  describePurpose,
  describeStop,
  rowLineOf,
  timePartsOf,
  tokenPartsOf,
  type SideRequest,
  type TurnDetails,
} from './details';
import type { Step } from './steps';

function turn(details: Partial<TurnDetails> = {}): TurnDetails {
  return {
    purpose: 'work',
    side: null,
    sentAs: null,
    model: 'claude-opus-5',
    effort: null,
    speed: null,
    cost: 0,
    lengthMs: 0,
    firstWordMs: null,
    cacheReadTokens: 0,
    cacheWriteTokens: 0,
    inputTokens: 0,
    outputTokens: 0,
    words: null,
    wordsLength: null,
    stopReason: null,
    attempt: null,
    ...details,
  };
}

function step(kind: Step['kind'], words: string | null): Step {
  return {
    id: '7',
    kind,
    atUtc: '2026-09-28T09:00:00.000Z',
    lengthMs: 1_000,
    tool: kind === 'tool' ? 'Bash' : null,
    fault: false,
    words,
    skill: null,
    unnamed: false,
    skillKnown: true,
    cost: 0,
  };
}

describe('describePurpose', () => {
  it('says a turn sent for the prompt was work on it', () => {
    expect(describePurpose(turn())).toBe('Work on the Prompt');
  });

  it('says a turn a subagent sent was its work', () => {
    expect(describePurpose(turn({ purpose: 'subagent', sentAs: 'agent:custom' }))).toBe("Subagent's work");
  });

  it.each<[SideRequest, string]>([
    ['awaySummary', 'Recap while you were away'],
    ['promptSuggestion', 'Next-prompt suggestion'],
    ['sessionTitle', 'Session title'],
    ['compaction', 'Compaction'],
    ['subagentSummary', 'Subagent summary'],
    ['webPageRead', 'Web page read'],
    ['webSearch', 'Web search'],
  ])('names the side request %s in words', (side, words) => {
    expect(describePurpose(turn({ purpose: 'side', side }))).toBe(words);
  });

  it('gives claude codes own value beside a side request studio has no name for', () => {
    expect(describePurpose(turn({ purpose: 'side', side: 'other', sentAs: 'bespoke_request' }))).toBe(
      'Side request: bespoke_request',
    );
  });
});

describe('rowLineOf', () => {
  it('reads a turn as its purpose, its output tokens and its cost', () => {
    const turns = { '7': turn({ outputTokens: 1_200, cost: 0.42 }) };

    expect(rowLineOf(step('turn', 'claude-opus-5'), turns)).toBe('Work on the Prompt · 1.2K output tokens · $0.42');
  });

  it('starts a side requests row with its purpose', () => {
    const turns = { '7': turn({ purpose: 'side', side: 'awaySummary', outputTokens: 80, cost: 0.01 }) };

    expect(rowLineOf(step('turn', 'claude-opus-5'), turns)).toMatch(/^Recap while you were away · /);
  });

  it('shows what a turn shows today until the details arrive', () => {
    expect(rowLineOf(step('turn', 'claude-opus-5'), null)).toBe('claude-opus-5');
  });

  it('leaves a tool call with its own words', () => {
    expect(rowLineOf(step('tool', 'ShellError'), { '7': turn() })).toBe('ShellError');
  });
});

describe('describeModel', () => {
  it('gives the model and its effort', () => {
    expect(describeModel(turn({ effort: 'high', speed: 'normal' }))).toBe('claude-opus-5 · high effort');
  });

  it('adds the speed when it was not the normal one', () => {
    expect(describeModel(turn({ effort: 'high', speed: 'fast' }))).toBe('claude-opus-5 · high effort · fast');
  });

  it('says a model claude code did not name is not known', () => {
    expect(describeModel(turn({ model: null }))).toBe('Not known');
  });
});

describe('tokenPartsOf', () => {
  it('splits the tokens into read from cache, written to cache, new input and output', () => {
    const parts = tokenPartsOf(turn({ cacheReadTokens: 40_000, cacheWriteTokens: 3_000, inputTokens: 12, outputTokens: 800 }));

    expect(parts.map((part) => [part.word, part.tokens])).toEqual([
      ['Read from cache', 40_000],
      ['Written to cache', 3_000],
      ['New input', 12],
      ['Output', 800],
    ]);
  });
});

describe('timePartsOf', () => {
  it('sets the wait for the first word against the time spent writing', () => {
    const parts = timePartsOf(turn({ lengthMs: 5_000, firstWordMs: 1_400 }));

    expect(parts.map((part) => [part.word, part.ms])).toEqual([
      ['Wait for the first word', 1_400],
      ['Writing', 3_600],
    ]);
  });

  it('leaves both not known where claude code gave no wait', () => {
    expect(timePartsOf(turn({ lengthMs: 5_000 })).map((part) => part.ms)).toEqual([null, null]);
  });
});

describe('describeStop', () => {
  it.each([
    ['end_turn', 'Finished its reply'],
    ['tool_use', 'Asked for a tool'],
    ['max_tokens', 'Cut off at the output limit'],
    ['refusal', 'Refused'],
  ])('says a turn that stopped for %s in words', (stopReason, words) => {
    expect(describeStop(turn({ stopReason }))).toBe(words);
  });

  it('gives any other reason as claude code sent it', () => {
    expect(describeStop(turn({ stopReason: 'pause_turn' }))).toBe('pause_turn');
  });

  it('says why a turn with no span stopped is not known', () => {
    expect(describeStop(turn())).toBe('Not known');
  });
});

describe('describeAttempt', () => {
  it('says which attempt a retried turn was', () => {
    expect(describeAttempt(turn({ attempt: 3 }))).toBe('Attempt 3');
  });

  it('says the attempt of a turn with no span is not known', () => {
    expect(describeAttempt(turn())).toBe('Not known');
  });
});
