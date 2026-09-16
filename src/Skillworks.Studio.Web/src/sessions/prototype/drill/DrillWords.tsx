// PROTOTYPE — throwaway. How variant A prints words and tool output, and what it prints when they were withheld.

import type { Said } from '../sessionModel';
import { format } from '../sessionMeasures';
import { settings } from './useDrillSession';

export function DrillWords({ said, setting, clamp }: { said: Said; setting: keyof typeof settings; clamp?: number }) {
  if (said.text === null) {
    return (
      <div className="drill-withheld">
        <span>Words withheld · {format.int(said.length)} characters</span>
        <code>{settings[setting]}</code>
      </div>
    );
  }

  const text = clamp !== undefined && said.text.length > clamp ? `${said.text.slice(0, clamp)}…` : said.text;

  return <blockquote className="drill-said">{text}</blockquote>;
}

export function DrillOutput({ output, bytes }: { output: string | null; bytes: number }) {
  if (output === null) {
    return (
      <div className="drill-withheld">
        <span>Output withheld · {format.bytes(bytes)}</span>
        <code>{settings.toolContent}</code>
      </div>
    );
  }

  return <pre className="drill-pre">{output}</pre>;
}
