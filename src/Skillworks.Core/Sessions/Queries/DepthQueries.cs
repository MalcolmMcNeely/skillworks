using Skillworks.Core.Filters;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed class DepthQueries(TraceStoreReader traces)
{
    // Asked only when a reader asks for a Depth, so a table nobody narrowed never waits on a second store.
    public Task<TracedSessions> OfPeriodAsync(DaySpan span, Filter filter, CancellationToken cancellationToken) =>
        filter.NarrowsByDepth
            ? traces.OfPeriodAsync(span.FromUtc, span.UntilUtc, cancellationToken)
            : Task.FromResult(TracedSessions.Unasked);
}
