import { describe, expect, it } from 'vitest';
import { describeSlice, nowAt, slicesOf, stripLabels, type StripSlice } from './strip';

const dayMilliseconds = 24 * 60 * 60 * 1000;

function daysTo(newest: string, count: number): string[] {
  return Array.from({ length: count }, (_, back) =>
    new Date(Date.parse(`${newest}T00:00:00Z`) - back * dayMilliseconds).toISOString().slice(0, 10),
  );
}

function landed(slice: StripSlice, activations: number): StripSlice {
  return { ...slice, state: 'landed', activations };
}

const span = { fromUtc: '2026-09-14T00:00:00+00:00', untilUtc: '2026-09-16T00:00:00+00:00' };

describe('stripLabels', () => {
  it('labels every sixth hour of a one-day strip', () => {
    expect(stripLabels(slicesOf(['2026-09-15']))).toEqual([
      { at: 0, text: '00:00' },
      { at: 0.25, text: '06:00' },
      { at: 0.5, text: '12:00' },
      { at: 0.75, text: '18:00' },
    ]);
  });

  it('labels every day of a week, at the slice the day starts on', () => {
    const labels = stripLabels(slicesOf(daysTo('2026-09-15', 7)));

    expect(labels.map((label) => label.text)).toEqual(['09 Sep', '10 Sep', '11 Sep', '12 Sep', '13 Sep', '14 Sep', '15 Sep']);
    expect(labels.map((label) => label.at)).toEqual([0, 1 / 7, 2 / 7, 3 / 7, 4 / 7, 5 / 7, 6 / 7]);
  });

  it('labels one day a week or fewer on a longer strip, so no two labels overlap', () => {
    expect(stripLabels(slicesOf(daysTo('2026-09-30', 30))).map((label) => label.text)).toEqual([
      '01 Sep',
      '08 Sep',
      '15 Sep',
      '22 Sep',
      '29 Sep',
    ]);
    expect(stripLabels(slicesOf(daysTo('2026-09-30', 365)))).toHaveLength(8);
  });

  it('labels nothing while the strip has no slices', () => {
    expect(stripLabels([])).toEqual([]);
  });
});

describe('nowAt', () => {
  it('places the mark where the moment falls in the span', () => {
    expect(nowAt(span, Date.parse('2026-09-15T12:00:00Z'))).toBe(0.75);
  });

  it('has no place for a moment before or after the span', () => {
    expect(nowAt(span, Date.parse('2026-09-13T23:59:59Z'))).toBeNull();
    expect(nowAt(span, Date.parse('2026-09-16T00:00:00Z'))).toBeNull();
  });
});

describe('describeSlice', () => {
  it('reads a landed slice as its hour and its Activations', () => {
    const slices = slicesOf(['2026-09-15']).map((slice) => landed(slice, 1200));

    expect(slices.slice(9, 10).map(describeSlice)).toEqual(['15 Sep 09:00 UTC. Activations 1,200.']);
  });

  it('reads a whole day without an hour, and says which of arriving and missing it is', () => {
    const readings = slicesOf(daysTo('2026-09-15', 8))
      .slice(0, 1)
      .flatMap((slice) => [describeSlice(slice), describeSlice({ ...slice, state: 'missing', activations: null })]);

    expect(readings).toEqual(['08 Sep UTC. Arriving.', '08 Sep UTC. Missing.']);
  });

  it('reads an hour slice that has not landed by its hour', () => {
    expect(slicesOf(['2026-09-15']).slice(0, 1).map(describeSlice)).toEqual(['15 Sep 00:00 UTC. Arriving.']);
  });
});
