using System.Globalization;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.Provenance;

public sealed class SkillEvents(IHttpClientFactory clients, IOptions<LokiOptions> options)
{
    public const string ClientName = "loki";

    // A line filter, not a label: Loki derives label names, so a rename would silently match nothing.
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

    // Caller cancellation must propagate, or a closed browser tab would be reported as an outage.
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

    // Loki puts a record's attributes third in an entry and flattens their dots to underscores.
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
