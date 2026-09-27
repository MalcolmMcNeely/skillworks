import { useState } from 'react';
import type { Range } from '../../lib/view';
import type { Highlight } from '../../lib/highlight';
import type { ActivationSpell } from '../../lib/panels/activations';
import type { Level } from '../../lib/panels/context';
import type { ToolRow } from '../../lib/panels/tools';
import { ContextTab } from './ContextTab';
import { SkillsTab } from './SkillsTab';
import { ToolsTab } from './ToolsTab';

type TabKey = 'context' | 'skills' | 'tools';

const tabs: readonly { key: TabKey; label: string }[] = [
  { key: 'context', label: 'Context' },
  { key: 'skills', label: 'Skills' },
  { key: 'tools', label: 'Tools' },
];

export function TimelineTabs({
  levels,
  limitTokens,
  spells,
  tools,
  view,
  selected,
  opened,
  highlight,
  onOpen,
  onActivation,
  onHighlight,
}: {
  levels: readonly Level[];
  limitTokens: number | null;
  spells: readonly ActivationSpell[];
  tools: readonly ToolRow[];
  view: Range | null;
  selected: string | null;
  opened: string | null;
  highlight: Highlight | null;
  onOpen: (step: string) => void;
  onActivation: (spell: ActivationSpell) => void;
  onHighlight: (picked: Highlight) => void;
}) {
  const [shown, setShown] = useState<TabKey>(highlight?.kind === 'tool' ? 'tools' : 'context');

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
          <SkillsTab spells={spells} view={view} opened={opened} onOpen={onActivation} />
        ) : (
          <ToolsTab rows={tools} inView={view !== null} highlight={highlight} onPick={onHighlight} />
        )}
      </div>
    </section>
  );
}
