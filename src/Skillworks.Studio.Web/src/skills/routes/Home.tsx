import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { RepositoryPicker } from '../../filters/components/RepositoryPicker';
import { filterParams, readFilter, type Filter } from '../../filters/lib/filters';
import { spanKeyOf, spanKeys, todayUtc, withSpanKey } from '../../filters/lib/spanKeys';
import { SignalWord } from '../../gaps/components/SignalWord';
import { HealthPanel } from '../../health/components/HealthPanel';
import { describeFetchFailure } from '../../http/lib/errors';
import { Keys } from '../../keys/components/Keys';
import { TelemetrySwitch } from '../../telemetry/components/TelemetrySwitch';
import { fetchSkills } from '../api/skills';
import { RailTotals } from '../components/RailTotals';
import { SkillMap } from '../components/SkillMap';
import { readMapChoice, withMapChoice, type MapChoice } from '../lib/mapChoice';
import type { SkillsAnswer } from '../lib/skills';

interface Reading {
  // The filter the answer was asked for, as text, so the screen can tell an answer for an older filter.
  narrowing: string;
  answer: SkillsAnswer | null;
  failure: string | null;
}

export function Home() {
  const [reading, setReading] = useState<Reading | null>(null);

  // Filter, view and order live in the address bar, so a reload, a bookmark or the back button lands on the same map.
  const [params, setParams] = useSearchParams();
  // No skill: Home offers no way to see or clear one, so an old link naming a skill must not narrow it unseen.
  const filter: Filter = { ...readFilter(params), skill: '' };
  const choice = readMapChoice(params);

  // Text, as a filter object is new every render; the view and order are left out as they need no new answer.
  const narrowing = filterParams(filter).toString();

  useEffect(() => {
    const abort = new AbortController();

    // Read back out of the text, so the effect depends only on what it is keyed on.
    fetchSkills(readFilter(new URLSearchParams(narrowing)), abort.signal).then(
      (answer) => setReading({ narrowing, answer, failure: null }),
      (failure: unknown) => {
        // An abort is the page tidying up after itself, not a failure worth showing.
        if (!abort.signal.aborted) {
          setReading({ narrowing, answer: null, failure: describeFetchFailure(failure) });
        }
      },
    );

    return () => abort.abort();
  }, [narrowing]);

  const answer = reading?.answer ?? null;
  const arriving = reading !== null && reading.narrowing !== narrowing;
  const today = todayUtc(new Date());

  // With no dates asked, the answer names the lookback, whose length only the API knows.
  const shownSpan = filter.from !== '' || filter.to !== '' ? filter : arriving ? null : (answer?.span ?? null);

  // Replaced, not pushed, so trying four spans does not cost four presses of the back button.
  const show = (nextFilter: Filter, nextChoice: MapChoice) =>
    setParams(withMapChoice(filterParams(nextFilter), nextChoice), { replace: true });

  return (
    <main className="home">
      <aside className="rail" aria-label="Instruments">
        <div className="rail-brand">
          <h1>Skillworks</h1>
          <SignalWord gap={answer?.gap ?? null} failure={reading?.failure ?? null} />
        </div>

        <section className="rail-block" aria-label="Narrow">
          <Keys
            label="Span"
            pressed={shownSpan === null ? null : spanKeyOf(shownSpan, today)}
            options={spanKeys}
            onPress={(key) => show(withSpanKey(filter, key, today), choice)}
          />
          <RepositoryPicker repository={filter.repository} onChange={(repository) => show({ ...filter, repository }, choice)} />
        </section>

        {/* No figures from a store that could not be read, as never-fired skills would total a quiet zero. */}
        <RailTotals answer={answer?.gap.kind === 'unreachable' ? null : answer} arriving={arriving} />

        <section className="rail-block rail-systems" aria-label="Systems">
          <HealthPanel />
          <TelemetrySwitch />
        </section>
      </aside>

      <SkillMap
        answer={answer}
        failure={reading?.failure ?? null}
        arriving={arriving}
        choice={choice}
        onChoose={(next) => show(filter, next)}
      />
    </main>
  );
}
