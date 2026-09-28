using System.Collections.Concurrent;
using System.Globalization;
using System.Net;
using System.Web;
using Skillworks.Core.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

// Stands in for a store that is down, failing, stops part way or answers late, which a running Loki cannot be made to be.
public sealed class BrokenEventsStore : DelegatingHandler
{
    private readonly Func<Uri, bool> _breaks;
    private readonly Func<BrokenEventsStore, HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> _broken;
    private readonly ConcurrentQueue<Uri> _asked = new();
    private readonly TaskCompletionSource<string> _holding = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource<string> _held = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource _letGo = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly Lock _gate = new();
    private readonly List<string> _answered = [];
    private readonly List<(Func<string, bool> Read, TaskCompletionSource Reached)> _awaited = [];

    private BrokenEventsStore(
        Func<Uri, bool> breaks,
        Func<BrokenEventsStore, HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> broken)
        : base(TestLoki.Handler())
    {
        _breaks = breaks;
        _broken = broken;
    }

    public static BrokenEventsStore Down() => new(Before(DateOnly.MaxValue), Refused);

    public static BrokenEventsStore Failing(HttpStatusCode status) =>
        new(Before(DateOnly.MaxValue), (_, _, _) => Task.FromResult(new HttpResponseMessage(status)));

    // Loki gives its reason as plain text, as it does for a query over its series limit.
    public static BrokenEventsStore Refusing(HttpStatusCode status, string reason) =>
        new(
            Before(DateOnly.MaxValue),
            (_, _, _) => Task.FromResult(new HttpResponseMessage(status) { Content = new StringContent(reason) }));

    public static BrokenEventsStore DownBefore(DateOnly oldestAnswered) => new(Before(oldestAnswered), Refused);

    public static BrokenEventsStore StallingBefore(DateOnly oldestAnswered) =>
        new(Before(oldestAnswered), Hold);

    // Each read names the events it counts, so a test can hold one back and leave the rest answering.
    public static BrokenEventsStore StallingOn(Func<string, bool> read) => new(route => read(QueryOf(route)), Hold);

    // Refused rather than held, so a test that reads to the end of the answer waits on nothing.
    public static BrokenEventsStore DownOn(Func<string, bool> read) => new(route => read(QueryOf(route)), Refused);

    public IReadOnlyList<string> Asked => [.. _asked.Select(route => route.PathAndQuery)];

    public IReadOnlyList<string> Queries => [.. _asked.Select(QueryOf)];

    public IReadOnlyList<DateOnly> DaysAsked => [.. _asked.Select(DayOf).OfType<DateOnly>()];

    public Task<string> HoldingRead => _holding.Task;

    public Task<string> HeldRead => _held.Task;

    public Task Answered(Func<string, bool> read)
    {
        lock (_gate)
        {
            if (_answered.Any(read))
            {
                return Task.CompletedTask;
            }

            var reached = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);

            _awaited.Add((read, reached));

            return reached.Task;
        }
    }

    public void LetGo() => _letGo.TrySetResult();

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var route = request.RequestUri ?? throw new InvalidOperationException("Studio asked the store for no route.");

        _asked.Enqueue(route);

        return _breaks(route) ? _broken(this, request, cancellationToken) : AnswerAsync(request, cancellationToken);
    }

    // Answered days come from the test Loki, so the days on or after this one hold real figures.
    private static Func<Uri, bool> Before(DateOnly oldestAnswered) => route => !(DayOf(route) >= oldestAnswered);

    private static string QueryOf(Uri route) => HttpUtility.ParseQueryString(route.Query)["query"] ?? "";

    private static Task<HttpResponseMessage> Refused(
        BrokenEventsStore store,
        HttpRequestMessage request,
        CancellationToken cancellationToken) =>
        throw new HttpRequestException("connection refused");

    private static Task<HttpResponseMessage> Hold(
        BrokenEventsStore store,
        HttpRequestMessage request,
        CancellationToken cancellationToken) =>
        store.HoldAsync(request, cancellationToken);

    private async Task<HttpResponseMessage> HoldAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var query = QueryOf(request.RequestUri!);

        _holding.TrySetResult(query);

        try
        {
            // Awaiting the winner rethrows what a real send given up on throws, which a finished WhenAny would swallow.
            await await Task.WhenAny(_letGo.Task, Never.Answers(cancellationToken));
        }
        catch (OperationCanceledException)
        {
            _held.TrySetResult(query);
            throw;
        }

        return await AnswerAsync(request, cancellationToken);
    }

    private async Task<HttpResponseMessage> AnswerAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var answer = await base.SendAsync(request, cancellationToken);
        var query = QueryOf(request.RequestUri!);

        lock (_gate)
        {
            _answered.Add(query);

            foreach (var wait in _awaited.Where(wait => wait.Read(query)))
            {
                wait.Reached.TrySetResult();
            }
        }

        return answer;
    }

    // Studio ends an instant query's day just before midnight, and starts an hour-by-hour query at its day's first step.
    private static DateOnly? DayOf(Uri route)
    {
        var query = HttpUtility.ParseQueryString(route.Query);

        return long.TryParse(query["time"] ?? query["start"], CultureInfo.InvariantCulture, out var nanoseconds)
            ? DateOnly.FromDateTime(DateTimeOffset.FromUnixTimeMilliseconds(nanoseconds / 1_000_000).UtcDateTime)
            : null;
    }
}
