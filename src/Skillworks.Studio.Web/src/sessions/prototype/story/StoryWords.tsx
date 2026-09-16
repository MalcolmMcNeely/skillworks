// PROTOTYPE — throwaway. Words that arrived, or the hatch that says they were held back and which setting sends them.

import { useState } from 'react';
import type { Said, ToolStep } from '../sessionModel';
import { format } from '../sessionMeasures';

export const settings = {
  prompts: 'OTEL_LOG_USER_PROMPTS=1',
  responses: 'OTEL_LOG_ASSISTANT_RESPONSES=1',
  toolContent: 'OTEL_LOG_TOOL_CONTENT=1',
};

export function Withheld({ length, setting, what = 'Words withheld' }: { length: number; setting: string; what?: string }) {
  return (
    <div className="story-withheld">
      <span>
        {what} · {format.int(length)} characters
      </span>
      <code>{setting}</code>
    </div>
  );
}

export function Words({ said, setting, tone }: { said: Said; setting: string; tone: 'typed' | 'written' | 'aside' }) {
  const [all, setAll] = useState(false);

  if (said.text === null) {
    // Narration between tool calls is short and frequent; a full-width hatch for each one would bury the chapter.
    return tone === 'aside' ? (
      <span className="story-withheld is-inline" title={setting}>
        Words withheld · {format.int(said.length)} characters
      </span>
    ) : (
      <Withheld length={said.length} setting={setting} />
    );
  }

  // A pasted spec can run to thousands of characters; the chapter should stay a chapter.
  const long = said.text.length > 700;
  const text = long && !all ? `${said.text.slice(0, 640)}…` : said.text;

  return (
    <div className={`story-words is-${tone}`}>
      <p>{text}</p>
      {long && (
        <button type="button" className="story-link" onClick={() => setAll(!all)}>
          {all ? 'Show less' : `Show all ${format.int(said.text.length)} characters`}
        </button>
      )}
    </div>
  );
}

export function ToolContent({ step }: { step: ToolStep }) {
  return (
    <div className="story-content">
      <p className="story-micro">Input · {format.bytes(step.inputBytes)}</p>
      <pre className="story-pre">{step.input}</pre>
      <p className="story-micro">
        Output · {format.bytes(step.outputBytes)}
        {step.error !== null && <span className="story-bad"> · {step.error}</span>}
      </p>
      {step.output === null ? (
        <Withheld length={step.outputBytes} setting={settings.toolContent} what="Output withheld" />
      ) : (
        <pre className={`story-pre${step.ok ? '' : ' is-failed'}`}>{step.output}</pre>
      )}
    </div>
  );
}
