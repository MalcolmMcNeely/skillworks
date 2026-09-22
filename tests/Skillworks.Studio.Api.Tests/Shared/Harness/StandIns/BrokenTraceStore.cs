using System.Collections.Concurrent;
using System.Net;

namespace Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

// A running container cannot be made to be down, failing or still starting.
public sealed class BrokenTraceStore(Func<HttpResponseMessage> broken) : DelegatingHandler(new HttpClientHandler())
{
    private readonly ConcurrentQueue<Uri> _asked = new();

    public static BrokenTraceStore Down() => new(() => throw new HttpRequestException("connection refused"));

    public static BrokenTraceStore Failing(HttpStatusCode status) => new(() => new HttpResponseMessage(status));

    // The Trace store refuses reads with a 503 until it has read back everything it was already sent.
    public static BrokenTraceStore StartingUp() => Failing(HttpStatusCode.ServiceUnavailable);

    public IReadOnlyList<string> Asked => [.. _asked.Select(route => route.PathAndQuery)];

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        _asked.Enqueue(request.RequestUri ?? throw new InvalidOperationException("Studio asked the store for no route."));

        return Task.FromResult(broken());
    }
}
