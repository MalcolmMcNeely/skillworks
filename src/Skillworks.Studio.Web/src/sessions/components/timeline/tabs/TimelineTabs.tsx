import { useState } from 'react';
import type { Spell } from '../../../lib/timeline/view';
import type { Highlight } from '../../../lib/timeline/highlight';
import type { Level } from '../../../lib/timeline/context';
import type { SkillRow } from '../../../lib/timeline/skills';
import type { ToolRow } from '../../../lib/timeline/tools';
import type { Mark } from '../../../lib/steps';
import { ContextTab } from './ContextTab';
import { CostTabPrototype } from './CostTabPrototype';
import { SkillsTab } from './SkillsTab';
import { ToolsTab } from './ToolsTab';

type TabKey = 'context' | 'skills' | 'tools' | 'cost';

const tabs: readonly { key: TabKey; label: string }[] = [
  { key: 'context', label: 'Context' },
  { key: 'skills', label: 'Skills' },
  { key: 'tools', label: 'Tools' },
  // PROTOTYPE — throwaway: the Cost tab is being judged.
  { key: 'cost', label: 'Cost' },
];

export function TimelineTabs({
  levels,
  limitTokens,
  skills,
  cost,
  tools,
  marks,
  view,
  subagentOpen,
  selected,
  highlight,
  onOpen,
  onHighlight,
}: {
  levels: readonly Level[];
  limitTokens: number | null;
  skills: readonly SkillRow[];
  cost: number;
  tools: readonly ToolRow[];
  marks: readonly Mark[];
  view: Spell | null;
  subagentOpen: boolean;
  selected: string | null;
  highlight: Highlight | null;
  onOpen: (step: string) => void;
  onHighlight: (picked: Highlight) => void;
}) {
  const [shown, setShown] = useState<TabKey>(
    // PROTOTYPE — throwaway: ?tab=cost opens the Cost tab first, so a link can land on it.
    new URLSearchParams(window.location.search).get('tab') === 'cost'
      ? 'cost'
      : highlight === null
        ? 'context'
        : highlight.kind === 'tool'
          ? 'tools'
          : 'skills',
  );

  return (
    <section className="session-panel timeline-tabs" aria-label="What is in view">
      <div className="tab-row" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            id={`tab-${tab.key}`}
            aria-selected={tab.key === shown}
            aria-controls={`tab-panel-${tab.key}`}
            className={`tab${tab.key === shown ? ' is-shown' : ''}`}
            onClick={() => setShown(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-panel" role="tabpanel" id={`tab-panel-${shown}`} aria-labelledby={`tab-${shown}`}>
        {shown === 'context' ? (
          <ContextTab levels={levels} limitTokens={limitTokens} view={view} selected={selected} onOpen={onOpen} />
        ) : shown === 'skills' ? (
          <SkillsTab
            rows={skills}
            cost={cost}
            inView={view !== null}
            wholeRun={subagentOpen}
            highlight={highlight}
            onPick={onHighlight}
          />
        ) : shown === 'tools' ? (
          <ToolsTab rows={tools} inView={view !== null} highlight={highlight} onPick={onHighlight} />
        ) : (
          <CostTabPrototype marks={marks} view={view} selected={selected} onOpen={onOpen} />
        )}
      </div>
    </section>
  );
}
