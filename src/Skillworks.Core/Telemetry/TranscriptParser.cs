using System.Text.Json;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Telemetry;

/// <summary>What one transcript line held.</summary>
/// <param name="Activations">Empty for the great majority of lines, which record something else.</param>
/// <param name="Problem">
/// Why the line could not be read at all. Non-null means the line was stepped over, so the ingest
/// has something to count and report rather than a silent gap.
/// </param>
internal readonly record struct LineReading(IReadOnlyList<Activation> Activations, string? Problem);

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
    public static LineReading Read(string line, RepositoryNames repositories)
    {
        if (string.IsNullOrWhiteSpace(line))
        {
            return new LineReading([], null);
        }

        JsonDocument document;

        try
        {
            document = JsonDocument.Parse(line);
        }
        catch (JsonException failure)
        {
            // A line Studio cannot read is one line, never the other 1,470. Its own message names
            // the column it gave up at, which is what makes the fault worth reporting.
            return new LineReading([], failure.Message);
        }

        using (document)
        {
            return new LineReading(Activations(document.RootElement, repositories), null);
        }
    }

    private static IReadOnlyList<Activation> Activations(JsonElement record, RepositoryNames repositories)
    {
        if (record.ValueKind != JsonValueKind.Object ||
            Text(record, "type") != "assistant" ||
            !record.TryGetProperty("message", out var message) ||
            !message.TryGetProperty("content", out var content) ||
            content.ValueKind != JsonValueKind.Array)
        {
            return [];
        }

        // Left null until something is found: almost every line of 678 MB reaches here and holds
        // no skill at all.
        List<Activation>? activations = null;

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

            (activations ??= []).Add(new Activation
            {
                ToolUseId = toolUseId,
                SkillName = skill,
                SessionId = Text(record, "sessionId") ?? "",
                Repository = repositories.Of(Text(record, "cwd")),
                GitBranch = Text(record, "gitBranch"),
                TimestampUtc = Timestamp(record),
            });
        }

        return activations is null ? [] : activations;
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
