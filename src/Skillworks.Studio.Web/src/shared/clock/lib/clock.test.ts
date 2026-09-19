import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clock, resetClock, setClock, type Clock } from './clock';

const noon = Date.parse('2026-09-15T12:00:00Z');
const minute = 60 * 1000;

const stubClock = (): Clock => ({ now: () => noon, tick: () => vi.fn<() => void>() });

describe('the browser Clock', () => {
  // Vitest's still clock, so nobody here hand-writes a queue of pending timers.
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(noon);
  });

  afterEach(() => vi.useRealTimers());

  it('stands still, so two reads give the same answer however long the test took between them', () => {
    expect(clock().now()).toBe(noon);
    expect(clock().now()).toBe(noon);
  });

  it('moves only when the test moves it', () => {
    vi.advanceTimersByTime(90 * minute);

    expect(clock().now()).toBe(noon + 90 * minute);
  });

  it('ticks once for each whole period the test moves past', () => {
    const onTick = vi.fn<() => void>();

    clock().tick(minute, onTick);
    vi.advanceTimersByTime(3 * minute);

    expect(onTick).toHaveBeenCalledTimes(3);
  });

  it('does not tick before the period is up', () => {
    const onTick = vi.fn<() => void>();

    clock().tick(minute, onTick);
    vi.advanceTimersByTime(minute - 1);

    expect(onTick).not.toHaveBeenCalled();
  });

  it('tells a tick the moment it was due, not the moment the test moved to', () => {
    const read: number[] = [];

    clock().tick(minute, () => read.push(clock().now()));
    vi.advanceTimersByTime(2 * minute);

    expect(read).toEqual([noon + minute, noon + 2 * minute]);
  });

  it('stops ticking once the tick is let go', () => {
    const onTick = vi.fn<() => void>();

    const letGo = clock().tick(minute, onTick);
    vi.advanceTimersByTime(minute);
    letGo();
    vi.advanceTimersByTime(10 * minute);

    expect(onTick).toHaveBeenCalledTimes(1);
  });
});

describe('the Clock a test supplies', () => {
  afterEach(() => resetClock());

  it('is the one everything reads once it is handed over', () => {
    const still = stubClock();

    setClock(still);

    expect(clock()).toBe(still);
  });

  it('gives way to the browser Clock again once the test lets go', () => {
    const still = stubClock();

    setClock(still);
    resetClock();

    expect(clock()).not.toBe(still);
  });
});
