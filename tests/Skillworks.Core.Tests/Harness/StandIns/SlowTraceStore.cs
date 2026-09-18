namespace Skillworks.Core.Tests.Harness.StandIns;

// Stands in front of a real store to hold every request back, which a running Tempo cannot be made to do.
public sealed class SlowTraceStore(TimeSpan held) : DelegatingHandler(new HttpClientHandler())
{
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        await Task.Delay(held, cancellationToken);

        return await base.SendAsync(request, cancellationToken);
    }
}
