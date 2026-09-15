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

    private static readonly TimeSpan Hour = TimeSpan.FromHours(1);

    // One cut for every query, so no figure puts an event on another day; Loki counts nothing hour by hour cut finer.
    private static readonly TimeSpan Cut = TimeSpan.FromMilliseconds(1);

    public Task<EventTotals> CountAsync(
        EventQuery query,
        IReadOnlyList<string> by,
        CancellationToken cancellationToken) =>
        TotalAsync(
            query,
            (from, until) => Instant($"{SumBy(by)} (count_over_time({Selected(query)} [{Range(from, until)}]))", until),
            cancellationToken);

    // Loki fails the whole query on one value that is not a number, so such an event adds nothing.
    public Task<EventTotals> SumAsync(
        EventQuery query,
        string attribute,
        IReadOnlyList<string> by,
        CancellationToken cancellationToken) =>
        TotalAsync(
            query,
            (from, until) => Instant(
                $"{SumBy(by)} (sum_over_time({Selected(query)} | unwrap {EventAttributes.LabelOf(attribute)} | __error__=\"\" [{Range(from, until)}]))",
                until),
            cancellationToken);

    // A range query, as 24 instant queries cost 24 times as much and an hour label multiplies the series a store caps.
    public Task<EventTotals> CountByHourAsync(
        EventQuery query,
        IReadOnlyList<string> by,
        CancellationToken cancellationToken) =>
        TotalAsync(
            query,
            (from, until) =>
                // Each step takes in its end, so the offset takes an hour's first instant in and its end out.
                $"loki/api/v1/query_range?query={Uri.EscapeDataString($"{SumBy(by)} (count_over_time({Selected(query)} [1h] offset {Range(Cut)}))")}" +
                $"&start={Nanoseconds(from + Hour)}&end={Nanoseconds(until)}&step={(long)Hour.TotalSeconds}",
            cancellationToken);

    public Task<string?> UnreachableAsync(CancellationToken cancellationToken)
    {
        var now = clock.GetUtcNow();

        var route =
            $"loki/api/v1/query_range?query={Uri.EscapeDataString(AnyStream)}" +
            $"&start={Nanoseconds(now - Probe)}&end={Nanoseconds(now)}&limit=1";

        return AskAsync<string?>(route, _ => null, reason => reason, cancellationToken);
    }

    private async Task<EventTotals> TotalAsync(
        EventQuery query,
        Func<DateTimeOffset, DateTimeOffset, string> routeOf,
        CancellationToken cancellationToken)
    {
        var groups = new List<EventTotal>();

        // One after another, so a long span asks no more of the store at once than a short one.
        foreach (var (from, until) in Windows(query))
        {
            var totalled = await AskAsync(
                routeOf(from, until),
                root => EventTotals.Of(Totals(root)),
                EventTotals.Failed,
                cancellationToken);

            if (totalled.Unreachable is not null)
            {
                return totalled;
            }

            groups.AddRange(totalled.Groups);
        }

        return EventTotals.Of(EventTotal.Joined(groups));
    }

    // A range leaves out its start and takes in its end, so ending a cut early takes From in and Until out.
    private static string Instant(string logql, DateTimeOffset until) =>
        $"loki/api/v1/query?query={Uri.EscapeDataString(logql)}&time={Nanoseconds(until - Cut)}";

    private static string SumBy(IReadOnlyList<string> by) =>
        by.Count == 0 ? "sum" : $"sum by ({string.Join(", ", by.Select(EventAttributes.LabelOf))})";

    private static string Range(DateTimeOffset from, DateTimeOffset until) => Range(until - from);

    private static string Range(TimeSpan length) => $"{(long)length.TotalMilliseconds}ms";

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

    // Abutting, so an event on a cut is counted once.
    private IEnumerable<(DateTimeOffset From, DateTimeOffset Until)> Windows(EventQuery query)
    {
        // At least a day, as a window of none would never move back.
        var longest = TimeSpan.FromDays(Math.Max(1, options.Value.MaxQueryDays));
        var until = query.Until;

        while (until > query.From)
        {
            var from = until - query.From > longest ? until - longest : query.From;

            yield return (from, until);

            until = from;
        }
    }

    private static string Quoted(string value) => JsonSerializer.Serialize(value, LogQlString);

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

    private static IReadOnlyList<EventTotal> Totals(JsonElement root)
    {
        var totals = new List<EventTotal>();

        foreach (var sample in Results(root))
        {
            if (sample.TryGetProperty("value", out var value) && Point(value) is (_, var total))
            {
                totals.Add(new EventTotal(Labels(sample), total));
            }

            if (sample.TryGetProperty("values", out var values) && values.ValueKind == JsonValueKind.Array)
            {
                foreach (var (at, stepTotal) in values.EnumerateArray().Select(Point).OfType<(double, decimal)>())
                {
                    // Each step ends the hour it counts.
                    var startOfHour = DateTimeOffset.FromUnixTimeMilliseconds((long)Math.Round(at * 1000)) - Hour;

                    totals.Add(new EventTotal(Labels(sample), stepTotal, startOfHour));
                }
            }
        }

        return totals;
    }

    private static (double At, decimal Total)? Point(JsonElement point) =>
        point.ValueKind == JsonValueKind.Array &&
        point.GetArrayLength() >= 2 &&
        point[0].ValueKind == JsonValueKind.Number &&
        point[1].ValueKind == JsonValueKind.String &&
        double.TryParse(point[1].GetString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var total) &&
        double.IsFinite(total)
            // Loki adds in floating point, and a decimal from a double keeps 15 digits, so 0.1 and 0.2 make 0.3.
            ? (point[0].GetDouble(), (decimal)total)
            : null;

    private static IEnumerable<JsonElement> Results(JsonElement root) =>
        root.TryGetProperty("data", out var data) &&
        data.TryGetProperty("result", out var results) &&
        results.ValueKind == JsonValueKind.Array
            ? results.EnumerateArray()
            : [];

    private static Dictionary<string, string> Labels(JsonElement sample)
    {
        var labels = new Dictionary<string, string>(StringComparer.Ordinal);

        if (sample.TryGetProperty("metric", out var names) && names.ValueKind == JsonValueKind.Object)
        {
            foreach (var label in names.EnumerateObject().Where(label => label.Value.ValueKind == JsonValueKind.String))
            {
                labels[label.Name] = label.Value.GetString()!;
            }
        }

        return labels;
    }

    private static long Nanoseconds(DateTimeOffset moment) => moment.ToUnixTimeMilliseconds() * 1_000_000;
}
