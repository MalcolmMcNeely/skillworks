namespace Skillworks.Core.Telemetry;

public static class TelemetryVariables
{
    // Metrics stay off: their skill.name label reads third-party for a private catalogue.
    public static IReadOnlyList<KeyValuePair<string, string>> For(string collectorEndpoint) =>
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

    // Held apart from the rest until the switch writes them, so a trace store with nothing in it reads as off.
    public static IReadOnlyList<KeyValuePair<string, string>> Traces =>
    [
        // Spans are beta, and without this one Claude Code makes none at all.
        new("CLAUDE_CODE_ENHANCED_TELEMETRY_BETA", "1"),
        new("OTEL_TRACES_EXPORTER", "otlp"),
    ];
}
