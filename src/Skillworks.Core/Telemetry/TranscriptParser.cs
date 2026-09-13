using System.Text.Json;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Telemetry;

/// <summary>
/// Turns one transcript line into the activations it records. Internal on purpose: the tests drive
/// the API, not this.
/// </summary>
/// <remarks>
/// An activation is read from a Skill tool use, because CONTEXT.md defines one as "one occasion on
/// which a skill fired" and that block is the firing. The record's own <c>attributionSkill</c> is a
/// different fact: the skill that was already active when the request was made. It repeats on every
/// turn a skill is in force, so counting it would count turns, not firings. It is what Attribution
/// will read when cost lands.
/// </remarks>
internal static class TranscriptParser
{
    public static List<Activation> Activations(string line, RepositoryNames repositories)
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
                Repository = repositories.Of(Text(record, "cwd")),
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

    private static DateTimeOffset Timestamp(JsonElement record) =>
        DateTimeOffset.TryParse(Text(record, "timestamp"), out var timestamp)
            ? timestamp.ToUniversalTime()
            : DateTimeOffset.MinValue;
}
