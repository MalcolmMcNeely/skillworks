using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net;
using Skillworks.Core.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

// A running container cannot be made to be down, failing, still starting or silent.
public sealed class BrokenTraceStore(Func<CancellationToken, Task<HttpResponseMessage>> broken)
    : DelegatingHandler(new HttpClientHandler())
{
    private readonly ConcurrentQueue<Uri> _asked = new();

    private readonly TaskCompletionSource<string> _firstAsked = new(TaskCreationOptions.RunContinuationsAsynchronously);

    public static BrokenTraceStore Down() => Answering(() => throw new HttpRequestException("connection refused"));

    public static BrokenTraceStore Failing(HttpStatusCode status) => Answering(() => new HttpResponseMessage(status));

    public static BrokenTraceStore Refusing(HttpStatusCode status, string reason) =>
        Answering(() => new HttpResponseMessage(status) { Content = new StringContent(reason) });

    // The Trace store refuses reads with a 503 until it has read back everything it was already sent.
    public static BrokenTraceStore StartingUp() => Failing(HttpStatusCode.ServiceUnavailable);

    public static BrokenTraceStore Stalling() => new(Silent);

    public IReadOnlyList<string> Asked => [.. _asked.Select(route => route.PathAndQuery)];

    // Set the moment the store is first asked, so a test can wait on that rather than on a clock.
    public Task<string> FirstAsked => _firstAsked.Task;

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var route = request.RequestUri ?? throw new InvalidOperationException("Studio asked the store for no route.");

        _asked.Enqueue(route);
        _firstAsked.TrySetResult(route.PathAndQuery);

        return broken(cancellationToken);
    }

    private static BrokenTraceStore Answering(Func<HttpResponseMessage> answer) => new(_ => Task.FromResult(answer()));

    private static async Task<HttpResponseMessage> Silent(CancellationToken cancellationToken)
    {
        await Never.Answers(cancellationToken);

        throw new UnreachableException();
    }
}
