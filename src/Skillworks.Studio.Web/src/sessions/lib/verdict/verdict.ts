import { describeCount, describeMoney } from '../../../shared/figures/lib/figures';
import { costBreakdownOf, type CostBreakdown } from './costBreakdown';
import { namedIn, type FindingsPage } from './findings';
import type { TimeBreakdownPage } from './timeBreakdown';
import { levelsOf, peakContextOf } from '../timeline/context';
import { describeRunLength, notKnown } from '../sessions';
import type { SessionAnswer } from '../steps';

export interface Verdict {
  headlines: Headline[];
  findings: FindingsPage | null;
  timeBreakdown: TimeBreakdownPage | null;
  costs: CostBreakdown | null;
}

// Takes no View, so no drag in the Timeline can reach a figure above it.
export function verdictOf(answer: SessionAnswer): Verdict {
  return {
    headlines: headlinesOf(answer),
    findings: answer.findings,
    timeBreakdown: answer.timeBreakdown,
    costs: costBreakdownOf(answer.exchanges, answer.beforeFirstPrompt, answer.subagents),
  };
}

export interface Headline {
  name: string;
  figure: string;
  note: string | null;
  // Colour is never the only sign, so a headline that raises the alarm also carries a figure a reader can check.
  alarm: boolean;
}

export function headlinesOf(answer: SessionAnswer): Headline[] {
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
    findingsHeadline(answer.findings),
  ];
}

function findingsHeadline(findings: FindingsPage | null): Headline {
  if (findings === null) {
    return { name: 'Findings', figure: notKnown, note: null, alarm: false };
  }

  // A Finding nobody could measure crossed nothing, so counting it would read as trouble the run never had.
  const crossed = namedIn(findings).filter((each) => each.known).length;

  return { name: 'Findings', figure: describeCount(crossed), note: null, alarm: crossed > 0 };
}
