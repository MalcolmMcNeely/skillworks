using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Web;

namespace Skillworks.Studio.Api.Tests.Harness.StandIns;

// Stands in for a store that is down, failing or stops part way, which a running Loki cannot be made to be.
public sealed class BrokenEventsStore : DelegatingHandler
{
    private readonly DateOnly _oldestAnswered;
    private readonly Func<BrokenEventsStore, CancellationToken, Task<HttpResponseMessage>> _broken;
    private readonly ConcurrentQueue<Uri> _asked = new();
    private readonly TaskCompletionSource<TimeSpan> _heldFor = new(TaskCreationOptions.RunContinuationsAsynchronously);

    // Answered days come from the test Loki, so the days before the break hold real figures.
    private BrokenEventsStore(
        DateOnly oldestAnswered,
        Func<BrokenEventsStore, CancellationToken, Task<HttpResponseMessage>> broken)
        : base(new HttpClientHandler())
    {
        _oldestAnswered = oldestAnswered;
        _broken = broken;
    }

    public static BrokenEventsStore Down() => new(DateOnly.MaxValue, Refused);

    public static BrokenEventsStore Failing(HttpStatusCode status) =>
        new(DateOnly.MaxValue, (_, _) => Task.FromResult(new HttpResponseMessage(status)));

    public static BrokenEventsStore DownBefore(string oldestAnswered) => new(Day(oldestAnswered), Refused);

    public static BrokenEventsStore StallingBefore(string oldestAnswered) =>
        new(Day(oldestAnswered), (store, cancellationToken) => store.HoldAsync(cancellationToken));

    public IReadOnlyList<string> Asked => [.. _asked.Select(route => route.PathAndQuery)];

    public IReadOnlyList<DateOnly> DaysAsked => [.. _asked.Select(DayOf).OfType<DateOnly>()];

    public Task<TimeSpan> HeldFor => _heldFor.Task;

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var route = request.RequestUri ?? throw new InvalidOperationException("Studio asked the store for no route.");

        _asked.Enqueue(route);

        return DayOf(route) >= _oldestAnswered
            ? base.SendAsync(request, cancellationToken)
            : _broken(this, cancellationToken);
    }

    private static Task<HttpResponseMessage> Refused(BrokenEventsStore store, CancellationToken cancellationToken) =>
        throw new HttpRequestException("connection refused");

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

    private static DateOnly Day(string day) => DateOnly.Parse(day, CultureInfo.InvariantCulture);
}
