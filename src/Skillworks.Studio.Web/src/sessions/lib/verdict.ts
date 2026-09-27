import { describeCount, describeMoney } from '../../shared/figures/lib/figures';
import { namedIn, type FindingsPage } from './findings';
import { levelsOf, peakContextOf } from './panels/context';
import { describeRunLength, notKnown } from './sessions';
import type { SessionAnswer } from './steps';

export interface Tile {
  name: string;
  figure: string;
  note: string | null;
  // Colour is never the only sign, so a tile that raises the alarm also carries a figure a reader can check.
  alarm: boolean;
}

// The whole run and never the View, so the verdict holds still while a reader digs in beneath it.
export function tilesOf(answer: SessionAnswer): Tile[] {
  const run = answer.session;

  if (run === null) {
    return [];
  }

  const faults = answer.steps.filter((step) => step.fault).length;
  const peak = peakContextOf(levelsOf(answer.context), answer.limitTokens);

  return [
    { name: 'Length', figure: describeRunLength(run.lengthMs), note: null, alarm: false },
    { name: 'Cost', figure: describeMoney(run.cost), note: null, alarm: false },
    { name: 'Tool calls', figure: describeCount(run.toolCalls), note: null, alarm: false },
    { name: 'Faults', figure: describeCount(faults), note: null, alarm: faults > 0 },
    { name: 'Peak context', figure: peak.figure, note: peak.note, alarm: peak.high },
    findingsTile(answer.findings),
  ];
}

function findingsTile(findings: FindingsPage | null): Tile {
  if (findings === null) {
    return { name: 'Findings', figure: notKnown, note: null, alarm: false };
  }

  // A Finding nobody could measure crossed nothing, so counting it would read as trouble the run never had.
  const crossed = namedIn(findings).filter((each) => each.known).length;

  return { name: 'Findings', figure: describeCount(crossed), note: null, alarm: crossed > 0 };
}
