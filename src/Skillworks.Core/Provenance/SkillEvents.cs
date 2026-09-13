using System.Globalization;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.Provenance;

/// <summary>
/// One skill_activated event. It is the only record of where a skill came from and what set it
/// off, because a transcript carries neither.
/// </summary>
/// <param name="Trigger">
/// Verbatim, as the store holds it: <c>claude-proactive</c> when the model chose the skill,
/// <c>user-slash</c> when a developer typed it. Reading those into words is the screen's job.
/// </param>
/// <param name="Source">Where the skill was loaded from: a settings folder, a plugin, and so on.</param>
/// <param name="Plugin">Null unless a plugin delivered it.</param>
/// <param name="Marketplace">Null unless a plugin delivered it.</param>
public sealed record SkillEvent(
    string Skill,
    DateTimeOffset At,
    string? Trigger,
    string? Source,
    string? Plugin,
    string? Marketplace);

/// <summary>
/// What one read of the events store came back with. A failure is carried rather than thrown:
/// missing provenance is something to say on a screen, not a reason to lose the rest of it.
/// </summary>
/// <param name="Unreachable">Why the store could not be read, or null when it answered.</param>
/// <param name="Truncated">
/// True when the period held more events than one read takes, so the oldest of them are not in
/// here. The newest are kept, because a screen is nearly always asking about recent work.
/// </param>
public sealed record EventReading(IReadOnlyList<SkillEvent> Events, string? Unreachable, bool Truncated = false)
{
    public static EventReading Of(IReadOnlyList<SkillEvent> events, bool truncated) =>
        new(events, null, truncated);

    public static EventReading Failed(string reason) => new([], reason);
}

/// <summary>
/// Reads skill_activated events out of Loki, over its range endpoint. There is no C# client for
/// Loki and none is needed: one GET, and one document to walk.
/// </summary>
public sealed class SkillEvents(IHttpClientFactory clients, IOptions<LokiOptions> options)
{
    /// <summary>The named client, so the address and the timeout are configured in one place.</summary>
    public const string ClientName = "loki";

    /// <summary>
    /// Every stream, and the body Claude Code writes for this event. Matched on the line rather
    /// than on a label: the attributes arrive as structured metadata under names Loki derives, and
    /// a selector built on a derived name would answer a rename with silence.
    /// </summary>
    private const string Query = "{service_name=~\".+\"} |= \"claude_code.skill_activated\"";

    public async Task<EventReading> ReadAsync(
        DateTimeOffset from,
        DateTimeOffset until,
        CancellationToken cancellationToken)
    {
        var address = options.Value.ResolvedAddress();
        var limit = options.Value.MaxEvents;
        var client = clients.CreateClient(ClientName);

        // Newest first, so a period too big for one read keeps the part a reader is asking about.
        var route =
            $"loki/api/v1/query_range?query={Uri.EscapeDataString(Query)}" +
            $"&start={Nanoseconds(from)}&end={Nanoseconds(until)}&limit={limit}&direction=backward";

        try
        {
            using var response = await client.GetAsync(route, cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                return EventReading.Failed($"{address} answered {(int)response.StatusCode}");
            }

            await using var body = await response.Content.ReadAsStreamAsync(cancellationToken);
            using var document = await JsonDocument.ParseAsync(body, cancellationToken: cancellationToken);

            var read = Read(document.RootElement);

            // A full answer is the one shape that cannot be told from a capped one, so it is taken
            // as capped. Reporting a period as whole when it was cut is the failure worth avoiding.
            return EventReading.Of(read, read.Count >= limit);
        }
        catch (Exception failure) when (Outside(failure, cancellationToken))
        {
            return EventReading.Failed($"{address} could not be read: {failure.Message}");
        }
    }

    /// <summary>
    /// A failure of the store rather than of Studio. A cancelled request is the caller giving up
    /// and has to go on being that, or a closed browser tab would be reported as an outage.
    /// </summary>
    private static bool Outside(Exception failure, CancellationToken cancellationToken) =>
        failure is HttpRequestException or JsonException ||
        (failure is TaskCanceledException && !cancellationToken.IsCancellationRequested);

    private static IReadOnlyList<SkillEvent> Read(JsonElement root)
    {
        if (!root.TryGetProperty("data", out var data) ||
            !data.TryGetProperty("result", out var streams) ||
            streams.ValueKind != JsonValueKind.Array)
        {
            return [];
        }

        var events = new List<SkillEvent>();

        foreach (var stream in streams.EnumerateArray())
        {
            if (!stream.TryGetProperty("values", out var entries) || entries.ValueKind != JsonValueKind.Array)
            {
                continue;
            }

            foreach (var entry in entries.EnumerateArray())
            {
                if (Entry(entry) is { } recorded)
                {
                    events.Add(recorded);
                }
            }
        }

        return events;
    }

    /// <summary>
    /// One entry: the moment, the line, and the attributes beside it. Loki carries a log record's
    /// attributes as the third part of an entry and flattens their dots to underscores. An entry
    /// without a skill name on it is some other event, and is not for this reader.
    /// </summary>
    private static SkillEvent? Entry(JsonElement entry)
    {
        if (entry.ValueKind != JsonValueKind.Array || entry.GetArrayLength() < 3)
        {
            return null;
        }

        var attributes = entry[2];

        if (attributes.ValueKind != JsonValueKind.Object ||
            Text(attributes, "skill_name") is not { } skill ||
            entry[0].ValueKind != JsonValueKind.String ||
            !long.TryParse(entry[0].GetString(), CultureInfo.InvariantCulture, out var nanoseconds))
        {
            return null;
        }

        return new SkillEvent(
            skill,
            DateTimeOffset.FromUnixTimeMilliseconds(nanoseconds / 1_000_000),
            Text(attributes, "invocation_trigger"),
            Text(attributes, "skill_source"),
            Text(attributes, "plugin_name"),
            Text(attributes, "marketplace_name"));
    }

    private static string? Text(JsonElement attributes, string name) =>
        attributes.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    private static long Nanoseconds(DateTimeOffset moment) => moment.ToUnixTimeMilliseconds() * 1_000_000;
}
