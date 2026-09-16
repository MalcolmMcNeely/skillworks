import { describe, expect, it } from 'vitest';
import { recordingWarning, switchOf, whoElseCanRead } from './telemetry';

const settingsPath = 'C:\\Users\\dev\\.claude\\settings.json';

describe('switchOf', () => {
  it('says On when Claude Code is emitting', () => {
    expect(switchOf({ emitting: true, readable: true, settingsPath, problem: null }, null)).toEqual({
      position: 'on',
      mark: 'On',
      word: 'On',
      why: null,
    });
  });

  it('says Off when Claude Code is not emitting', () => {
    expect(switchOf({ emitting: false, readable: true, settingsPath, problem: null }, null)).toEqual({
      position: 'off',
      mark: 'Off',
      word: 'Off',
      why: null,
    });
  });

  it('says it cannot read the settings, and opens the file and the problem, so the developer knows why it will not flip', () => {
    expect(
      switchOf({ emitting: false, readable: false, settingsPath, problem: 'its top level is not an object' }, null),
    ).toEqual({
      position: 'unreadable',
      mark: '⚠',
      word: 'Unreadable',
      why: 'Studio cannot read C:\\Users\\dev\\.claude\\settings.json, so it will not write it: its top level is not an object.',
    });
  });

  it('still opens a reason when the API names no problem with a file it cannot read', () => {
    const reading = switchOf({ emitting: false, readable: false, settingsPath, problem: null }, null);

    expect(reading.why).toBe(
      'Studio cannot read C:\\Users\\dev\\.claude\\settings.json, so it will not write it: it could not be parsed.',
    );
  });

  it('claims neither On nor Off while the API has not answered', () => {
    expect(switchOf(null, null)).toEqual({ position: 'asking', mark: '…', word: 'Asking', why: null });
  });

  it('says No link, and opens the failure, when the API could not be read', () => {
    expect(switchOf(null, 'Failed to fetch')).toEqual({
      position: 'unlinked',
      mark: '✕',
      word: 'No link',
      why: 'Failed to fetch',
    });
  });

  it('drops a state read earlier when a later call fails, as the file may have changed since', () => {
    const reading = switchOf({ emitting: true, readable: true, settingsPath, problem: null }, 'Failed to fetch');

    expect(reading.position).toBe('unlinked');
  });

  it('gives every position a mark of its own, so colour is never the only signal', () => {
    const marks = [
      switchOf({ emitting: true, readable: true, settingsPath, problem: null }, null),
      switchOf({ emitting: false, readable: true, settingsPath, problem: null }, null),
      switchOf({ emitting: false, readable: false, settingsPath, problem: null }, null),
      switchOf(null, null),
      switchOf(null, 'Failed to fetch'),
    ].map((reading) => reading.mark);

    expect(new Set(marks).size).toBe(5);
  });
});

describe('recordingWarning', () => {
  const said = [...recordingWarning, whoElseCanRead].join(' ');

  it('names no setting, because a variable name tells a reader nothing about what is kept', () => {
    expect(said).not.toMatch(/OTEL_|CLAUDE_CODE_/);
  });

  it('says what will be kept of what the developer types and of what the agent answers', () => {
    expect(said).toMatch(/you type/);
    expect(said).toMatch(/writes back/);
  });

  it('says tool content is kept, as that is where a file the developer never meant to share goes', () => {
    expect(said).toMatch(/tool/);
    expect(said).toMatch(/files/);
  });

  it('says who else will be able to read it, which is the part a developer cannot undo', () => {
    expect(whoElseCanRead).toMatch(/organisation/);
  });
});
