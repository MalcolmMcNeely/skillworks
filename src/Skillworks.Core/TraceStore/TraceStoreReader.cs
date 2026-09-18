using System.Globalization;
using System.Net;
using System.Text.Encodings.Web;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.TraceStore;

public sealed class TraceStoreReader(IHttpClientFactory clients, IOptions<TempoOptions> options, TimeProvider clock)
{
    public const string ClientName = "tempo";

    // A real search over a short window: a readiness route would pass a store that refuses TraceQL.
    private static readonly TimeSpan Probe = TimeSpan.FromMinutes(1);

    // A JSON string is a TraceQL string, and relaxed escaping never writes the surrogate pairs TraceQL rejects.
    private static readonly JsonSerializerOptions TraceQlString = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };

    private const string SessionAttribute = "session.id";

    private const int SpanIdBytes = 8;

    private const int TraceIdBytes = 16;

    public async Task<SessionSpans> OfSessionAsync(
        string session,
        DateTimeOffset from,
        DateTimeOffset until,
        CancellationToken cancellationToken)
    {
        // One budget over the whole read, because it makes a request per trace and each would take its own.
        using var spent = new CancellationTokenSource(Whole(options.Value.SessionTimeoutSeconds), clock);
        using var whole = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, spent.Token);

        var budget = new Budget(whole.Token, cancellationToken);
        var traces = new HashSet<string>(StringComparer.Ordinal);
        var most = Most(options.Value.MostTraces);
        var shortened = false;

        // A trace that straddles a cut comes back from both windows, so the ids gather into a set.
        foreach (var (start, end) in Windows(from, until))
        {
            var found = await AskAsync<IReadOnlyList<string>>(
                Search($"{{ span.{SessionAttribute} = {Quoted(session)} }}", start, end, most),
                TraceIds,
                [],
                budget);

            if (found.Unreachable is not null)
            {
                return SessionSpans.Failed(found.Unreachable);
            }

            shortened |= Filled(found.Value.Count, most);

            traces.UnionWith(found.Value);
        }

        var spans = new List<Span>();

        // A search names only the spans it matched, so the run itself is read back trace by trace.
        foreach (var trace in traces)
        {
            var read = await AskAsync<IReadOnlyList<Span>>(Trace(trace), Spans, [], budget);

            if (read.Unreachable is not null)
            {
                return SessionSpans.Failed(read.Unreachable);
            }

            spans.AddRange(read.Value);
        }

        return SessionSpans.Of([.. spans.OrderBy(span => span.Started)], shortened);
    }

    // The values of one attribute, not a search: a period holds far more traces than a search hands back.
    public async Task<TracedSessions> OfPeriodAsync(
        DateTimeOffset from,
        DateTimeOffset until,
        CancellationToken cancellationToken)
    {
        var sessions = new HashSet<string>(StringComparer.Ordinal);
        var most = Most(options.Value.MostSessions);
        var shortened = false;

        foreach (var (start, end) in Windows(from, until))
        {
            var found = await AskAsync<IReadOnlyList<string>>(
                Values(start, end, most),
                Sessions,
                [],
                Budget.PerRequest(cancellationToken));

            if (found.Unreachable is not null)
            {
                return TracedSessions.Failed(found.Unreachable);
            }

            shortened |= Filled(found.Value.Count, most);

            sessions.UnionWith(found.Value);
        }

        return TracedSessions.Of(sessions, shortened);
    }

    public async Task<TraceStoreAnswer> AnsweringAsync(CancellationToken cancellationToken)
    {
        var address = options.Value.ResolvedAddress();
        var now = clock.GetUtcNow();

        try
        {
            using var response = await SendAsync(
                Search($"{{ span.{SessionAttribute} != \"\" }}", now - Probe, now, 1),
                cancellationToken);

            return response.StatusCode switch
            {
                _ when response.IsSuccessStatusCode => TraceStoreAnswer.Answering(address),

                HttpStatusCode.ServiceUnavailable => TraceStoreAnswer.Starting(
                    $"{address} is still starting, so it is not answering reads yet."),

                var status => TraceStoreAnswer.Unreachable($"{address} answered {(int)status}"),
            };
        }
        catch (Exception failure) when (Outside(failure, cancellationToken))
        {
            return TraceStoreAnswer.Unreachable($"{address} could not be read: {failure.Message}");
        }
    }

    // The store cuts an answer to the limit it was asked for and never says it had more, so a full answer is a short one.
    private static bool Filled(int answered, int limit) => answered >= limit;

    // At least one, as a limit of none asks the store for a default of its own and would never be reached.
    private static int Most(int asked) => Math.Max(1, asked);

    // At least a second, as a budget of none would be spent before the first request went out.
    private static TimeSpan Whole(int seconds) => TimeSpan.FromSeconds(Math.Max(1, seconds));

    // Within a block a search keeps only the spans whose own times fall in the window, which a values read does not.
    private static string Search(string traceQl, DateTimeOffset from, DateTimeOffset until, int limit) =>
        $"api/search?q={Uri.EscapeDataString(traceQl)}&{Window(from, until)}&limit={limit}";

    private static string Values(DateTimeOffset from, DateTimeOffset until, int limit) =>
        $"api/v2/search/tag/span.{SessionAttribute}/values?{Window(from, until)}&limit={limit}";

    // The store picks its blocks by when the spans reached it, so a period ending before they arrived reads none.
    private static string Window(DateTimeOffset from, DateTimeOffset until) =>
        $"start={from.ToUnixTimeSeconds()}&end={SecondsRoundedUp(until)}";

    // A whole week is exactly as long as a store will answer for, so a spare second at the end would be refused.
    private static long SecondsRoundedUp(DateTimeOffset until) => (until.ToUnixTimeMilliseconds() + 999) / 1000;

    private IEnumerable<(DateTimeOffset From, DateTimeOffset Until)> Windows(DateTimeOffset from, DateTimeOffset until)
    {
        // At least a day, as a window of none would never move back.
        var longest = TimeSpan.FromDays(Math.Max(1, options.Value.MaxSearchDays));

        while (until > from)
        {
            var start = until - from > longest ? until - longest : from;

            yield return (start, until);

            until = start;
        }
    }

    // Tempo writes a trace id without its leading zeroes, and takes one back the same way.
    private static string Trace(string traceId) => $"api/v2/traces/{Uri.EscapeDataString(traceId)}";

    private static string Quoted(string value) => JsonSerializer.Serialize(value, TraceQlString);

    private async Task<Answer<T>> AskAsync<T>(string route, Func<JsonElement, T> read, T none, Budget budget)
    {
        var address = options.Value.ResolvedAddress();

        try
        {
            using var response = await SendAsync(route, budget.Within);

            if (!response.IsSuccessStatusCode)
            {
                return new Answer<T>(none, $"{address} answered {(int)response.StatusCode}");
            }

            await using var body = await response.Content.ReadAsStreamAsync(budget.Within);
            using var document = await JsonDocument.ParseAsync(body, cancellationToken: budget.Within);

            return new Answer<T>(read(document.RootElement), null);
        }
        catch (Exception failure) when (Outside(failure, budget.Caller))
        {
            return new Answer<T>(none, $"{address} could not be read: {failure.Message}");
        }
    }

    private async Task<HttpResponseMessage> SendAsync(string route, CancellationToken cancellationToken)
    {
        var tempo = options.Value;
        var client = clients.CreateClient(ClientName);

        using var request = new HttpRequestMessage(HttpMethod.Get, route);

        if (!string.IsNullOrWhiteSpace(tempo.Tenant))
        {
            request.Headers.Add("X-Scope-OrgID", tempo.Tenant.Trim());
        }

        return await client.SendAsync(request, cancellationToken);
    }

    // Caller cancellation must propagate, or a closed browser tab would be reported as an outage.
    private static bool Outside(Exception failure, CancellationToken cancellationToken) =>
        failure is HttpRequestException or JsonException ||
        (failure is TaskCanceledException && !cancellationToken.IsCancellationRequested);

    private static IReadOnlyList<string> Sessions(JsonElement root) =>
    [
        .. Items(root, "tagValues")
            .Select(held => Text(held, "value"))
            .OfType<string>()
    ];

    private static IReadOnlyList<string> TraceIds(JsonElement root) =>
    [
        .. Items(root, "traces")
            .Select(trace => Text(trace, "traceID"))
            .OfType<string>()
    ];

    private static IReadOnlyList<Span> Spans(JsonElement root)
    {
        if (!root.TryGetProperty("trace", out var trace))
        {
            return [];
        }

        return
        [
            .. from resource in Items(trace, "resourceSpans")
               from scope in Items(resource, "scopeSpans")
               from span in Items(scope, "spans")
               select Read(span) into read
               where read is not null
               select read
        ];
    }

    private static Span? Read(JsonElement span) =>
        Identifier(span, "traceId") is { } traceId &&
        Identifier(span, "spanId") is { } spanId &&
        Text(span, "name") is { } name &&
        Moment(span, "startTimeUnixNano") is { } started &&
        Moment(span, "endTimeUnixNano") is { } ended
            ? new Span(traceId, spanId, Identifier(span, "parentSpanId"), name, started, ended, Attributes(span))
            : null;

    // Tempo writes a span's ids as base64, where OTLP's own JSON asks for hex, and a hex id is itself
    // valid base64, so only a decode of the length an id really is may be believed.
    private static string? Identifier(JsonElement span, string field)
    {
        if (Text(span, field) is not { Length: > 0 } written)
        {
            return null;
        }

        var bytes = new byte[written.Length];

        return Convert.TryFromBase64String(written, bytes, out var length) && length is SpanIdBytes or TraceIdBytes
            ? Convert.ToHexStringLower(bytes, 0, length)
            : written;
    }

    private static DateTimeOffset? Moment(JsonElement span, string field) =>
        long.TryParse(Text(span, field), NumberStyles.Integer, CultureInfo.InvariantCulture, out var nanoseconds)
            ? DateTimeOffset.FromUnixTimeMilliseconds(nanoseconds / 1_000_000)
            : null;

    private static IReadOnlyDictionary<string, string> Attributes(JsonElement span)
    {
        var attributes = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var attribute in Items(span, "attributes"))
        {
            if (Text(attribute, "key") is { } key &&
                attribute.TryGetProperty("value", out var value) &&
                Scalar(value) is { } scalar)
            {
                attributes[key] = scalar;
            }
        }

        return attributes;
    }

    // Reading only the string would drop the figures and flags a span carries beside its words.
    private static string? Scalar(JsonElement value) => value
        .EnumerateObject()
        .Select(field => field.Value.ValueKind switch
        {
            JsonValueKind.String => field.Value.GetString(),
            JsonValueKind.Number or JsonValueKind.True or JsonValueKind.False => field.Value.ToString(),
            _ => null,
        })
        .OfType<string>()
        .FirstOrDefault();

    private static string? Text(JsonElement held, string field) =>
        held.TryGetProperty(field, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static IEnumerable<JsonElement> Items(JsonElement held, string field) =>
        held.TryGetProperty(field, out var items) && items.ValueKind == JsonValueKind.Array ? items.EnumerateArray() : [];

    private sealed record Answer<T>(T Value, string? Unreachable);

    // Two tokens, because a budget that ran out is the store falling short and a reader who left is not.
    private readonly record struct Budget(CancellationToken Within, CancellationToken Caller)
    {
        // A read with no budget of its own, where each request is bounded by the client's timeout alone.
        public static Budget PerRequest(CancellationToken cancellationToken) =>
            new(cancellationToken, cancellationToken);
    }
}
