using System.Net;

namespace Skillworks.Core.Tests.Shared.Harness.StandIns;

// Stands in for a Collector that holds a door until a test lets it answer, which a running Collector cannot be made to do.
public sealed class HeldCollector : HttpMessageHandler
{
    public const string EventsDoor = "/v1/logs";

    public const string SpansDoor = "/v1/traces";

    private readonly Dictionary<string, Held> _doors = new(StringComparer.Ordinal)
    {
        [EventsDoor] = new Held(),
        [SpansDoor] = new Held(),
    };

    // A test waits on this before it moves the Clock, so no test moves it on a wait instead.
    public Task Knocked(string door) => _doors[door].Knocked.Task;

    public void LetGo(string door) => _doors[door].LetGo.TrySetResult();

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var held = _doors[request.RequestUri!.AbsolutePath];

        held.Knocked.TrySetResult();

        // Awaiting the winner rethrows what a real send given up on throws, which a completed WhenAny would swallow.
        await await Task.WhenAny(held.LetGo.Task, Never.Answers(cancellationToken));

        return new HttpResponseMessage(HttpStatusCode.OK);
    }

    private sealed record Held
    {
        public TaskCompletionSource Knocked { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public TaskCompletionSource LetGo { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
    }
}