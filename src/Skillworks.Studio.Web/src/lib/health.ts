/**
 * How Studio's own health reads as sentences. Structural, so this module stays pure — it never
 * imports the wire types that happen to match it, and it takes the parts rather than the answer
 * they arrived in.
 */

/** How one part of Studio is doing. The API spells these; the words for them are made here. */
export type PartState = 'working' | 'starting' | 'off' | 'broken';

/** One part of Studio: how it is doing, and what a developer would do about it. */
export interface Part {
  name: string;
  state: PartState;
  detail: string;
  /** Null when there is nothing to do. */
  action: string | null;
}

/** The mark beside a part's name, so a panel of five reads at a glance rather than word by word. */
const marks: Record<PartState, string> = {
  working: '✓',
  starting: '…',
  off: '○',
  broken: '✕',
};

/** One part as a line: the mark, what is true now, and what to do about it when there is something. */
export function describePart(part: Part): string {
  const said = `${marks[part.state]} ${part.name}: ${part.detail}`;

  return part.action === null ? said : `${said} ${part.action}`;
}

/**
 * The parts that are not doing their job. A part that is deliberately off is in here: nothing is
 * broken, and a screen is still missing something because of it.
 */
export function troubled(parts: readonly Part[]): Part[] {
  return parts.filter((part) => part.state !== 'working');
}

/**
 * Studio in one line, for a reader who is not looking at the panel. It counts rather than names,
 * because the panel below it does the naming.
 */
export function describeHealth(parts: readonly Part[]): string {
  const trouble = troubled(parts);

  if (trouble.length === 0) {
    return 'Every part of Studio is working.';
  }

  return trouble.length === 1
    ? `1 part of Studio needs attention: ${trouble[0]!.name}.`
    : `${trouble.length} parts of Studio need attention: ${trouble.map((part) => part.name).join(', ')}.`;
}
