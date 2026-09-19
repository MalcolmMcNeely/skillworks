using System.Text.Json.Nodes;

namespace Skillworks.Core.Shared.Telemetry;

// Never written: this file switches recording on for colleagues who are not at the keyboard, so a person commits it.
public sealed record TeamSettings(string Path, string Text)
{
    // Rendered by the same hand that writes the developer's own file, or the two would drift apart unnoticed.
    public static TeamSettings For(ClaudeSettingsFile file, string collectorEndpoint) =>
        new(".claude/settings.json", file.Render(Document(collectorEndpoint)));

    private static JsonObject Document(string collectorEndpoint) => new()
    {
        ["env"] = new JsonObject(
            TelemetryVariables.For(collectorEndpoint)
                .Select(variable => KeyValuePair.Create(variable.Key, (JsonNode?)JsonValue.Create(variable.Value)))),
    };
}
