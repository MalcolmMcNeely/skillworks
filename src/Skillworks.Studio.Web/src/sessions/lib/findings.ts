import { describeCount, describeLength, describeShare } from '../../figures/lib/figures';
import { notKnown } from './sessions';

export type FindingKind =
  | 'failingAgain'
  | 'editedAgain'
  | 'rateLimited'
  | 'cacheRebuilt'
  | 'nearTheLimit'
  | 'hooks'
  | 'waiting'
  | 'costlySubagent';

export interface Finding {
  kind: FindingKind;
  // Null where the bar is about the whole run rather than one command, file or subagent.
  subject: string | null;
  // Null where only a span could have measured it and the run has none, so no figure here is a made-up zero.
  figure: number | null;
  bar: number;
  // Null where the finding is about a length of time rather than one step, which is what the moment is for.
  step: string | null;
  atUtc: string;
  lengthMs: number;
}

export interface FindingsPage {
  kind: 'findings';
  findings: Finding[];
}

// How one bar is put into words. The bar's own figure comes from the API, on the Finding.
interface Wording {
  kind: FindingKind;
  word: string;
  reads: 'count' | 'share' | 'length' | 'times';
  note: string;
}

const wordings: readonly Wording[] = [
  {
    kind: 'failingAgain',
    word: 'The same call kept failing',
    reads: 'count',
    note: 'One call failed over and over, which is an agent stuck rather than one thing going wrong.',
  },
  {
    kind: 'editedAgain',
    word: 'One file was edited over and over',
    reads: 'count',
    note: 'An agent that cannot land a change goes back to the same file again and again.',
  },
  {
    kind: 'rateLimited',
    word: 'The run hit a rate limit',
    reads: 'count',
    note: 'The model turned a request away because too many had been sent.',
  },
  {
    kind: 'cacheRebuilt',
    word: 'The prompt cache was rebuilt',
    reads: 'count',
    note: 'The context was written again at full price instead of being read back cheaply.',
  },
  {
    kind: 'nearTheLimit',
    word: 'The context came near its limit',
    reads: 'share',
    note: 'Claude Code cuts a run down as its window fills, so this is the last part before that happens.',
  },
  {
    kind: 'hooks',
    word: 'Hooks took a large share of the working time',
    reads: 'share',
    note: 'Measured against the time the run was working, not against the time it sat waiting.',
  },
  {
    kind: 'waiting',
    word: 'The run waited a long time for permission',
    reads: 'length',
    note: 'Time a tool was ready to run and waited for a person to allow it.',
  },
  {
    kind: 'costlySubagent',
    word: 'One subagent cost far more than its siblings',
    reads: 'times',
    note: 'Measured against the middle of what the others cost, so the runaway cannot raise its own bar.',
  },
];

export interface Named extends Wording {
  finding: Finding;
  startMs: number;
  endMs: number;
  reading: string;
  // The bar in the same words as the figure, so a reader sees how close the call was.
  barReading: string;
  known: boolean;
}

// In the order the bars are declared, so a reader who knows the list finds the same Finding in the same place twice.
export function namedIn(page: FindingsPage | null): Named[] {
  const found = new Map((page?.findings ?? []).map((finding) => [finding.kind, finding]));

  return wordings.flatMap((wording) => {
    const finding = found.get(wording.kind);

    return finding === undefined ? [] : [named(wording, finding)];
  });
}

function named(wording: Wording, finding: Finding): Named {
  const startMs = Date.parse(finding.atUtc);

  return {
    ...wording,
    finding,
    startMs,
    endMs: startMs + finding.lengthMs,
    reading: finding.figure === null ? notKnown : readingOf(wording, finding.figure),
    barReading: readingOf(wording, finding.bar),
    known: finding.figure !== null,
  };
}

function readingOf(wording: Wording, figure: number): string {
  if (wording.reads === 'count') {
    return figure === 1 ? 'once' : `${describeCount(figure)} times`;
  }

  if (wording.reads === 'share') {
    return describeShare(figure);
  }

  return wording.reads === 'length' ? describeLength(figure) : `${figure.toFixed(1)}× the others`;
}

// A run whose spans have not landed has read no bar yet, which is not the same as a run that crossed none.
export function noFindingsWord(page: FindingsPage | null): string {
  return page === null ? 'Still reading the run.' : 'Nothing in this run crossed a bar.';
}
