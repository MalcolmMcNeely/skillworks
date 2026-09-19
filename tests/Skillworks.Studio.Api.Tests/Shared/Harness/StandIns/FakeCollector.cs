using System.Net;

namespace Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

// Stands in for a Collector with a door shut, which a running Collector cannot be made to have.
public sealed class FakeCollector(Func<HttpResponseMessage> events, Func<HttpResponseMessage> spans) : HttpMessageHandler
{
    private const string EventsDoor = "/v1/logs";

    private const string SpansDoor = "/v1/traces";

    private readonly Dictionary<string, string> _taken = new(StringComparer.Ordinal);

    public static FakeCollector Open() => new(Took, Took);

    // A Collector started before its settings told it to take Spans serves one door and answers 404 on the other.
    public static FakeCollector SpansShut() => new(Took, Missing);

    public static FakeCollector EventsShut() => new(Missing, Took);

    public static FakeCollector Down() => new(Refused, Refused);

    public string? EventsPayload => _taken.GetValueOrDefault(EventsDoor);

    public string? SpansPayload => _taken.GetValueOrDefault(SpansDoor);

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var door = request.RequestUri?.AbsolutePath ?? "";

        _taken[door] = request.Content is null ? "" : await request.Content.ReadAsStringAsync(cancellationToken);

        return door switch
        {
            EventsDoor => events(),
            SpansDoor => spans(),
            _ => Missing(),
        };
    }

    private static HttpResponseMessage Took() => new(HttpStatusCode.OK);

    private static HttpResponseMessage Missing() => new(HttpStatusCode.NotFound);

    private static HttpResponseMessage Refused() => throw new HttpRequestException("connection refused");
}
