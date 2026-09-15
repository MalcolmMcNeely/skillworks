import { noLink } from '../../http/lib/errors';

export type SwitchPosition = 'on' | 'off' | 'unreadable' | 'asking' | 'unlinked';

export interface SwitchReading {
  position: SwitchPosition;
  mark: string;
  word: string;
  why: string | null;
}

export function switchOf(
  state: { emitting: boolean; readable: boolean; settingsPath: string; problem: string | null } | null,
  failure: string | null,
): SwitchReading {
  // Ahead of the state, which may no longer match the disk once the API stops answering.
  if (failure !== null) {
    return { position: 'unlinked', mark: '✕', word: noLink, why: failure };
  }

  if (state === null) {
    return { position: 'asking', mark: '…', word: 'Asking', why: null };
  }

  if (!state.readable) {
    return {
      position: 'unreadable',
      mark: '⚠',
      word: 'Unreadable',
      why: `Studio cannot read ${state.settingsPath}, so it will not write it: ${state.problem ?? 'it could not be parsed'}.`,
    };
  }

  return state.emitting
    ? { position: 'on', mark: 'On', word: 'On', why: null }
    : { position: 'off', mark: 'Off', word: 'Off', why: null };
}

export function describeChange(change: { name: string; from: string | null; to: string }): string {
  return `${change.name}: ${change.from ?? 'not set'} → ${change.to}`;
}
