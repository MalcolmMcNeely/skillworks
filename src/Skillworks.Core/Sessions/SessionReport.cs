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

        var (rows, period) = await sessions.ListAsync(span, order, cancellationToken);

        if (period.Unreachable is null)
        {
            yield return new SessionsPage(rows);
        }

        yield return new GapEnd(gaps.InTotals(period, period.Unreachable is null ? [] : span.NewestFirst()));
    }
}
