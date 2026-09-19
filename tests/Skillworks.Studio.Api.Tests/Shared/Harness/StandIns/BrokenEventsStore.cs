using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Web;

namespace Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

// Stands in for a store that is down, failing or stops part way, which a running Loki cannot be made to be.
public sealed class BrokenEventsStore : DelegatingHandler
{
    private readonly Func<Uri, bool> _breaks;
    private readonly Func<BrokenEventsStore, CancellationToken, Task<HttpResponseMessage>> _broken;
    private readonly ConcurrentQueue<Uri> _asked = new();
    private readonly TaskCompletionSource<TimeSpan> _heldFor = new(TaskCreationOptions.RunContinuationsAsynchronously);

    private BrokenEventsStore(
        Func<Uri, bool> breaks,
        Func<BrokenEventsStore, CancellationToken, Task<HttpResponseMessage>> broken)
        : base(new HttpClientHandler())
    {
        _breaks = breaks;
        _broken = broken;
    }

    public static BrokenEventsStore Down() => new(Before(DateOnly.MaxValue), Refused);

    public static BrokenEventsStore Failing(HttpStatusCode status) =>
        new(Before(DateOnly.MaxValue), (_, _) => Task.FromResult(new HttpResponseMessage(status)));

    public static BrokenEventsStore DownBefore(DateOnly oldestAnswered) => new(Before(oldestAnswered), Refused);

    public static BrokenEventsStore StallingBefore(DateOnly oldestAnswered) =>
        new(Before(oldestAnswered), Hold);

    // Each read names the events it counts, so a test can hold one back and leave the rest answering.
    public static BrokenEventsStore StallingOn(Func<string, bool> read) => new(route => read(QueryOf(route)), Hold);

    // Refused rather than held, so a test that reads to the end of the answer waits on nothing.
    public static BrokenEventsStore DownOn(Func<string, bool> read) => new(route => read(QueryOf(route)), Refused);

    public IReadOnlyList<string> Asked => [.. _asked.Select(route => route.PathAndQuery)];

    public IReadOnlyList<DateOnly> DaysAsked => [.. _asked.Select(DayOf).OfType<DateOnly>()];

    public Task<TimeSpan> HeldFor => _heldFor.Task;

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var route = request.RequestUri ?? throw new InvalidOperationException("Studio asked the store for no route.");

        _asked.Enqueue(route);

        return _breaks(route) ? _broken(this, cancellationToken) : base.SendAsync(request, cancellationToken);
    }

    // Answered days come from the test Loki, so the days on or after this one hold real figures.
    private static Func<Uri, bool> Before(DateOnly oldestAnswered) => route => !(DayOf(route) >= oldestAnswered);

    private static string QueryOf(Uri route) => HttpUtility.ParseQueryString(route.Query)["query"] ?? "";

    private static Task<HttpResponseMessage> Refused(BrokenEventsStore store, CancellationToken cancellationToken) =>
        throw new HttpRequestException("connection refused");

    private static Task<HttpResponseMessage> Hold(BrokenEventsStore store, CancellationToken cancellationToken) =>
        store.HoldAsync(cancellationToken);

    private async Task<HttpResponseMessage> HoldAsync(CancellationToken cancellationToken)
    {
        var held = Stopwatch.StartNew();

        try
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
        }
        catch (OperationCanceledException)
        {
            _heldFor.TrySetResult(held.Elapsed);
            throw;
        }

        throw new UnreachableException();
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
