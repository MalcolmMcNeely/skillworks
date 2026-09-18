import type { Range } from '../view';

export type SplitPart = 'waiting' | 'tools' | 'hooks' | 'model' | 'subagents' | 'side' | 'quiet' | 'yourTurn';

export interface PartSpell {
  part: SplitPart;
  atUtc: string;
  lengthMs: number;
}

export interface SplitPage {
  kind: 'split';
  // Three of the parts can only be measured from a Span, so this says whether they were measured at all.
  traced: boolean;
  // Never overlapping, so a View is split by clipping each Spell to it and nothing else.
  parts: PartSpell[];
  // The whole of each part, overlaps and all, which is what the exclusive figure beside it leaves out.
  kinds: PartSpell[];
}

interface Part {
  part: SplitPart;
  word: string;
  note: string;
}

const parts: readonly Part[] = [
  {
    part: 'waiting',
    word: 'Waiting for your OK',
    note: 'A tool was ready to run and waited for a person to allow it.',
  },
  { part: 'hooks', word: 'Hooks', note: 'Hook scripts the main agent ran, before or after a tool call.' },
  {
    part: 'tools',
    word: 'Tools running',
    note: 'Main agent tool calls, from the moment they were allowed to the moment they came back.',
  },
  { part: 'model', word: 'Model thinking', note: 'Main agent turns, from the request to the last word.' },
  {
    part: 'subagents',
    word: 'Only subagents',
    note: 'The main agent had nothing running and waited on a subagent.',
  },
  { part: 'side', word: 'Side requests', note: 'A turn nobody asked for, such as naming the run or compacting it.' },
  { part: 'quiet', word: 'Nothing running', note: 'Inside an exchange, with nothing on any lane.' },
  { part: 'yourTurn', word: 'Your turn', note: 'Between one exchange ending and the next starting.' },
];

// A run with no Span cannot tell a person's delay, a hook run or a subagent's work from the rest of the time.
const fromSpans = new Set<SplitPart>(['waiting', 'hooks', 'subagents']);

export interface Share extends Part {
  ms: number;
  // The whole of the part, which is the exclusive figure plus every moment another part took from it.
  overlapMs: number;
  // False where only a Span could say, and the Spans are not there, so nothing here may read as none.
  known: boolean;
}

// Always all eight, as a part that took none of a run is an answer and a row that comes and goes is not.
export function sharesOf(page: SplitPage | null, view: Range | null): Share[] {
  const exclusive = summed(page?.parts ?? [], view);
  const whole = summed(page?.kinds ?? [], view);

  return parts.map((part) => ({
    ...part,
    ms: exclusive.get(part.part) ?? 0,
    overlapMs: whole.get(part.part) ?? 0,
    known: page !== null && (page.traced || !fromSpans.has(part.part)),
  }));
}

// Clipped rather than filtered, as a Spell can run in and out of the View and only its middle counts.
function summed(spells: readonly PartSpell[], view: Range | null): Map<SplitPart, number> {
  const totals = new Map<SplitPart, number>();

  for (const spell of spells) {
    const startMs = Date.parse(spell.atUtc);
    const endMs = startMs + spell.lengthMs;
    const from = view === null ? startMs : Math.max(startMs, view[0]);
    const to = view === null ? endMs : Math.min(endMs, view[1]);

    if (to > from) {
      totals.set(spell.part, (totals.get(spell.part) ?? 0) + (to - from));
    }
  }

  return totals;
}

export function splitLength(shares: readonly Share[]): number {
  return shares.reduce((total, share) => total + share.ms, 0);
}

export function shareOf(share: Share, lengthMs: number): number {
  return lengthMs > 0 ? share.ms / lengthMs : 0;
}

// The split comes with the spans, so a run whose second part is still on its way has read nothing yet.
export function noSplitWord(split: SplitPage | null): string {
  return split === null ? 'Still reading the run.' : 'Nothing ran in view.';
}
