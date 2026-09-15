using System.Runtime.CompilerServices;
using Skillworks.Core.EventsStore;
using Skillworks.Core.Gaps;

namespace Skillworks.Core.Arriving;

public sealed class ArrivingDays(GapReport gaps)
{
    public async IAsyncEnumerable<ArrivingLine> AnswerAsync<TDay>(
        ArrivingLine head,
        IReadOnlyList<DateOnly> days,
        Func<DateOnly, CancellationToken, Task<(TDay Line, EventTotals Period)>> dayAsync,
        [EnumeratorCancellation] CancellationToken cancellationToken)
        where TDay : ArrivingLine
    {
        yield return head;

        var read = EventTotals.Of([]);
        var landed = 0;

        // No retry: the Gap names what failed, and the developer decides when to ask again.
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

        yield return new AnswerEnd(gaps.InTotals(read, [.. days.Skip(landed)]));
    }
}
