using System.Text.Json;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Telemetry;

/// <summary>What one transcript line held.</summary>
/// <param name="Activations">Empty for the great majority of lines, which record something else.</param>
/// <param name="Turn">
/// The request this line belongs to, or null when the line records no request. Several lines of one
/// request each report it in full, so the caller keys on the request id and takes it once.
/// </param>
/// <param name="Problem">
/// Why the line could not be read at all. Non-null means the line was stepped over, so the ingest
/// has something to count and report rather than a silent gap.
/// </param>
internal readonly record struct LineReading(
    IReadOnlyList<Activation> Activations,
    Turn? Turn,
    string? Problem);

/// <summary>
/// Turns one transcript line into the activations and the spend it records. Internal on purpose:
/// the tests drive the API, not this.
/// </summary>
/// <remarks>
/// An activation is read from a Skill tool use, because CONTEXT.md defines one as "one occasion on
/// which a skill fired" and that block is the firing. The record's own <c>attributionSkill</c> is a
/// different fact: the skill that was already active when the request was made. It repeats on every
/// turn a skill is in force, so counting it would count turns, not firings. It is what Attribution
/// reads, and it is why the turn that chose a skill is charged to no skill.
/// </remarks>
internal static class TranscriptParser
{
    public static LineReading Read(string line, RepositoryNames repositories)
    {
        if (string.IsNullOrWhiteSpace(line))
        {
            return new LineReading([], null, null);
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
            return new LineReading([], null, failure.Message);
        }

        using (document)
        {
            var record = document.RootElement;

            if (record.ValueKind != JsonValueKind.Object ||
                Text(record, "type") != "assistant" ||
                !record.TryGetProperty("message", out var message))
            {
                return new LineReading([], null, null);
            }

            return new LineReading(
                Activations(record, message, repositories),
                Turn(record, message, repositories),
                null);
        }
    }

    private static IReadOnlyList<Activation> Activations(
        JsonElement record,
        JsonElement message,
        RepositoryNames repositories)
    {
        if (!message.TryGetProperty("content", out var content) || content.ValueKind != JsonValueKind.Array)
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
                Arguments = input.GetRawText(),
                Repository = repositories.Of(Text(record, "cwd")),
                GitBranch = Text(record, "gitBranch"),
                TimestampUtc = Timestamp(record),
                Model = Text(message, "model"),
                Effort = Text(record, "effort"),
            });
        }

        return activations is null ? [] : activations;
    }

    private static Turn? Turn(JsonElement record, JsonElement message, RepositoryNames repositories)
    {
        if (!message.TryGetProperty("usage", out var usage) ||
            usage.ValueKind != JsonValueKind.Object ||
            Text(message, "model") is not { } model)
        {
            return null;
        }

        // The message id is the same request under another name, and stands in for the rare record
        // written without one. Without either there is no way to tell a repeat from a new request,
        // and counting it would be worse than dropping it.
        if ((Text(record, "requestId") ?? Text(message, "id")) is not { } requestId)
        {
            return null;
        }

        var cacheWritten = Count(usage, "cache_creation_input_tokens");
        var written5m = cacheWritten;
        var written1h = 0L;

        // Absent on older records. The cache then lasted the API's default five minutes, so putting
        // the lot in that bucket prices it as it was actually billed.
        if (usage.TryGetProperty("cache_creation", out var split) && split.ValueKind == JsonValueKind.Object)
        {
            written5m = Count(split, "ephemeral_5m_input_tokens");
            written1h = Count(split, "ephemeral_1h_input_tokens");
        }

        var thinking = usage.TryGetProperty("output_tokens_details", out var details) &&
                       details.ValueKind == JsonValueKind.Object
            ? Count(details, "thinking_tokens")
            : 0;

        return new Turn
        {
            RequestId = requestId,
            SessionId = Text(record, "sessionId") ?? "",
            SkillName = Text(record, "attributionSkill"),
            Repository = repositories.Of(Text(record, "cwd")),
            GitBranch = Text(record, "gitBranch"),
            TimestampUtc = Timestamp(record),
            Model = model,
            Effort = Text(record, "effort"),
            InputTokens = Count(usage, "input_tokens"),
            OutputTokens = Count(usage, "output_tokens"),
            ThinkingTokens = thinking,
            CacheReadTokens = Count(usage, "cache_read_input_tokens"),
            CacheWrite5mTokens = written5m,
            CacheWrite1hTokens = written1h,
        };
    }

    private static string? Text(JsonElement element, string property) =>
        element.TryGetProperty(property, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    private static long Count(JsonElement element, string property) =>
        element.TryGetProperty(property, out var value) &&
        value.ValueKind == JsonValueKind.Number &&
        value.TryGetInt64(out var count)
            ? count
            : 0;

    private static DateTimeOffset Timestamp(JsonElement record) =>
        DateTimeOffset.TryParse(Text(record, "timestamp"), out var timestamp)
            ? timestamp.ToUniversalTime()
            : DateTimeOffset.MinValue;
}
