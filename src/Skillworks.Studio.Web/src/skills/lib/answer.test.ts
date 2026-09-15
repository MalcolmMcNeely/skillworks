import { describe, expect, it } from 'vitest';
import type { Gap } from '../../gaps/lib/gaps';
import { chunkedBody } from '../../http/lib/chunkedBody';
import { readLines } from '../../http/lib/lines';
import type { Origin } from '../../provenance/lib/provenance';
import { foldSkillsLine, showsFigures, type SkillsAnswer } from './answer';
import type { SkillOnDay, SkillsLine, TurnTotals } from './skills';

async function statesOf(chunks: readonly string[]): Promise<SkillsAnswer[]> {
  const states: SkillsAnswer[] = [];
  let answer: SkillsAnswer | null = null;

  for await (const line of readLines<SkillsLine>(chunkedBody(chunks), new AbortController().signal)) {
    answer = foldSkillsLine(answer, line);
    states.push(answer);
  }

  return states;
}

function wire(...lines: SkillsLine[]): string[] {
  return lines.map((line) => `${JSON.stringify(line)}\n`);
}

const span = {
  from: '2026-09-14',
  to: '2026-09-15',
  lookback: false,
  fromUtc: '2026-09-14T00:00:00+00:00',
  untilUtc: '2026-09-16T00:00:00+00:00',
};

function head(catalogueSkills: string[] = [], days = ['2026-09-15', '2026-09-14']): SkillsLine {
  return { kind: 'head', span, days, catalogueSkills };
}

function daysBack(count: number): string[] {
  return Array.from({ length: count }, (_, back) => `2026-09-${String(15 - back).padStart(2, '0')}`);
}

function hours(counts: Record<number, number>): number[] {
  return Array.from({ length: 24 }, (_, hour) => counts[hour] ?? 0);
}

function day(date: string, skills: SkillOnDay[], unnamedSpend: TurnTotals | null = null): SkillsLine {
  return { kind: 'day', day: date, skills, unnamedSpend, unnarrowedEvents: 10 };
}

function end(gap: Gap): SkillsLine {
  return { kind: 'end', gap };
}

function spent(cost: number, tokens = 0): TurnTotals {
  return { cost, inputTokens: tokens, outputTokens: tokens, cacheReadTokens: tokens, cacheCreationTokens: tokens };
}

function fired(name: string, activations: number, spend: TurnTotals | null, more: Partial<SkillOnDay> = {}): SkillOnDay {
  const named = spend === null ? null : [];

  return {
    name,
    activations,
    hours: hours({}),
    triggers: [],
    repositories: [],
    models: named,
    efforts: named,
    spend,
    origins: [],
    ...more,
  };
}

const complete: Gap = { kind: 'complete', missing: null };

const stopped: Gap = { kind: 'unreachable', missing: 'Studio could not read the events store. Nothing is shown for 2026-09-14.' };

const proactive: Origin = { trigger: 'claude-proactive', source: 'projectSettings', plugin: null, marketplace: null };

const typed: Origin = { ...proactive, trigger: 'user-slash' };

describe('foldSkillsLine', () => {
  it('takes the span from the head', async () => {
    const [atHead] = await statesOf(wire(head()));

    expect(atHead?.span).toEqual(span);
  });

  it('grows the totals as each day lands', async () => {
    const states = await statesOf(
      wire(
        head(),
        day('2026-09-15', [fired('grilling', 2, spent(1, 100))]),
        day('2026-09-14', [fired('grilling', 2, spent(0.5, 50)), fired('tdd', 4, spent(0.5, 10))]),
        end(complete),
      ),
    );

    expect(states.map((state) => state.totals)).toEqual([
      { cost: 0, activations: 0, skills: 0, tokens: 0, each: null, unnamedSpend: null },
      { cost: 1, activations: 2, skills: 1, tokens: 400, each: 0.5, unnamedSpend: null },
      { cost: 2, activations: 8, skills: 2, tokens: 640, each: 0.25, unnamedSpend: null },
      { cost: 2, activations: 8, skills: 2, tokens: 640, each: 0.25, unnamedSpend: null },
    ]);
  });

  it('is arriving with no Gap until the end lands, then complete with the Gap it carries', async () => {
    const quiet: Gap = { kind: 'quiet', missing: 'Telemetry is on and the events store holds nothing for this period.' };

    const states = await statesOf(wire(head(), day('2026-09-15', []), day('2026-09-14', []), end(quiet)));

    expect(states.map((state) => [state.arriving, state.gap])).toEqual([
      [true, null],
      [true, null],
      [true, null],
      [false, quiet],
    ]);
  });

  it('counts a day as landed only once its line lands', async () => {
    const states = await statesOf(wire(head(['probekit:probe-local']), day('2026-09-15', []), day('2026-09-14', []), end(complete)));

    expect(states.map((state) => state.landedDays)).toEqual([
      [],
      ['2026-09-15'],
      ['2026-09-15', '2026-09-14'],
      ['2026-09-15', '2026-09-14'],
    ]);
  });

  it('orders the Origins of a skill as one day would, by marketplace, plugin and trigger', async () => {
    const delivered: Origin = { trigger: 'claude-proactive', source: 'plugin', plugin: 'probekit', marketplace: 'skillworks' };

    const states = await statesOf(
      wire(
        head(),
        day('2026-09-15', [fired('grilling', 2, spent(0), { origins: [delivered, typed] })]),
        day('2026-09-14', [fired('grilling', 1, spent(0), { origins: [proactive] })]),
      ),
    );

    expect(states.at(-1)?.skills[0]?.origins).toEqual([proactive, typed, delivered]);
  });

  it('adds up a skill across the days it fired', async () => {
    const states = await statesOf(
      wire(
        head(),
        day('2026-09-15', [
          fired('grilling', 3, spent(0.3), {
            hours: hours({ 14: 3 }),
            repositories: ['acme/xi'],
            models: ['claude-sonnet-5'],
            efforts: ['high'],
            origins: [proactive],
          }),
        ]),
        day('2026-09-14', [
          fired('grilling', 1, spent(0.5), {
            hours: hours({ 8: 1 }),
            repositories: ['acme/nu', 'acme/xi'],
            models: ['claude-opus-5[1m]'],
            efforts: ['high'],
            origins: [proactive, typed],
          }),
        ]),
      ),
    );

    expect(states.at(-1)?.skills).toEqual([
      {
        name: 'grilling',
        activations: 4,
        triggers: [],
        repositories: ['acme/nu', 'acme/xi'],
        models: ['claude-opus-5[1m]', 'claude-sonnet-5'],
        efforts: ['high'],
        spend: spent(0.8),
        each: 0.2,
        origins: [proactive, typed],
        lastFired: '2026-09-15T14:00:00Z',
        spark: [0, 1, 0, 0, 0, 0, 3, 0],
      },
    ]);
  });

  it('reads a skill as not named only while no landed day has named its spend', async () => {
    const states = await statesOf(
      wire(
        head(),
        day('2026-09-15', [fired('probe', 2, null)]),
        day('2026-09-14', [fired('probe', 2, spent(1), { models: ['claude-sonnet-5'], efforts: ['low'] })]),
        day('2026-09-13', [fired('probe', 1, null)]),
      ),
    );

    expect(states.slice(1).map(({ skills: [probe] }) => [probe?.spend?.cost ?? null, probe?.each, probe?.models])).toEqual([
      [null, null, null],
      [1, 0.25, ['claude-sonnet-5']],
      [1, 0.2, ['claude-sonnet-5']],
    ]);
  });

  it('gives a skill that spent but never fired no Each, rather than an Each of nothing', async () => {
    const [, afterDay] = await statesOf(wire(head(), day('2026-09-15', [fired('grilling', 0, spent(0.4))])));

    expect(afterDay?.skills.map((skill) => skill.each)).toEqual([null]);
  });

  it('adds up Unnamed spend across the days that carry it', async () => {
    const states = await statesOf(wire(head(), day('2026-09-15', [], spent(0.25, 10)), day('2026-09-14', [], spent(0.5, 20))));

    expect(states.map((state) => state.unnamedSpend)).toEqual([null, spent(0.25, 10), spent(0.75, 30)]);
    expect(states.at(-1)?.totals).toMatchObject({ cost: 0.75, tokens: 120, unnamedSpend: 0.75 });
  });

  it('has no Unnamed spend when no day carries any, as when the filter names a skill', async () => {
    const states = await statesOf(wire(head(), day('2026-09-15', []), end(complete)));

    expect(states.map((state) => state.unnamedSpend)).toEqual([null, null, null]);
  });

  it('lists the catalogue skills at zero from the head, until a day names them', async () => {
    const [atHead, afterDay] = await statesOf(
      wire(head(['probekit:probe-local', 'probekit:probe-plugin']), day('2026-09-15', [fired('probekit:probe-plugin', 2, null)])),
    );

    expect(atHead?.skills.map((skill) => [skill.name, skill.activations, skill.spend, skill.each])).toEqual([
      ['probekit:probe-local', 0, spent(0), null],
      ['probekit:probe-plugin', 0, spent(0), null],
    ]);
    expect(atHead?.totals.skills).toBe(2);

    // The catalogue's zero named no Turns, so it does not outweigh a day that says they went unnamed.
    expect(afterDay?.skills.map((skill) => [skill.name, skill.activations, skill.spend])).toEqual([
      ['probekit:probe-local', 0, spent(0)],
      ['probekit:probe-plugin', 2, null],
    ]);
  });

  it('shows no figures before a day lands or from a store that could not be read', async () => {
    const unreachable: Gap = { kind: 'unreachable', missing: 'Studio could not read the events store.' };

    const landing = await statesOf(wire(head(['probekit:probe-local']), day('2026-09-15', []), end(complete)));
    const down = await statesOf(wire(head(['probekit:probe-local']), end(unreachable)));

    expect([null, ...landing].map(showsFigures)).toEqual([false, false, true, true]);
    expect(down.map(showsFigures)).toEqual([false, false]);
  });

  it('keeps the landed days and marks the rest missing, not zero, when the store stops part way', async () => {
    const states = await statesOf(wire(head(), day('2026-09-15', [fired('grilling', 2, spent(1))]), end(stopped)));

    expect(states.map((state) => [state.landedDays, state.missingDays])).toEqual([
      [[], []],
      [['2026-09-15'], []],
      [['2026-09-15'], ['2026-09-14']],
    ]);
    expect(states.at(-1)?.totals).toMatchObject({ cost: 1, activations: 2 });
    expect(states.at(-1)?.gap).toEqual(stopped);
  });

  it('shows the figures of the days that landed when the store stops part way', async () => {
    const states = await statesOf(wire(head(['probekit:probe-local']), day('2026-09-15', []), end(stopped)));

    expect(states.map(showsFigures)).toEqual([false, true, true]);
  });

  it('cuts a span of one day into hour slices of every skill\'s Activations', async () => {
    const [atHead, afterDay] = await statesOf(
      wire(
        head([], ['2026-09-15']),
        day('2026-09-15', [
          fired('grilling', 3, spent(1), { hours: hours({ 9: 2, 17: 1 }) }),
          fired('tdd', 1, spent(1), { hours: hours({ 9: 1 }) }),
        ]),
      ),
    );

    expect(atHead?.slices).toHaveLength(24);
    expect(atHead?.slices.every((slice) => slice.state === 'arriving')).toBe(true);
    expect(afterDay?.slices.map((slice) => [slice.startHour, slice.lengthInHours, slice.state, slice.activations])).toEqual(
      Array.from({ length: 24 }, (_, hour) => [hour, 1, 'landed', hour === 9 ? 3 : hour === 17 ? 1 : 0]),
    );
  });

  it('cuts a span of up to a week into six-hour slices, oldest first, and fills them from the right as days land', async () => {
    const states = await statesOf(
      wire(
        head([], daysBack(7)),
        day('2026-09-15', [fired('grilling', 4, spent(1), { hours: hours({ 0: 1, 5: 1, 6: 1, 23: 1 }) })]),
      ),
    );

    const slices = states.at(-1)?.slices ?? [];

    expect(slices).toHaveLength(28);
    expect(slices.slice(0, 4).map((slice) => [slice.day, slice.startHour, slice.lengthInHours])).toEqual([
      ['2026-09-09', 0, 6],
      ['2026-09-09', 6, 6],
      ['2026-09-09', 12, 6],
      ['2026-09-09', 18, 6],
    ]);
    expect(slices.slice(0, 24).every((slice) => slice.state === 'arriving' && slice.activations === null)).toBe(true);
    expect(slices.slice(24).map((slice) => [slice.day, slice.state, slice.activations])).toEqual([
      ['2026-09-15', 'landed', 2],
      ['2026-09-15', 'landed', 1],
      ['2026-09-15', 'landed', 0],
      ['2026-09-15', 'landed', 1],
    ]);
  });

  it('cuts a span longer than a week into day slices', async () => {
    const states = await statesOf(
      wire(
        head([], daysBack(8)),
        day('2026-09-15', [fired('grilling', 3, spent(1), { hours: hours({ 2: 1, 20: 2 }) })]),
        day('2026-09-14', []),
      ),
    );

    expect(states.at(-1)?.slices.map((slice) => [slice.day, slice.startHour, slice.lengthInHours, slice.activations])).toEqual([
      ...daysBack(8)
        .slice(2)
        .toReversed()
        .map((date) => [date, 0, 24, null]),
      ['2026-09-14', 0, 24, 0],
      ['2026-09-15', 0, 24, 3],
    ]);
  });

  it('marks the slices of days the store never gave missing, with no count, once the answer ends', async () => {
    const states = await statesOf(wire(head(), day('2026-09-15', [fired('grilling', 2, spent(1), { hours: hours({ 9: 2 }) })]), end(stopped)));

    expect(states.map((state) => state.slices.map((slice) => [slice.day, slice.state, slice.activations]))).toEqual([
      [...Array.from({ length: 4 }, () => ['2026-09-14', 'arriving', null]), ...Array.from({ length: 4 }, () => ['2026-09-15', 'arriving', null])],
      [
        ...Array.from({ length: 4 }, () => ['2026-09-14', 'arriving', null]),
        ['2026-09-15', 'landed', 0],
        ['2026-09-15', 'landed', 2],
        ['2026-09-15', 'landed', 0],
        ['2026-09-15', 'landed', 0],
      ],
      [
        ...Array.from({ length: 4 }, () => ['2026-09-14', 'missing', null]),
        ['2026-09-15', 'landed', 0],
        ['2026-09-15', 'landed', 2],
        ['2026-09-15', 'landed', 0],
        ['2026-09-15', 'landed', 0],
      ],
    ]);
  });

  it('keeps the start of the last UTC hour each skill fired in, across the days that landed', async () => {
    const states = await statesOf(
      wire(
        head(['probekit:probe-local']),
        day('2026-09-15', [
          fired('grilling', 2, spent(1), { hours: hours({ 3: 1, 9: 1 }) }),
          fired('spender', 0, spent(1)),
        ]),
        day('2026-09-14', [
          fired('grilling', 1, spent(1), { hours: hours({ 22: 1 }) }),
          fired('tdd', 1, spent(1), { hours: hours({ 23: 1 }) }),
        ]),
      ),
    );

    expect(states.map((state) => state.skills.map((skill) => [skill.name, skill.lastFired]))).toEqual([
      [['probekit:probe-local', null]],
      [
        ['grilling', '2026-09-15T09:00:00Z'],
        ['probekit:probe-local', null],
        ['spender', null],
      ],
      [
        ['grilling', '2026-09-15T09:00:00Z'],
        ['probekit:probe-local', null],
        ['spender', null],
        ['tdd', '2026-09-14T23:00:00Z'],
      ],
    ]);
  });

  it('adds a skill\'s Activations by trigger across the days that landed', async () => {
    const states = await statesOf(
      wire(
        head(),
        day('2026-09-15', [
          fired('grilling', 3, spent(1), {
            triggers: [
              { trigger: 'claude-proactive', activations: 2 },
              { trigger: 'user-slash', activations: 1 },
            ],
          }),
        ]),
        day('2026-09-14', [
          fired('grilling', 3, spent(1), {
            triggers: [
              { trigger: null, activations: 1 },
              { trigger: 'user-slash', activations: 2 },
            ],
          }),
        ]),
      ),
    );

    expect(states.map((state) => state.skills[0]?.triggers ?? [])).toEqual([
      [],
      [
        { trigger: 'claude-proactive', activations: 2 },
        { trigger: 'user-slash', activations: 1 },
      ],
      // An absent trigger first, as the answer orders them, so a skill reads the same however many days it spans.
      [
        { trigger: null, activations: 1 },
        { trigger: 'claude-proactive', activations: 2 },
        { trigger: 'user-slash', activations: 3 },
      ],
    ]);
  });

  it('adds up to the skill\'s Activations however many days its triggers span', async () => {
    const states = await statesOf(
      wire(
        head(),
        day('2026-09-15', [fired('grilling', 2, spent(1), { triggers: [{ trigger: 'user-slash', activations: 2 }] })]),
        day('2026-09-14', [fired('grilling', 1, spent(1), { triggers: [{ trigger: 'user-slash', activations: 1 }] })]),
      ),
    );

    const grilling = states.at(-1)?.skills[0];

    expect(grilling?.triggers.reduce((sum, trigger) => sum + trigger.activations, 0)).toBe(grilling?.activations);
  });

  it('fills a skill\'s chart slice by slice, in step with the activity strip', async () => {
    const states = await statesOf(
      wire(
        head([], daysBack(7)),
        day('2026-09-15', [fired('grilling', 3, spent(1), { hours: hours({ 5: 1, 6: 2 }) })]),
        day('2026-09-14', [fired('grilling', 1, spent(1), { hours: hours({ 20: 1 }) })]),
      ),
    );

    // One count per slice, so a bar of the chart covers the same six hours as the slice above it.
    expect(states.map((state) => state.skills[0]?.spark.slice(20) ?? [])).toEqual([
      [],
      [0, 0, 0, 0, 1, 2, 0, 0],
      [0, 0, 0, 1, 1, 2, 0, 0],
    ]);
    expect(states.at(-1)?.skills[0]?.spark).toHaveLength(states.at(-1)?.slices.length ?? 0);
  });

  it('gives a catalogue skill that never fired a chart of nothing rather than no chart', async () => {
    const [atHead] = await statesOf(wire(head(['probekit:probe-local'], ['2026-09-15'])));

    expect(atHead?.skills[0]?.spark).toEqual(Array.from({ length: 24 }, () => 0));
  });

  it('lands a day whose line the network split across chunks', async () => {
    const text = wire(head(), day('2026-09-15', [fired('grilling', 2, spent(1))]), end(complete)).join('');
    const cut = text.indexOf('grilling');

    const states = await statesOf([text.slice(0, cut), text.slice(cut)]);

    expect(states.map((state) => state.totals.activations)).toEqual([0, 2, 2]);
  });
});
