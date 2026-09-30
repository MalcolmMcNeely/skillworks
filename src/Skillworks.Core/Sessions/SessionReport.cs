using System.Runtime.CompilerServices;
using Skillworks.Core.Sessions.DepthColumn;
using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Shared.Gaps;
using Skillworks.Core.Sessions.Lookup;
using Skillworks.Core.Sessions.Measures;
using Skillworks.Core.Sessions.Queries;

namespace Skillworks.Core.Sessions;

public sealed class SessionReport(SessionQueries sessions, GapReport gaps, TimeProvider clock, LookupReach reach)
{
    private static readonly Gap NothingMissing = new(GapKind.Complete, null);

    // One page of rows, not a day at a time: a Session cut at midnight would read as two halves.
    // A span on the Filter is left unread, as no span narrows this list and an old link must still open it.
    public async IAsyncEnumerable<ArrivingLine> AnswerAsync(
        Filter filter,
        DateTimeOffset? asOfUtc,
        DateTimeOffset? latestBeforeUtc,
        string? lookup,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var now = clock.GetUtcNow();
        var id = string.IsNullOrWhiteSpace(lookup) ? null : lookup.Trim();

        // Never later than now, as an instant still to come would read events the list has not yet reached.
        // A Lookup names one run, so it reads as of now and takes no paging.
        var asOf = id is null && asOfUtc is { } handed && handed < now ? handed : now;

        yield return new SessionsHead(asOf);

        var read = id is null
            ? await sessions.ListAsync(asOf, latestBeforeUtc, filter, cancellationToken)
            : await sessions.LookupAsync(id, reach.StartBefore(asOf), asOf, cancellationToken);
        var fellShort = new List<MeasureLanding>();
        DepthLanding? depths = null;

        if (read.Unreachable is null)
        {
            yield return new SessionsPage(read.Rows);

            // Behind the rows, so a reader has the table in hand before a single number reaches it.
            // Each is sent the moment it lands, so a Depth ready first never waits on a Measure still out.
            await using var measures = read.Measures.GetAsyncEnumerator(cancellationToken);

            var measuring = measures.MoveNextAsync().AsTask();
            var depthing = read.Depths;
            List<Task> pending = [measuring, depthing];

            while (pending.Count > 0)
            {
                var landed = await Task.WhenAny(pending);

                pending.Remove(landed);

                if (landed == depthing)
                {
                    depths = await depthing;

                    if (depths is not null)
                    {
                        yield return new SessionDepths(depths.Depths);
                    }

                    continue;
                }

                if (!await measuring)
                {
                    continue;
                }

                var landing = measures.Current;

                if (landing.Unreachable is null)
                {
                    yield return new SessionMeasure(landing.Measure, landing.Values);
                }
                else
                {
                    fellShort.Add(landing);
                }

                measuring = measures.MoveNextAsync().AsTask();
                pending.Add(measuring);
            }
        }

        var gap = Shown(
            id is null ? gaps.InRows(read.Unreachable, read.LinesRead) : gaps.InLookup(read.Unreachable),
            // Only where rows stand, as a Measure with no row to sit on leaves no column of dashes to explain.
            Missed(read.Rows.Count > 0 ? fellShort : []),
            // Only where a row was left a dash, as a store that fell short but named every row lost nothing.
            depths is not null && depths.Depths.Count < read.Rows.Count ? gaps.InDepths(depths.Traced) : NothingMissing);

        yield return new SessionsEnd(gap, read.OldestLatestUtc, read.QuietSinceUtc);
    }

    // They land in no order of their own, so the sentence would name them differently run to run.
    private Gap Missed(IEnumerable<MeasureLanding> fellShort)
    {
        MeasureLanding[] named = [.. fellShort.OrderBy(landing => landing.Measure)];

        return gaps.InMeasures(
            named.Select(landing => landing.Unreachable).FirstOrDefault(),
            [.. named.Select(landing => MeasureHeading.Of(landing.Measure))]);
    }

    // No rows at all is the bigger loss, and beside it a column of dashes goes unsaid.
    // Two columns of dashes are both named, as each comes from a store of its own.
    private static Gap Shown(Gap events, Gap measures, Gap depths)
    {
        if (events.Kind == GapKind.Unreachable)
        {
            return events;
        }

        return (measures.Kind, depths.Kind) switch
        {
            (GapKind.Complete, GapKind.Complete) => events,
            (_, GapKind.Complete) => measures,
            (GapKind.Complete, _) => depths,
            _ => Gap.Beside(measures, depths),
        };
    }
}
