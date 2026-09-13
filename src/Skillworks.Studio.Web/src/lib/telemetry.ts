/**
 * How the telemetry switch reads as sentences. Structural, so this module stays pure — it never
 * imports the wire types that happen to match it.
 */

/** Whether Claude Code is emitting to Studio. Settings Studio cannot read are their own answer. */
export function describeTelemetry(state: {
  emitting: boolean;
  readable: boolean;
  settingsPath: string;
  problem: string | null;
}): string {
  if (!state.readable) {
    return `Studio cannot read ${state.settingsPath}, so it will not write it: ${
      state.problem ?? 'it could not be parsed'
    }`;
  }

  return state.emitting
    ? 'Claude Code is emitting telemetry to Studio.'
    : 'Claude Code is not emitting telemetry to Studio.';
}

/** One line of the preview Studio shows before it writes anything. */
export function describeChange(change: { name: string; from: string | null; to: string }): string {
  return `${change.name}: ${change.from ?? 'not set'} → ${change.to}`;
}
