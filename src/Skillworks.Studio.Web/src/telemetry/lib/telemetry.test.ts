import { describe, expect, it } from 'vitest';
import { describeChange, describeTelemetry } from './telemetry';

const settingsPath = 'C:\\Users\\dev\\.claude\\settings.json';

describe('describeTelemetry', () => {
  it('says so when Claude Code is emitting', () => {
    expect(
      describeTelemetry({ emitting: true, readable: true, settingsPath, problem: null }),
    ).toBe('Claude Code is emitting telemetry to Studio.');
  });

  it('says so when Claude Code is not emitting', () => {
    expect(
      describeTelemetry({ emitting: false, readable: true, settingsPath, problem: null }),
    ).toBe('Claude Code is not emitting telemetry to Studio.');
  });

  it('names the file and the problem when the settings cannot be read', () => {
    const sentence = describeTelemetry({
      emitting: false,
      readable: false,
      settingsPath,
      problem: 'its top level is not an object',
    });

    expect(sentence).toContain(settingsPath);
    expect(sentence).toContain('its top level is not an object');
  });
});

describe('describeChange', () => {
  it('shows the value a variable would lose', () => {
    expect(describeChange({ name: 'OTEL_LOGS_EXPORTER', from: 'console', to: 'otlp' })).toBe(
      'OTEL_LOGS_EXPORTER: console → otlp',
    );
  });

  it('says a variable is not set rather than showing an empty gap', () => {
    expect(describeChange({ name: 'OTEL_LOGS_EXPORTER', from: null, to: 'otlp' })).toBe(
      'OTEL_LOGS_EXPORTER: not set → otlp',
    );
  });
});
