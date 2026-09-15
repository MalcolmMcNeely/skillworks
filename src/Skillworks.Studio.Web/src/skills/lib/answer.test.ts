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

function head(catalogueSkills: string[] = []): SkillsLine {
  return { kind: 'head', span, days: ['2026-09-15', '2026-09-14'], catalogueSkills };
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

  return { name, activations, repositories: [], models: named, efforts: named, spend, origins: [], ...more };
}

const complete: Gap = { kind: 'complete', missing: null };

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
          fired('grilling', 3, spent(0.3), { repositories: ['acme/xi'], models: ['claude-sonnet-5'], efforts: ['high'], origins: [proactive] }),
        ]),
        day('2026-09-14', [
          fired('grilling', 1, spent(0.5), {
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
        repositories: ['acme/nu', 'acme/xi'],
        models: ['claude-opus-5[1m]', 'claude-sonnet-5'],
        efforts: ['high'],
        spend: spent(0.8),
        each: 0.2,
        origins: [proactive, typed],
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

  it('lands a day whose line the network split across chunks', async () => {
    const text = wire(head(), day('2026-09-15', [fired('grilling', 2, spent(1))]), end(complete)).join('');
    const cut = text.indexOf('grilling');

    const states = await statesOf([text.slice(0, cut), text.slice(cut)]);

    expect(states.map((state) => state.totals.activations)).toEqual([0, 2, 2]);
  });
});
