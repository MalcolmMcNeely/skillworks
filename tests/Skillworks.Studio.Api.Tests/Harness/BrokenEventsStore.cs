using System.Net;

namespace Skillworks.Studio.Api.Tests.Harness;

// Stands in for a store that is down or failing, which a running Loki cannot be made to be.
public sealed class BrokenEventsStore : HttpMessageHandler
{
    private readonly Func<HttpResponseMessage> _answer;

    private BrokenEventsStore(Func<HttpResponseMessage> answer) => _answer = answer;

    public static BrokenEventsStore Down() => new(() => throw new HttpRequestException("connection refused"));

    public static BrokenEventsStore Failing(HttpStatusCode status) => new(() => new HttpResponseMessage(status));

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken) =>
        Task.FromResult(_answer());
}
