namespace Skillworks.Core.Shared.Telemetry;

public static class TelemetryVariables
{
    // All of them or none: a run recorded with only some of these cannot be read in full.
    public static IReadOnlyList<KeyValuePair<string, string>> For(string collectorEndpoint) =>
        [.. Events(collectorEndpoint), .. Words, .. Traces];

    // Metrics stay off: their skill.name label reads third-party for a private catalogue.
    private static IReadOnlyList<KeyValuePair<string, string>> Events(string collectorEndpoint) =>
    [
        // Nothing is exported at all without this one.
        new("CLAUDE_CODE_ENABLE_TELEMETRY", "1"),
        // skill_activated is a log event, so the logs exporter is the one that carries provenance.
        new("OTEL_LOGS_EXPORTER", "otlp"),
        // Without this the skill name arrives as the placeholder "custom_skill".
        new("OTEL_LOG_TOOL_DETAILS", "1"),
        new("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf"),
        new("OTEL_EXPORTER_OTLP_ENDPOINT", collectorEndpoint),
        // Despite its name, from Claude Code 2.1.269 this puts the vcs.* repository attributes on log events too.
        new("OTEL_METRICS_INCLUDE_REPOSITORY", "true"),
    ];

    // Without these a prompt, an answer and a tool result all arrive as <REDACTED>.
    public static IReadOnlyList<KeyValuePair<string, string>> Words =>
    [
        new("OTEL_LOG_USER_PROMPTS", "1"),
        new("OTEL_LOG_ASSISTANT_RESPONSES", "1"),
        new("OTEL_LOG_TOOL_CONTENT", "1"),
    ];

    // Health reads these on their own, to tell a trace store nobody switched on from a broken one.
    public static IReadOnlyList<KeyValuePair<string, string>> Traces =>
    [
        // Spans are beta, and without this one Claude Code makes none at all.
        new("CLAUDE_CODE_ENHANCED_TELEMETRY_BETA", "1"),
        new("OTEL_TRACES_EXPORTER", "otlp"),
    ];
}
