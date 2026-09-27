import { isAttributed, isToolCall, type Mark, type Step } from './steps';

export type Highlight =
  | { kind: 'tool'; name: string }
  | { kind: 'skill'; name: string }
  | { kind: 'noSkill' }
  | { kind: 'unnamed' };

const lit = 'lit';

const named = { tool: 'tool:', skill: 'skill:' } as const;

// Keys with no prefix, so a skill that happens to be called "unnamed" is never read as Unnamed spend.
const noSkill = 'no-skill';

const unnamed = 'unnamed';

export function skillLabelOf(highlight: Exclude<Highlight, { kind: 'tool' }>): string {
  if (highlight.kind === 'skill') {
    return highlight.name;
  }

  return highlight.kind === 'noSkill' ? 'No skill' : 'Unnamed spend';
}

export function describeLit(highlight: Highlight): string {
  return highlight.kind === 'tool' ? `every ${highlight.name} call` : `every Step of ${skillLabelOf(highlight)}`;
}

export function highlightKey(highlight: Highlight): string {
  if (highlight.kind === 'noSkill') {
    return noSkill;
  }

  if (highlight.kind === 'unnamed') {
    return unnamed;
  }

  return `${named[highlight.kind]}${highlight.name}`;
}

// A Highlight lives in the address bar, so a link can light every call of one tool for a teammate.
export function readHighlight(params: URLSearchParams): Highlight | null {
  return highlightOf(params.get(lit));
}

// From its key, so a page can hold a Highlight still across renders, where one read off the address is new each time.
export function highlightOf(key: string | null): Highlight | null {
  if (key === noSkill) {
    return { kind: 'noSkill' };
  }

  if (key === unnamed) {
    return { kind: 'unnamed' };
  }

  for (const kind of ['tool', 'skill'] as const) {
    if (key !== null && key.startsWith(named[kind]) && key.length > named[kind].length) {
      return { kind, name: key.slice(named[kind].length) };
    }
  }

  return null;
}

export function withHighlight(params: URLSearchParams, highlight: Highlight | null): URLSearchParams {
  const shown = new URLSearchParams(params);

  if (highlight === null) {
    shown.delete(lit);
  } else {
    shown.set(lit, highlightKey(highlight));
  }

  return shown;
}

export function sameHighlight(one: Highlight | null, other: Highlight): boolean {
  return one !== null && highlightKey(one) === highlightKey(other);
}

export function toggled(shown: Highlight | null, picked: Highlight): Highlight | null {
  return sameHighlight(shown, picked) ? null : picked;
}

function lights(highlight: Highlight, step: Step): boolean {
  if (highlight.kind === 'tool') {
    return isToolCall(step) && step.tool === highlight.name;
  }

  // By each Step's Attribution, not an Activation's spell, so a skill that called another claims none of its Steps.
  if (!isAttributed(step)) {
    return false;
  }

  if (highlight.kind === 'skill') {
    return step.skill === highlight.name;
  }

  return highlight.kind === 'unnamed' ? step.unnamed : step.skill === null && !step.unnamed;
}

export function litBy(highlight: Highlight, marks: readonly Mark[]): Set<string> {
  return new Set(marks.filter(({ step }) => lights(highlight, step)).map(({ step }) => step.id));
}
