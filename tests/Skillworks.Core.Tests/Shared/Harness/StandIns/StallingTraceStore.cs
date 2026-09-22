namespace Skillworks.Core.Tests.Shared.Harness.StandIns;

// A running container cannot be made to hold every request back.
public sealed class StallingTraceStore() : DelegatingHandler(new HttpClientHandler())
{
    private readonly TaskCompletionSource _asked = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource _letGo = new(TaskCreationOptions.RunContinuationsAsynchronously);

    // A test waits for this before it moves the Clock, so no test moves it on a wait instead.
    public Task Asked => _asked.Task;

    public void LetGo() => _letGo.TrySetResult();

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        _asked.TrySetResult();

        // Cancellation is left to the send below, which throws what a real read given up on throws.
        await Task.WhenAny(_letGo.Task, Never.Answers(cancellationToken));

        return await base.SendAsync(request, cancellationToken);
    }
}
