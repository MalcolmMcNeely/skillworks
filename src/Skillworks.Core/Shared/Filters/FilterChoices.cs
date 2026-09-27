using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Shared.Filters;

// Only the span narrows the choices, so picking a Repository never hides the others.
public sealed class FilterChoices(EventsStoreReader events, ArrivingDays arriving, Lookback lookback)
{
    private const string EventName = "skill_activated";

    public IAsyncEnumerable<ArrivingLine> AnswerAsync(Filter filter, CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);
        var days = span.NewestFirst();

        // A Gap would count Activations alone, so a period that only spent would read as quiet.
        return arriving.AnswerWithoutGapAsync(new FilterChoicesHead(span, days), days, DayAsync, cancellationToken);
    }

    private async Task<(FilterChoicesDay Line, EventTotals Period)> DayAsync(
        DateOnly day,
        CancellationToken cancellationToken)
    {
        var whole = DaySpan.Of(day);

        var activations = await events.CountAsync(
            new EventQuery(EventName, whole.FromUtc, whole.UntilUtc),
            [EventAttributes.Owner, EventAttributes.RepositoryName],
            cancellationToken);

        return (new FilterChoicesDay(day, Repositories(activations)), activations);
    }

    private static IReadOnlyList<string> Repositories(EventTotals activations) =>
    [
        .. activations.Groups
            .Select(count => count.Repository)
            .OfType<string>()
            .Distinct()
            .OrderBy(repository => repository, StringComparer.OrdinalIgnoreCase)
    ];
}
