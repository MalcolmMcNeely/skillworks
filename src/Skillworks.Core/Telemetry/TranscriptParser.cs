using System.Text.Json;

namespace Skillworks.Core.Telemetry;

/// <summary>
/// Turns one transcript line into the activations it records. A Skill tool use is a firing, so one
/// assistant record can hold several. Internal on purpose: the tests drive the API, not this.
/// </summary>
internal static class TranscriptParser
{
    public static List<Activation> Activations(string line)
    {
        var activations = new List<Activation>();

        using var document = Parse(line);

        if (document is null || document.RootElement.ValueKind != JsonValueKind.Object)
        {
            return activations;
        }

        var record = document.RootElement;

        if (Text(record, "type") != "assistant" ||
            !record.TryGetProperty("message", out var message) ||
            !message.TryGetProperty("content", out var content) ||
            content.ValueKind != JsonValueKind.Array)
        {
            return activations;
        }

        foreach (var block in content.EnumerateArray())
        {
            if (block.ValueKind != JsonValueKind.Object ||
                Text(block, "type") != "tool_use" ||
                Text(block, "name") != "Skill" ||
                !block.TryGetProperty("input", out var input) ||
                Text(input, "skill") is not { } skill ||
                Text(block, "id") is not { } toolUseId)
            {
                continue;
            }

            activations.Add(new Activation
            {
                ToolUseId = toolUseId,
                SkillName = skill,
                SessionId = Text(record, "sessionId") ?? "",
                Repository = Repository(Text(record, "cwd")),
                GitBranch = Text(record, "gitBranch"),
                TimestampUtc = Timestamp(record),
            });
        }

        return activations;
    }

    /// <summary>A line Studio cannot read is one line, never the other 1,470. It is skipped.</summary>
    private static JsonDocument? Parse(string line)
    {
        if (string.IsNullOrWhiteSpace(line))
        {
            return null;
        }

        try
        {
            return JsonDocument.Parse(line);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static string? Text(JsonElement element, string property) =>
        element.TryGetProperty(property, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    /// <summary>
    /// Split by hand rather than with Path, because a Windows transcript read on Linux still has to
    /// yield "alpha" from "C:\Projects\alpha".
    /// </summary>
    private static string? Repository(string? workingDirectory) =>
        workingDirectory?.TrimEnd('\\', '/').Split('\\', '/') is [.., var leaf] && leaf.Length > 0
            ? leaf
            : null;

    private static DateTimeOffset Timestamp(JsonElement record) =>
        DateTimeOffset.TryParse(Text(record, "timestamp"), out var timestamp)
            ? timestamp.ToUniversalTime()
            : DateTimeOffset.MinValue;
}
