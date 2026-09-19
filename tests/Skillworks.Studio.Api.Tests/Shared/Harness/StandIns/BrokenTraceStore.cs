using System.Collections.Concurrent;
using System.Net;

namespace Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

// Stands in for a store that is down, failing or still starting, which a running Tempo cannot be made to be.
public sealed class BrokenTraceStore(Func<HttpResponseMessage> broken) : DelegatingHandler(new HttpClientHandler())
{
    private readonly ConcurrentQueue<Uri> _asked = new();

    public static BrokenTraceStore Down() => new(() => throw new HttpRequestException("connection refused"));

    public static BrokenTraceStore Failing(HttpStatusCode status) => new(() => new HttpResponseMessage(status));

    // Tempo refuses reads with a 503 until it has read back everything it was already sent.
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
