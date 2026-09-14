export type PartState = 'working' | 'starting' | 'off' | 'broken';

export interface Part {
  name: string;
  state: PartState;
  detail: string;
  action: string | null;
}

const marks: Record<PartState, string> = {
  working: '✓',
  starting: '…',
  off: '○',
  broken: '✕',
};

export function describePart(part: Part): string {
  const said = `${marks[part.state]} ${part.name}: ${part.detail}`;

  return part.action === null ? said : `${said} ${part.action}`;
}

// A part deliberately off counts: nothing is broken, but a screen is still missing something.
export function troubled(parts: readonly Part[]): Part[] {
  return parts.filter((part) => part.state !== 'working');
}

export function describeHealth(parts: readonly Part[]): string {
  const trouble = troubled(parts);

  if (trouble.length === 0) {
    return 'Every part of Studio is working.';
  }

  return trouble.length === 1
    ? `1 part of Studio needs attention: ${trouble[0]!.name}.`
    : `${trouble.length} parts of Studio need attention: ${trouble.map((part) => part.name).join(', ')}.`;
}
