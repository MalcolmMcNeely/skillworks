import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { RepositoryPicker } from '../../filters/components/RepositoryPicker';
import { filterParams, readFilter, type Filter } from '../../filters/lib/filters';
import { spanKeyOf, spanKeys, todayUtc, withSpanKey } from '../../filters/lib/spanKeys';
import { SignalWord } from '../../gaps/components/SignalWord';
import { HealthLamps } from '../../health/components/HealthLamps';
import { describeFetchFailure } from '../../http/lib/errors';
import { Keys } from '../../keys/components/Keys';
import { UpButton } from '../../pages/components/UpButton';
import { useTabTitle } from '../../pages/components/useTabTitle';
import { watch } from '../../pages/lib/pages';
import { TelemetrySwitch } from '../../telemetry/components/TelemetrySwitch';
import { fetchSkills } from '../api/skills';
import { ActivityStrip } from '../components/ActivityStrip';
import { RailTotals } from '../components/RailTotals';
import { SkillMap } from '../components/SkillMap';
import { foldSkillsLine, showsFigures, type SkillsAnswer } from '../lib/answer';
import { readMapChoice, withMapChoice, type MapChoice } from '../lib/mapChoice';

interface Reading {
  // The filter the answer was asked for, as text, so the screen can tell an answer for an older filter.
  narrowing: string;
  answer: SkillsAnswer | null;
  failure: string | null;
}

export function Watch() {
  const [reading, setReading] = useState<Reading | null>(null);

  useTabTitle(watch.tabTitle);

  // Filter, view and order live in the address bar, so a reload, a bookmark or the back button lands on the same map.
  const [params, setParams] = useSearchParams();
  // No skill: Watch offers no way to see or clear one, so an old link naming a skill must not narrow it unseen.
  const filter: Filter = { ...readFilter(params), skill: '' };
  const choice = readMapChoice(params);

  // Text, as a filter object is new every render; the view and order are left out as they need no new answer.
  const narrowing = filterParams(filter).toString();

  useEffect(() => {
    const abort = new AbortController();

    const read = async () => {
      let answer: SkillsAnswer | null = null;

      // Read back out of the text, so the effect depends only on what it is keyed on.
      for await (const line of fetchSkills(readFilter(new URLSearchParams(narrowing)), abort.signal)) {
        answer = foldSkillsLine(answer, line);
        setReading({ narrowing, answer, failure: null });
      }
    };

    read().catch((failure: unknown) => {
      // An abort is the page tidying up after itself, not a failure worth showing.
      if (!abort.signal.aborted) {
        setReading({ narrowing, answer: null, failure: describeFetchFailure(failure) });
      }
    });

    // A changed filter stops the old answer, so its days never land in the new view.
    return () => abort.abort();
  }, [narrowing]);

  const answer = reading?.answer ?? null;
  const forOlderFilter = reading !== null && reading.narrowing !== narrowing;
  const arriving = forOlderFilter || (answer?.arriving ?? false);
  const today = todayUtc(new Date());

  // With no dates asked, the answer names the lookback, whose length only the API knows.
  const shownSpan = filter.from !== '' || filter.to !== '' ? filter : forOlderFilter ? null : (answer?.span ?? null);

  // Replaced, not pushed, so trying four spans does not cost four presses of the back button.
  const show = (nextFilter: Filter, nextChoice: MapChoice) =>
    setParams(withMapChoice(filterParams(nextFilter), nextChoice), { replace: true });

  return (
    <main className="page watch">
      <aside className="rail" aria-label="Instruments">
        <div className="rail-brand">
          <UpButton parent={watch.parent} />
          <h1>{watch.name}</h1>
          <SignalWord gap={answer?.gap ?? null} failure={reading?.failure ?? null} />
        </div>

        <section className="rail-block systems" aria-label="Systems">
          <HealthLamps />
          <TelemetrySwitch />
        </section>

        <section className="rail-block" aria-label="Narrow">
          <Keys
            label="Span"
            pressed={shownSpan === null ? null : spanKeyOf(shownSpan, today)}
            options={spanKeys}
            onPress={(key) => show(withSpanKey(filter, key, today), choice)}
          />
          <RepositoryPicker
            span={filter}
            repository={filter.repository}
            onChange={(repository) => show({ ...filter, repository }, choice)}
          />
        </section>

        <RailTotals answer={showsFigures(answer) ? answer : null} arriving={arriving} />
      </aside>

      <div className="board">
        <ActivityStrip answer={answer} failure={reading?.failure ?? null} arriving={arriving} />
        <SkillMap
          answer={answer}
          failure={reading?.failure ?? null}
          arriving={arriving}
          choice={choice}
          onChoose={(next) => show(filter, next)}
        />
      </div>
    </main>
  );
}
