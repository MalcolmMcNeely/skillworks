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

        // Every row is the events store's answer, so a trace store that fell short leaves them standing.
        if (period.Unreachable is null)
        {
            yield return new SessionsPage(rows);
        }

        yield return new GapEnd(Shown(
            gaps.InTotals(period, period.Unreachable is null ? [] : span.NewestFirst()),
            gaps.InDepths(traced)));
    }

    // An events store that never answered emptied the table, so it is named ahead of a trace store.
    private static Gap Shown(Gap events, Gap depths) =>
        events.Kind == GapKind.Unreachable || depths.Kind == GapKind.Complete ? events : depths;
}
