import { isToolCall, type Mark } from './steps';

export interface Highlight {
  kind: 'tool';
  name: string;
}

const lit = 'lit';

const tool = 'tool:';

// A Highlight lives in the address bar, so a link can light every call of one tool for a teammate.
export function readHighlight(params: URLSearchParams): Highlight | null {
  const written = params.get(lit);

  if (written === null || !written.startsWith(tool) || written.length === tool.length) {
    return null;
  }

  return { kind: 'tool', name: written.slice(tool.length) };
}

export function withHighlight(params: URLSearchParams, highlight: Highlight | null): URLSearchParams {
  const written = new URLSearchParams(params);

  if (highlight === null) {
    written.delete(lit);
  } else {
    written.set(lit, `${tool}${highlight.name}`);
  }

  return written;
}

export function toggled(shown: Highlight | null, picked: Highlight): Highlight | null {
  return shown !== null && shown.kind === picked.kind && shown.name === picked.name ? null : picked;
}

export function litBy(highlight: Highlight, marks: readonly Mark[]): Set<string> {
  return new Set(
    marks.filter(({ step }) => isToolCall(step) && step.tool === highlight.name).map(({ step }) => step.id),
  );
}
