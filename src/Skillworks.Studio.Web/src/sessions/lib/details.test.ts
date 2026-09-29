import { describe, expect, it } from 'vitest';
import { describePurpose, rowLineOf, type SideRequest, type TurnDetails } from './details';
import type { Step } from './steps';

function turn(details: Partial<TurnDetails> = {}): TurnDetails {
  return { purpose: 'work', side: null, sentAs: null, outputTokens: 0, cost: 0, ...details };
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
