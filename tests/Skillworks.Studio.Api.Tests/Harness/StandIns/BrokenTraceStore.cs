using System.Net;

namespace Skillworks.Studio.Api.Tests.Harness.StandIns;

// Stands in for a store that is down, failing or still starting, which a running Tempo cannot be made to be.
public sealed class BrokenTraceStore(Func<HttpResponseMessage> broken) : DelegatingHandler(new HttpClientHandler())
{
    public static BrokenTraceStore Down() => new(() => throw new HttpRequestException("connection refused"));

    public static BrokenTraceStore Failing(HttpStatusCode status) => new(() => new HttpResponseMessage(status));

    // Tempo refuses reads with a 503 until it has read back everything it was already sent.
    public static BrokenTraceStore StartingUp() => Failing(HttpStatusCode.ServiceUnavailable);

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken) =>
        Task.FromResult(broken());
}
