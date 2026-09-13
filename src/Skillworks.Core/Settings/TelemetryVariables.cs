namespace Skillworks.Core.Settings;

/// <summary>
/// The environment block Studio owns. Nothing outside this set is ever written or taken away, which
/// is the whole reason turning telemetry off is safe.
/// </summary>
public static class TelemetryVariables
{
    /// <summary>
    /// In the order a developer should read them, so the preview looks the same every time.
    /// Metrics stay off on purpose: their <c>skill.name</c> label reads <c>third-party</c> for a
    /// private catalogue, so only the logs signal answers "which skill fired".
    /// </summary>
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
    ];
}
