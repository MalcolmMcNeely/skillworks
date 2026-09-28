namespace Skillworks.Core.Tests.Shared.Harness.StandIns;

// Stands in for an events store whose container is down, so the refusal arrives at once and no Clock decides it.
public sealed class RefusingEventsStore : HttpMessageHandler
{
    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken) =>
        throw new HttpRequestException("No connection could be made because the target machine actively refused it.");
}
