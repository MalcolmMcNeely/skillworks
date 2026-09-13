import { describe, expect, it } from 'vitest';
import {
  describeFault,
  describeFaultList,
  describeFaults,
  describeIngest,
  describeRefresh,
} from './ingest';

const transcript = 'C:\\Users\\dev\\.claude\\projects\\C--Projects-alpha\\session.jsonl';

const idle = {
  running: false,
  completedPasses: 1,
  transcriptsSeen: 1471,
  transcriptsTotal: 1471,
  lastPassWasFull: false,
};

describe('describeIngest', () => {
  it('counts the transcripts it has reached while it is reading', () => {
    expect(
      describeIngest({ ...idle, running: true, completedPasses: 0, transcriptsSeen: 312 }),
    ).toBe('Reading transcript 312 of 1471.');
  });

  it('says it is still looking before it knows how many there are', () => {
    expect(
      describeIngest({
        ...idle,
        running: true,
        completedPasses: 0,
        transcriptsSeen: 0,
        transcriptsTotal: 0,
      }),
    ).toBe('Looking for transcripts…');
  });

  it('tells an empty screen apart from an unfinished one', () => {
    expect(
      describeIngest({
        ...idle,
        completedPasses: 0,
        transcriptsSeen: 0,
        transcriptsTotal: 0,
      }),
    ).toBe('The first read has not started yet.');
  });

  it('says there is nothing to read rather than reporting zero of zero', () => {
    expect(describeIngest({ ...idle, transcriptsSeen: 0, transcriptsTotal: 0 })).toBe(
      'There are no transcripts to read.',
    );
  });

  it('says how much it read once the pass is done', () => {
    expect(describeIngest(idle)).toBe('Read all 1471 transcripts.');
  });

  it('says so when the pass that finished was the full re-read that was asked for', () => {
    expect(describeIngest({ ...idle, lastPassWasFull: true })).toBe(
      'Read all 1471 transcripts again, from scratch.',
    );
  });
});

describe('describeRefresh', () => {
  it('says so plainly when nothing has been read yet', () => {
    expect(describeRefresh(null)).toBe('Not refreshed yet.');
  });

  it('names the time the numbers last moved', () => {
    expect(describeRefresh('2026-09-13T09:15:00.000Z')).toContain('Last refreshed');
  });
});

describe('describeFaults', () => {
  it('says nothing was skipped rather than showing a zero', () => {
    expect(describeFaults(0)).toBe('Nothing was skipped.');
  });

  it('counts one skipped piece without an s', () => {
    expect(describeFaults(1)).toBe('1 piece of transcript was skipped.');
  });

  it('counts several', () => {
    expect(describeFaults(4)).toBe('4 pieces of transcript were skipped.');
  });
});

describe('describeFaultList', () => {
  it('says so when the API handed back fewer than it counted', () => {
    expect(describeFaultList(200, 1471)).toBe('Showing the first 200 of 1471.');
  });

  it('says the list is complete when it is', () => {
    expect(describeFaultList(3, 3)).toBe('Showing all 3.');
  });
});

describe('describeFault', () => {
  it('names the line a developer would open the file at', () => {
    expect(describeFault({ path: transcript, line: 312, reason: 'the line ends early' })).toBe(
      `${transcript} line 312: the line ends early`,
    );
  });

  it('names the file alone when the whole of it would not open', () => {
    expect(describeFault({ path: transcript, line: 0, reason: 'it is in use' })).toBe(
      `${transcript}: it is in use`,
    );
  });
});
