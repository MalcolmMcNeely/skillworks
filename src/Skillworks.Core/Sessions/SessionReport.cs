using System.Runtime.CompilerServices;
using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;
using Skillworks.Core.Sessions.Measures;
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

        var read = await sessions.ListAsync(span, filter, order, cancellationToken);
        var fellShort = new List<MeasureLanding>();

        // Every row is the events store's answer, so a trace store that fell short leaves them standing.
        if (read.Unreachable is null)
        {
            yield return new SessionsPage(read.Rows);

            // Behind the rows, so a reader has the table in hand before a single number reaches it.
            await foreach (var landing in read.Measures.WithCancellation(cancellationToken))
            {
                if (landing.Unreachable is null)
                {
                    yield return new SessionMeasure(landing.Measure, landing.Values);
                }
                else
                {
                    fellShort.Add(landing);
                }
            }
        }

        var period = await read.Period;

        yield return new GapEnd(Shown(
            gaps.InTotals(period, period.Unreachable is null ? [] : span.NewestFirst()),
            // Only where rows stand, as a Measure with no row to sit on leaves no column of dashes to explain.
            Missed(read.Rows.Count > 0 ? fellShort : []),
            gaps.InDepths(read.Traced)));
    }

    // They land in no order of their own, so the sentence would name them differently run to run.
    private Gap Missed(IEnumerable<MeasureLanding> fellShort)
    {
        MeasureLanding[] named = [.. fellShort.OrderBy(landing => landing.Measure)];

        return gaps.InMeasures(
            named.Select(landing => landing.Unreachable).FirstOrDefault(),
            [.. named.Select(landing => MeasureHeading.Of(landing.Measure))]);
    }

    // The bigger loss is named first: no rows at all, then a table nobody narrowed, then columns of dashes.
    // A table nobody narrowed says nothing about itself, so its sentence never gives way to one about
    // dashes a reader can already see.
    private static Gap Shown(Gap events, Gap measures, Gap depths)
    {
        if (events.Kind == GapKind.Unreachable)
        {
            return events;
        }

        if (depths.Kind != GapKind.Complete)
        {
            return measures.Kind == GapKind.Complete ? depths : Gap.Beside(depths, measures);
        }

        return measures.Kind == GapKind.Complete ? events : measures;
    }
}
