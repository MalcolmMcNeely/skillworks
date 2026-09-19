using System.Runtime.CompilerServices;
using Skillworks.Core.Shared.Gaps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Shared.Arriving;

public sealed class ArrivingDays(GapReport gaps)
{
    public IAsyncEnumerable<ArrivingLine> AnswerAsync<TDay>(
        ArrivingLine head,
        IReadOnlyList<DateOnly> days,
        Func<DateOnly, CancellationToken, Task<(TDay Line, EventTotals Period)>> dayAsync,
        CancellationToken cancellationToken)
        where TDay : ArrivingLine =>
        LinesAsync(head, days, dayAsync, (read, unread) => new GapEnd(gaps.InTotals(read, unread)), cancellationToken);

    public IAsyncEnumerable<ArrivingLine> AnswerWithoutGapAsync<TDay>(
        ArrivingLine head,
        IReadOnlyList<DateOnly> days,
        Func<DateOnly, CancellationToken, Task<(TDay Line, EventTotals Period)>> dayAsync,
        CancellationToken cancellationToken)
        where TDay : ArrivingLine =>
        LinesAsync(head, days, dayAsync, (_, _) => new PlainEnd(), cancellationToken);

    private async IAsyncEnumerable<ArrivingLine> LinesAsync<TDay>(
        ArrivingLine head,
        IReadOnlyList<DateOnly> days,
        Func<DateOnly, CancellationToken, Task<(TDay Line, EventTotals Period)>> dayAsync,
        Func<EventTotals, IReadOnlyList<DateOnly>, AnswerEnd> endOf,
        [EnumeratorCancellation] CancellationToken cancellationToken)
        where TDay : ArrivingLine
    {
        yield return head;

        var read = EventTotals.Of([]);
        var landed = 0;

        // No retry: the developer decides when to ask again.
        foreach (var day in days)
        {
            var (line, period) = await dayAsync(day, cancellationToken);

            read = read.Plus(period);

            if (period.Unreachable is not null)
            {
                break;
            }

            yield return line;
            landed++;
        }

        yield return endOf(read, [.. days.Skip(landed)]);
    }
}
