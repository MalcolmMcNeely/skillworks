using System.Globalization;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.EventsStore;

public sealed class EventsStoreReader(IHttpClientFactory clients, IOptions<LokiOptions> options, TimeProvider clock)
{
    public const string ClientName = "loki";

    // A real query over a short window: a readiness route would pass a store that refuses queries.
    private static readonly TimeSpan Probe = TimeSpan.FromMinutes(1);

    private const string AnyStream = "{service_name=~\".+\"}";

    public Task<EventReading> ReadAsync(
        string eventName,
        DateTimeOffset from,
        DateTimeOffset until,
        CancellationToken cancellationToken) =>
        QueryAsync($"{AnyStream} |= \"claude_code.{eventName}\"", from, until, options.Value.MaxEvents, cancellationToken);

    public async Task<string?> UnreachableAsync(CancellationToken cancellationToken)
    {
        var now = clock.GetUtcNow();

        return (await QueryAsync(AnyStream, now - Probe, now, 1, cancellationToken)).Unreachable;
    }

    private async Task<EventReading> QueryAsync(
        string query,
        DateTimeOffset from,
        DateTimeOffset until,
        int limit,
        CancellationToken cancellationToken)
    {
        var loki = options.Value;
        var address = loki.ResolvedAddress();
        var client = clients.CreateClient(ClientName);

        // Newest first, so a period too big for one read keeps the part a reader is asking about.
        var route =
            $"loki/api/v1/query_range?query={Uri.EscapeDataString(query)}" +
            $"&start={Nanoseconds(from)}&end={Nanoseconds(until)}&limit={limit}&direction=backward";

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
                return EventReading.Failed($"{address} answered {(int)response.StatusCode}");
            }

            await using var body = await response.Content.ReadAsStreamAsync(cancellationToken);
            using var document = await JsonDocument.ParseAsync(body, cancellationToken: cancellationToken);

            var read = Read(document.RootElement);

            // A full answer cannot be told from a capped one, and calling a cut period whole is the worse mistake.
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

    private static IReadOnlyList<TelemetryEvent> Read(JsonElement root)
    {
        if (!root.TryGetProperty("data", out var data) ||
            !data.TryGetProperty("result", out var streams) ||
            streams.ValueKind != JsonValueKind.Array)
        {
            return [];
        }

        var events = new List<TelemetryEvent>();

        foreach (var stream in streams.EnumerateArray())
        {
            if (!stream.TryGetProperty("values", out var entries) || entries.ValueKind != JsonValueKind.Array)
            {
                continue;
            }

            // Loki answers a record's attributes as its stream's labels, not beside the entry.
            var labels = Labels(stream);

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

    private static Dictionary<string, string> Labels(JsonElement stream)
    {
        var labels = new Dictionary<string, string>(StringComparer.Ordinal);

        if (stream.TryGetProperty("stream", out var names) && names.ValueKind == JsonValueKind.Object)
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
