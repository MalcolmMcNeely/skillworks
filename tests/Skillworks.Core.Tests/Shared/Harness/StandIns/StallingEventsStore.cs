using System.Diagnostics;

namespace Skillworks.Core.Tests.Shared.Harness.StandIns;

// Stands in for an events store that never answers, which a running Loki cannot be made to be.
public sealed class StallingEventsStore : HttpMessageHandler
{
    private readonly TaskCompletionSource _asked = new(TaskCreationOptions.RunContinuationsAsynchronously);

    // A test waits for this before it moves the Clock, so no test moves it on a wait instead.
    public Task Asked => _asked.Task;

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        _asked.TrySetResult();

        await Never.Answers(cancellationToken);

        throw new UnreachableException();
    }
}
