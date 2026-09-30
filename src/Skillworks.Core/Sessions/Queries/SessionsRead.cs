using Skillworks.Core.Sessions.DepthColumn;
using Skillworks.Core.Sessions.Measures;

namespace Skillworks.Core.Sessions.Queries;

public sealed record SessionsRead(
    // The gate's own shortfall, and only it leaves no rows to stand.
    string? Unreachable,
    IReadOnlyList<SessionRow> Rows,
    IAsyncEnumerable<MeasureLanding> Measures,
    // Lands null where no row stands, as the trace store is then never asked.
    Task<DepthLanding?> Depths,
    // Every line of activity read, so an empty list tells a quiet month from a narrowed one.
    long LinesRead,
    // At most one of the two, as a read either stopped at a Latest or ran out of lines at the end of its 30 days or its reach.
    DateTimeOffset? OldestLatestUtc,
    DateTimeOffset? QuietSinceUtc)
{
    public static SessionsRead Failed(string unreachable, long linesRead) =>
        new(unreachable, [], AsyncEnumerable.Empty<MeasureLanding>(), Unread, linesRead, null, null);

    public static SessionsRead Empty(long linesRead, DateTimeOffset? quietSinceUtc) =>
        new(null, [], AsyncEnumerable.Empty<MeasureLanding>(), Unread, linesRead, null, quietSinceUtc);

    private static Task<DepthLanding?> Unread => Task.FromResult<DepthLanding?>(null);
}
