import type { SymbolTable } from '../../alphabets/lib/alphabets';
import { noLink } from '../../http/lib/errors';

export type SwitchPosition = 'on' | 'off' | 'unreadable' | 'asking' | 'unlinked';

export interface SwitchReading {
  position: SwitchPosition;
  mark: string;
  word: string;
  why: string | null;
}

// A mark apiece, so colour is never the only signal of where the switch sits.
const switchMarks: Record<SwitchPosition, string> = {
  on: 'On',
  off: 'Off',
  unreadable: '⚠',
  asking: '…',
  unlinked: '✕',
};

export const switchSymbols: SymbolTable = { alphabet: 'condition', glyphs: Object.values(switchMarks) };

export function switchOf(
  state: { emitting: boolean; readable: boolean; settingsPath: string; problem: string | null } | null,
  failure: string | null,
): SwitchReading {
  // Ahead of the state, which may no longer match the disk once the API stops answering.
  if (failure !== null) {
    return { position: 'unlinked', mark: switchMarks.unlinked, word: noLink, why: failure };
  }

  if (state === null) {
    return { position: 'asking', mark: switchMarks.asking, word: 'Asking', why: null };
  }

  if (!state.readable) {
    return {
      position: 'unreadable',
      mark: switchMarks.unreadable,
      word: 'Unreadable',
      why: `Studio cannot read ${state.settingsPath}, so it will not write it: ${state.problem ?? 'it could not be parsed'}.`,
    };
  }

  return state.emitting
    ? { position: 'on', mark: switchMarks.on, word: 'On', why: null }
    : { position: 'off', mark: switchMarks.off, word: 'Off', why: null };
}

// No setting is named here, because a variable name warns nobody of what a colleague could read.
export const recordingWarning: string[] = [
  'Everything you type to Claude Code on this machine.',
  'Everything Claude Code writes back, including its plans and its reasons.',
  'What every tool was handed and what it returned, so the text of the files you work on goes too.',
  'How long each step took, and which agent ran it.',
];

export const whoElseCanRead =
  'All of it goes to the stores the whole organisation reads. Anyone who can open them can read your work.';
