import { describe, expect, it } from 'vitest';
import {
  describeAllowedBy,
  describeAttempt,
  describeModel,
  describeOutcome,
  describeOutputNote,
  describePurpose,
  describeStop,
  describeWithheld,
  fileOf,
  outputOf,
  rowLineOf,
  timePartsOf,
  tokenPartsOf,
  toolTimePartsOf,
  whatItDid,
  type SideRequest,
  type ToolDetails,
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

function tool(details: Partial<ToolDetails> = {}): ToolDetails {
  return {
    tool: 'Bash',
    passed: true,
    error: null,
    input: null,
    inputBytes: null,
    parameters: null,
    command: null,
    description: null,
    resultBytes: null,
    allowedBy: 'config',
    traced: true,
    output: null,
    diff: null,
    waitedMs: null,
    ranMs: null,
    hooksBefore: null,
    hooksAfter: null,
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

    expect(rowLineOf(step('turn', 'claude-opus-5'), turns, null)).toBe('Work on the Prompt · 1.2K output tokens · $0.42');
  });

  it('starts a side requests row with its purpose', () => {
    const turns = { '7': turn({ purpose: 'side', side: 'awaySummary', outputTokens: 80, cost: 0.01 }) };

    expect(rowLineOf(step('turn', 'claude-opus-5'), turns, null)).toMatch(/^Recap while you were away · /);
  });

  it('shows what a turn shows today until the details arrive', () => {
    expect(rowLineOf(step('turn', 'claude-opus-5'), null, null)).toBe('claude-opus-5');
  });

  it('shows what a tool call shows today until the details arrive', () => {
    expect(rowLineOf(step('tool', 'ShellError'), { '7': turn() }, null)).toBe('ShellError');
  });

  it('reads a tool call as what it did', () => {
    const tools = { '7': tool({ description: 'Build the solution' }) };

    expect(rowLineOf(step('tool', null), null, tools)).toBe('Build the solution');
  });
});

describe('whatItDid', () => {
  it('reads a bash call as its description', () => {
    expect(whatItDid(tool({ command: 'dotnet build', description: 'Build the solution' }))).toBe('Build the solution');
  });

  it('reads a bash call with no description as its command', () => {
    expect(whatItDid(tool({ command: 'dotnet build' }))).toBe('dotnet build');
  });

  it('reads a bash call whose command was kept back as withheld with its size', () => {
    expect(whatItDid(tool({ inputBytes: 812 }))).toBe('Withheld · 812 bytes');
  });

  it.each(['Edit', 'Write', 'Read', 'MultiEdit', 'NotebookEdit'])('reads a call of %s as the file it touched', (name) => {
    expect(whatItDid(tool({ tool: name, input: '{"file_path":"src/Clock.cs","old_string":"a"}' }))).toBe('src/Clock.cs');
  });

  it('reads a notebook edit as the notebook it touched', () => {
    expect(whatItDid(tool({ tool: 'NotebookEdit', input: '{"notebook_path":"study.ipynb"}' }))).toBe('study.ipynb');
  });

  it('reads a call of Skill as the skill it started', () => {
    expect(whatItDid(tool({ tool: 'Skill', input: '{"skill":"skillworks:tdd","args":"494"}' }))).toBe('skillworks:tdd');
  });

  it('reads a call of Skill with no input as the skill its parameters named', () => {
    expect(whatItDid(tool({ tool: 'Skill', parameters: '{"skill_name":"skillworks:tdd"}' }))).toBe('skillworks:tdd');
  });

  it.each(['Grep', 'Glob'])('reads a call of %s as the pattern it searched', (name) => {
    expect(whatItDid(tool({ tool: name, input: '{"pattern":"TimeProvider","path":"src"}' }))).toBe('TimeProvider');
  });

  it.each(['Agent', 'Task'])('reads a call of %s as the description of its subagent', (name) => {
    expect(whatItDid(tool({ tool: name, input: '{"description":"Find the clock reads","prompt":"Look"}' }))).toBe(
      'Find the clock reads',
    );
  });

  it('reads a call of any other tool as the start of its input', () => {
    const input = `{"url":"https://example.com/${'a'.repeat(200)}"}`;

    expect(whatItDid(tool({ tool: 'WebFetch', input }))).toBe(`{"url":"https://example.com/${'a'.repeat(52)}…`);
  });

  it('reads a short input of any other tool whole', () => {
    expect(whatItDid(tool({ tool: 'WebSearch', input: '{"query":"loki"}' }))).toBe('{"query":"loki"}');
  });

  it('says a failed call failed', () => {
    expect(whatItDid(tool({ passed: false, error: 'Exit code 1', description: 'Build the solution' }))).toBe(
      'Failed · Build the solution',
    );
  });
});

describe('describeAllowedBy', () => {
  it.each([
    ['config', 'Allowed by your settings'],
    ['user_temporary', 'You allowed it, this once'],
    ['user_permanent', 'You allowed it, from now on'],
    ['hook', 'A hook allowed it'],
  ])('says a call allowed by %s in words', (allowedBy, words) => {
    expect(describeAllowedBy(tool({ allowedBy }))).toBe(words);
  });

  it('gives any other value as claude code sent it', () => {
    expect(describeAllowedBy(tool({ allowedBy: 'mode' }))).toBe('mode');
  });

  it('says who allowed a call claude code did not name is not known', () => {
    expect(describeAllowedBy(tool({ allowedBy: null }))).toBe('Not known');
  });
});

describe('describeOutcome', () => {
  it('says a call that passed passed', () => {
    expect(describeOutcome(tool())).toBe('Passed');
  });

  it('says a call that failed failed', () => {
    expect(describeOutcome(tool({ passed: false, error: 'Exit code 1' }))).toBe('Failed');
  });
});

describe('describeWithheld', () => {
  it('gives the size of an input claude code kept back', () => {
    expect(describeWithheld(tool({ inputBytes: 4_096 }))).toBe('Withheld · 4,096 bytes');
  });

  it('says withheld alone where claude code gave no size', () => {
    expect(describeWithheld(tool())).toBe('Withheld');
  });
});

describe('outputOf', () => {
  it("gives an edit's diff", () => {
    expect(outputOf(tool({ tool: 'Edit', diff: '-a\n+b' }))).toBe('-a\n+b');
  });

  it("gives any other call's output", () => {
    expect(outputOf(tool({ output: 'Build succeeded.' }))).toBe('Build succeeded.');
  });
});

describe('describeOutputNote', () => {
  const cut = 'x'.repeat(2_048);

  it('says an output Claude Code cut short is the first 2,048 characters, and gives the whole size', () => {
    expect(describeOutputNote(tool({ output: cut, resultBytes: 48_213 }))).toBe(
      'The first 2,048 characters of 48,213 bytes',
    );
  });

  it('says a diff Claude Code cut short is the first 2,048 characters too', () => {
    expect(describeOutputNote(tool({ tool: 'Edit', diff: cut, resultBytes: 9_000 }))).toBe(
      'The first 2,048 characters of 9,000 bytes',
    );
  });

  it('says nothing of an output of 2,048 characters that is the whole result', () => {
    expect(describeOutputNote(tool({ output: cut, resultBytes: 2_048 }))).toBeNull();
  });

  it('says nothing of a short output', () => {
    expect(describeOutputNote(tool({ output: 'ok', resultBytes: 48_213 }))).toBeNull();
  });

  it('reads Withheld with its size where Claude Code kept the output back', () => {
    expect(describeOutputNote(tool({ resultBytes: 512 }))).toBe('Withheld · 512 bytes');
  });

  it('reads Withheld alone where Claude Code kept the output back and gave no size', () => {
    expect(describeOutputNote(tool())).toBe('Withheld');
  });

  it('reads not known where no Span landed for the call', () => {
    expect(describeOutputNote(tool({ traced: false, resultBytes: 512 }))).toBe('Not known');
  });

  it('reads not known for a Subagent call, as Claude Code never sends its output', () => {
    expect(describeOutputNote(tool({ tool: 'Agent', resultBytes: 512 }))).toBe('Not known');
  });
});

describe('toolTimePartsOf', () => {
  it('splits the call into hooks before, waiting for approval, running and hooks after', () => {
    const parts = toolTimePartsOf(
      tool({
        hooksBefore: { count: 2, lengthMs: 850 },
        waitedMs: 12_000,
        ranMs: 4_000,
        hooksAfter: { count: 1, lengthMs: 1_200 },
      }),
    );

    expect(parts.map((part) => [part.word, part.ms])).toEqual([
      ['Hooks before', 850],
      ['Waiting for approval', 12_000],
      ['Running', 4_000],
      ['Hooks after', 1_200],
    ]);
  });

  it('gives each hook part its length and how many hooks ran', () => {
    const parts = toolTimePartsOf(
      tool({ hooksBefore: { count: 2, lengthMs: 850 }, hooksAfter: { count: 1, lengthMs: 1_200 } }),
    );

    expect([parts[0].figure, parts[3].figure]).toEqual(['850 ms · 2 hooks', '1.2 s · 1 hook']);
  });

  it('gives a side where no hook ran no time', () => {
    const before = toolTimePartsOf(tool())[0];

    expect([before.ms, before.figure]).toEqual([0, 'No hooks']);
  });

  it('gives a call that asked no one no wait for approval', () => {
    expect(toolTimePartsOf(tool({ ranMs: 4_000 }))[1].ms).toBe(0);
  });

  it('leaves the wait and the running not known where no Span landed for the call', () => {
    const parts = toolTimePartsOf(tool({ traced: false }));

    expect(parts.map((part) => part.figure)).toEqual(['No hooks', 'Not known', 'Not known', 'No hooks']);
  });
});

describe('fileOf', () => {
  it('gives the file a read read', () => {
    expect(fileOf(tool({ tool: 'Read', input: '{"file_path":"src/Clock.cs"}' }))).toBe('src/Clock.cs');
  });

  it('gives no file where the input was kept back', () => {
    expect(fileOf(tool({ tool: 'Read', inputBytes: 30 }))).toBeNull();
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
