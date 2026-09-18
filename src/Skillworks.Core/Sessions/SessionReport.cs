using System.Runtime.CompilerServices;
using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;
using Skillworks.Core.Sessions.Queries;

namespace Skillworks.Core.Sessions;

public sealed class SessionReport(SessionQueries sessions, GapReport gaps, Lookback lookback)
{
    // One page of rows, not a day at a time: a Session cut at midnight would read as two halves.
    public async IAsyncEnumerable<ArrivingLine> AnswerAsync(
        Filter filter,
        SessionOrder order,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);

        yield return new SessionsHead(span, order.SortedOn, order.HighestFirst);

        var (rows, period, traced) = await sessions.ListAsync(span, filter, order, cancellationToken);

        // A Depth the trace store could not answer would narrow the table by guesswork, so it shows no rows at all.
        // Half an answer narrows it the same way, and a run the store left out would go missing without a word.
        if (period.Unreachable is null && traced.Unreachable is null && !traced.Shortened)
        {
            yield return new SessionsPage(rows);
        }

        yield return new GapEnd(Emptied(
            gaps.InTotals(period, period.Unreachable is null ? [] : span.NewestFirst()),
            gaps.InDepths(traced)));
    }

    // The store that emptied the table is the one to name, and an events store that never answered empties it hardest.
    private static Gap Emptied(Gap events, Gap depths) =>
        events.Kind == GapKind.Unreachable || depths.Kind == GapKind.Complete ? events : depths;
}
