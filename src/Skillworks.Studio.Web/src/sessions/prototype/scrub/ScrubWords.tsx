// PROTOTYPE — throwaway. Words as they reached the store: the text itself, or the purple hatch that says it was held
// back, how long it was and which setting would send it.

import type { Said, ToolStep } from '../sessionModel';
import { format } from '../sessionMeasures';
import { settings } from './scrubRange';

export function ScrubWords({ said, setting, clip }: { said: Said; setting: string; clip?: number }) {
  if (said.text === null) {
    return (
      <div className="scrub-withheld">
        <span>Withheld · {format.int(said.length)} characters</span>
        <code>{setting}=1</code>
      </div>
    );
  }

  const text = clip !== undefined && said.text.length > clip ? `${said.text.slice(0, clip)}…` : said.text;
  return <blockquote className="scrub-said">{text}</blockquote>;
}

export function ScrubToolContent({ tool }: { tool: ToolStep }) {
  return (
    <div className="scrub-io">
      <p className="scrub-micro">Sent to the tool · {format.bytes(tool.inputBytes)}</p>
      <pre className="scrub-pre">{tool.input}</pre>
      <p className="scrub-micro">Came back · {format.bytes(tool.outputBytes)}</p>
      {tool.output === null ? (
        <div className="scrub-withheld">
          <span>Withheld · {format.bytes(tool.outputBytes)}</span>
          <code>{settings.toolContent}=1</code>
        </div>
      ) : (
        <pre className={`scrub-pre${tool.ok ? '' : ' is-failed'}`}>{tool.output}</pre>
      )}
    </div>
  );
}
