import { inSpell, type Spell } from './view';
import { isToolCall, type Mark } from '../steps';

export interface ToolRow {
  tool: string;
  calls: number;
  faults: number;
  // Somebody chose each of these, so they ride beside the Faults and are never added to them.
  friction: number;
  lengthMs: number;
}

export function toolRowsOf(marks: readonly Mark[], view: Spell | null): ToolRow[] {
  const rows = new Map<string, ToolRow>();

  for (const { step } of inSpell(marks, view)) {
    if (!isToolCall(step)) {
      continue;
    }

    const row = rows.get(step.tool) ?? { tool: step.tool, calls: 0, faults: 0, friction: 0, lengthMs: 0 };

    rows.set(step.tool, {
      ...row,
      calls: row.calls + 1,
      faults: row.faults + (step.fault ? 1 : 0),
      friction: row.friction + (step.kind === 'refused' ? 1 : 0),
      lengthMs: row.lengthMs + step.lengthMs,
    });
  }

  // By name within a tie, so two reads of one run list the rows the same way.
  return [...rows.values()].toSorted((one, other) => other.calls - one.calls || one.tool.localeCompare(other.tool, 'en'));
}
