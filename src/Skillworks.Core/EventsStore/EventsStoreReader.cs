using System.Globalization;
using System.Text.Encodings.Web;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.EventsStore;

public sealed class EventsStoreReader(IHttpClientFactory clients, IOptions<LokiOptions> options, TimeProvider clock)
{
    public const string ClientName = "loki";

    // A real query over a short window: a readiness route would pass a store that refuses queries.
    private static readonly TimeSpan Probe = TimeSpan.FromMinutes(1);

    // A JSON string is a LogQL string, and relaxed escaping never writes the surrogate pairs LogQL rejects.
    private static readonly JsonSerializerOptions LogQlString = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };

    private const string AnyStream = "{service_name=~\".+\"}";

    public Task<EventReading> ReadAsync(
        string eventName,
        DateTimeOffset from,
        DateTimeOffset until,
        CancellationToken cancellationToken) =>
        QueryAsync(Selected(new EventQuery(eventName, from, until)), from, until, options.Value.MaxEvents, cancellationToken);

    // Counted by Loki, so no read cap cuts a busy organisation's total short.
    public Task<EventCounts> CountAsync(
        EventQuery query,
        IReadOnlyList<string> by,
        CancellationToken cancellationToken)
    {
        if (query.Until <= query.From)
        {
            return Task.FromResult(EventCounts.Of([]));
        }

        var range = (long)(query.Until - query.From).TotalMilliseconds;
        var sum = by.Count == 0 ? "sum" : $"sum by ({string.Join(", ", by.Select(EventAttributes.LabelOf))})";
        var logql = $"{sum} (count_over_time({Selected(query)} [{range}ms]))";

        // A range leaves out its start and takes in its end, so ending a nanosecond early takes From in and Until out.
        var route =
            $"loki/api/v1/query?query={Uri.EscapeDataString(logql)}" +
            $"&time={Nanoseconds(query.Until) - 1}";

        return AskAsync(route, root => EventCounts.Of(Counts(root)), EventCounts.Failed, cancellationToken);
    }

    public async Task<string?> UnreachableAsync(CancellationToken cancellationToken)
    {
        var now = clock.GetUtcNow();

        return (await QueryAsync(AnyStream, now - Probe, now, 1, cancellationToken)).Unreachable;
    }

    private static string Selected(EventQuery query)
    {
        var logql = $"{AnyStream} |= \"claude_code.{query.EventName}\"";

        if (query.Skill is { } skill)
        {
            logql += $" | {EventAttributes.LabelOf(EventAttributes.Skill)}={Quoted(skill)}";
        }

        if (query.Repository is { } repository)
        {
            var (owner, name) = EventAttributes.OwnerAndName(repository);
            var ownerLabel = EventAttributes.LabelOf(EventAttributes.Owner);
            var nameLabel = EventAttributes.LabelOf(EventAttributes.RepositoryName);

            // An empty match would take in every event that has no Repository, which a Repository filter leaves out.
            logql +=
                $" | {ownerLabel}!=\"\" | {nameLabel}!=\"\"" +
                $" | {ownerLabel}={Quoted(owner)} | {nameLabel}={Quoted(name)}";
        }

        return logql;
    }

    private static string Quoted(string value) => JsonSerializer.Serialize(value, LogQlString);

    private Task<EventReading> QueryAsync(
        string query,
        DateTimeOffset from,
        DateTimeOffset until,
        int limit,
        CancellationToken cancellationToken)
    {
        // Newest first, so a period too big for one read keeps the part a reader is asking about.
        var route =
            $"loki/api/v1/query_range?query={Uri.EscapeDataString(query)}" +
            $"&start={Nanoseconds(from)}&end={Nanoseconds(until)}&limit={limit}&direction=backward";

        return AskAsync(
            route,
            root =>
            {
                var read = Read(root);

                // A full answer cannot be told from a capped one, and calling a cut period whole is the worse mistake.
                return EventReading.Of(read, read.Count >= limit);
            },
            EventReading.Failed,
            cancellationToken);
    }

    private async Task<T> AskAsync<T>(
        string route,
        Func<JsonElement, T> read,
        Func<string, T> failed,
        CancellationToken cancellationToken)
    {
        var loki = options.Value;
        var address = loki.ResolvedAddress();
        var client = clients.CreateClient(ClientName);

        using var request = new HttpRequestMessage(HttpMethod.Get, route);

        if (!string.IsNullOrWhiteSpace(loki.Tenant))
        {
            request.Headers.Add("X-Scope-OrgID", loki.Tenant.Trim());
        }

        try
        {
            using var response = await client.SendAsync(request, cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                return failed($"{address} answered {(int)response.StatusCode}");
            }

            await using var body = await response.Content.ReadAsStreamAsync(cancellationToken);
            using var document = await JsonDocument.ParseAsync(body, cancellationToken: cancellationToken);

            return read(document.RootElement);
        }
        catch (Exception failure) when (Outside(failure, cancellationToken))
        {
            return failed($"{address} could not be read: {failure.Message}");
        }
    }

    // Caller cancellation must propagate, or a closed browser tab would be reported as an outage.
    private static bool Outside(Exception failure, CancellationToken cancellationToken) =>
        failure is HttpRequestException or JsonException ||
        (failure is TaskCanceledException && !cancellationToken.IsCancellationRequested);

    private static IReadOnlyList<TelemetryEvent> Read(JsonElement root)
    {
        var events = new List<TelemetryEvent>();

        foreach (var stream in Results(root))
        {
            if (!stream.TryGetProperty("values", out var entries) || entries.ValueKind != JsonValueKind.Array)
            {
                continue;
            }

            // Loki answers a record's attributes as its stream's labels, not beside the entry.
            var labels = Labels(stream, "stream");

            foreach (var entry in entries.EnumerateArray())
            {
                if (At(entry) is { } at)
                {
                    events.Add(new TelemetryEvent(at, labels));
                }
            }
        }

        return events;
    }

    private static IReadOnlyList<EventCount> Counts(JsonElement root)
    {
        var counts = new List<EventCount>();

        foreach (var sample in Results(root))
        {
            if (sample.TryGetProperty("value", out var value) &&
                value.ValueKind == JsonValueKind.Array &&
                value.GetArrayLength() >= 2 &&
                value[1].ValueKind == JsonValueKind.String &&
                decimal.TryParse(value[1].GetString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var count))
            {
                counts.Add(new EventCount(Labels(sample, "metric"), (long)count));
            }
        }

        return counts;
    }

    private static IEnumerable<JsonElement> Results(JsonElement root) =>
        root.TryGetProperty("data", out var data) &&
        data.TryGetProperty("result", out var results) &&
        results.ValueKind == JsonValueKind.Array
            ? results.EnumerateArray()
            : [];

    private static Dictionary<string, string> Labels(JsonElement result, string property)
    {
        var labels = new Dictionary<string, string>(StringComparer.Ordinal);

        if (result.TryGetProperty(property, out var names) && names.ValueKind == JsonValueKind.Object)
        {
            foreach (var label in names.EnumerateObject().Where(label => label.Value.ValueKind == JsonValueKind.String))
            {
                labels[label.Name] = label.Value.GetString()!;
            }
        }

        return labels;
    }

    private static DateTimeOffset? At(JsonElement entry) =>
        entry.ValueKind == JsonValueKind.Array &&
        entry.GetArrayLength() >= 1 &&
        entry[0].ValueKind == JsonValueKind.String &&
        long.TryParse(entry[0].GetString(), CultureInfo.InvariantCulture, out var nanoseconds)
            ? DateTimeOffset.FromUnixTimeMilliseconds(nanoseconds / 1_000_000)
            : null;

    private static long Nanoseconds(DateTimeOffset moment) => moment.ToUnixTimeMilliseconds() * 1_000_000;
}
