using System.Globalization;
using System.Text.Encodings.Web;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.Shared.Stores.EventsStore;

public sealed class EventsStoreReader(IHttpClientFactory clients, IOptions<LokiOptions> options, TimeProvider clock)
{
    public const string ClientName = "loki";

    // A real query over a short window: a readiness route would pass a store that refuses queries.
    private static readonly TimeSpan Probe = TimeSpan.FromMinutes(1);

    // A JSON string is a LogQL string, and relaxed escaping never writes the surrogate pairs LogQL rejects.
    private static readonly JsonSerializerOptions LogQlString = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };

    private const string AnyStream = "{service_name=~\".+\"}";

    private static readonly TimeSpan Hour = TimeSpan.FromHours(1);

    // Under Loki's own cap, so the store never refuses a page.
    private const int Page = 1000;

    // One person's run in one repository ends long before this, so the read is bounded rather than endless.
    private const int MostLines = 50_000;

    // One cut for every query, so no figure puts an event on another day; Loki counts nothing hour by hour cut finer.
    private static readonly TimeSpan Cut = TimeSpan.FromMilliseconds(1);

    // An event carries the instant it happened only as text, so the line's own timestamp is unwrapped instead.
    private const string AsMoment = "| label_format at=`{{ __timestamp__ | unixEpochMillis }}` | unwrap at";

    public Task<EventTotals> CountAsync(
        EventQuery query,
        IReadOnlyList<string> by,
        CancellationToken cancellationToken) =>
        TotalAsync(
            query,
            (from, until) => Instant($"{SumBy(by)} (count_over_time({Selected(query)} [{Range(from, until)}]))", until),
            Enumerable.Sum,
            cancellationToken);

    // The total is a moment, as milliseconds since the epoch, and not a count.
    public Task<EventTotals> EarliestAsync(
        EventQuery query,
        IReadOnlyList<string> by,
        CancellationToken cancellationToken) =>
        OverTimeAsync(query, "min_over_time", by, Enumerable.Min, cancellationToken);

    public Task<EventTotals> LatestAsync(
        EventQuery query,
        IReadOnlyList<string> by,
        CancellationToken cancellationToken) =>
        OverTimeAsync(query, "max_over_time", by, Enumerable.Max, cancellationToken);

    private Task<EventTotals> OverTimeAsync(
        EventQuery query,
        string over,
        IReadOnlyList<string> by,
        Func<IEnumerable<decimal>, decimal> join,
        CancellationToken cancellationToken) =>
        TotalAsync(
            query,
            (from, until) => Instant(
                $"{over}({Selected(query)} {AsMoment} [{Range(from, until)}]){GroupedBy(by)}",
                until),
            join,
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
            Enumerable.Sum,
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
            Enumerable.Sum,
            cancellationToken);

    // The store caps both the days one query may span and the entries it may answer with.
    public async Task<EventLines> LinesAsync(EventQuery query, CancellationToken cancellationToken)
    {
        var lines = new List<EventLine>();
        var seen = new HashSet<string>(StringComparer.Ordinal);

        foreach (var (start, until) in Windows(query))
        {
            var from = start;

            while (from < until && lines.Count < MostLines)
            {
                var read = await AskAsync(
                    $"loki/api/v1/query_range?query={Uri.EscapeDataString(Selected(query))}" +
                    $"&start={Nanoseconds(from)}&end={Nanoseconds(until)}&limit={Page}&direction=forward",
                    root => EventLines.Of(Entries(root)),
                    EventLines.Failed,
                    cancellationToken);

                if (read.Unreachable is not null)
                {
                    return read;
                }

                var fresh = read.Lines.Where(line => seen.Add(line.Key)).ToList();

                lines.AddRange(fresh);

                // A page that fills up and adds nothing new would ask for the same instant for ever.
                if (read.Lines.Count < Page || fresh.Count == 0)
                {
                    break;
                }

                from = read.Lines.Max(line => line.At);
            }
        }

        // Loki answers stream by stream, and each event of a run is a stream of its own.
        return EventLines.Of([.. lines.OrderBy(line => line.At)]);
    }

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
        Func<IEnumerable<decimal>, decimal> join,
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

        return EventTotals.Of(EventTotal.Joined(groups, join));
    }

    // A range leaves out its start and takes in its end, so ending a cut early takes From in and Until out.
    private static string Instant(string logql, DateTimeOffset until) =>
        $"loki/api/v1/query?query={Uri.EscapeDataString(logql)}&time={Nanoseconds(until - Cut)}";

    private static string SumBy(IReadOnlyList<string> by) => $"sum{GroupedBy(by)}";

    private static string GroupedBy(IReadOnlyList<string> by) =>
        by.Count == 0 ? "" : $" by ({string.Join(", ", by.Select(EventAttributes.LabelOf))})";

    private static string Range(DateTimeOffset from, DateTimeOffset until) => Range(until - from);

    private static string Range(TimeSpan length) => $"{(long)length.TotalMilliseconds}ms";

    private static string Selected(EventQuery query)
    {
        var logql = $"{AnyStream} |= \"claude_code.{query.EventName}\"";

        if (query.Session is { } session)
        {
            logql += $" | {EventAttributes.LabelOf(EventAttributes.Session)}={Quoted(session)}";
        }

        if (query.Skill is { } skill)
        {
            logql += $" | {EventAttributes.LabelOf(EventAttributes.Skill)}={Quoted(skill)}";
        }

        if (query.QuerySource is { } source)
        {
            logql += $" | {EventAttributes.LabelOf(EventAttributes.QuerySource)}={Quoted(source)}";
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

        // One per request, as a long period is asked for a window at a time and one Patience over them all would cut it short.
        var patience = Patience(loki.TimeoutSeconds);

        using var spent = new CancellationTokenSource(patience, clock);
        using var within = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, spent.Token);

        try
        {
            using var response = await client.SendAsync(request, within.Token);

            if (!response.IsSuccessStatusCode)
            {
                return failed($"{address} answered {(int)response.StatusCode}");
            }

            await using var body = await response.Content.ReadAsStreamAsync(within.Token);
            using var document = await JsonDocument.ParseAsync(body, cancellationToken: within.Token);

            return read(document.RootElement);
        }
        catch (Exception failure) when (Outside(failure, cancellationToken))
        {
            // A Patience that ran out says so, or a reader is told only that something somewhere was cancelled.
            return failed(spent.IsCancellationRequested
                ? $"{address} did not answer inside the {patience.TotalSeconds:0} seconds Studio waits"
                : $"{address} could not be read: {failure.Message}");
        }
    }

    // At least a second, as a Patience of none would be spent before the request went out.
    private static TimeSpan Patience(int seconds) => TimeSpan.FromSeconds(Math.Max(1, seconds));

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

    // Loki hands back every attribute of an event as a label on its stream, so one entry is one event.
    private static IReadOnlyList<EventLine> Entries(JsonElement root)
    {
        var lines = new List<EventLine>();

        foreach (var stream in Results(root))
        {
            if (!stream.TryGetProperty("values", out var values) || values.ValueKind != JsonValueKind.Array)
            {
                continue;
            }

            var labels = Labels(stream, "stream");

            lines.AddRange(values.EnumerateArray().Select(Moment).OfType<DateTimeOffset>().Select(at => new EventLine(labels, at)));
        }

        return lines;
    }

    private static DateTimeOffset? Moment(JsonElement entry) =>
        entry.ValueKind == JsonValueKind.Array &&
        entry.GetArrayLength() >= 1 &&
        entry[0].ValueKind == JsonValueKind.String &&
        long.TryParse(entry[0].GetString(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var nanoseconds)
            ? DateTimeOffset.FromUnixTimeMilliseconds(nanoseconds / 1_000_000)
            : null;

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

    private static Dictionary<string, string> Labels(JsonElement sample, string property = "metric")
    {
        var labels = new Dictionary<string, string>(StringComparer.Ordinal);

        if (sample.TryGetProperty(property, out var names) && names.ValueKind == JsonValueKind.Object)
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
