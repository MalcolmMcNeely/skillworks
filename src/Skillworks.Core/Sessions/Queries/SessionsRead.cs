using Skillworks.Core.Sessions.Measures;
using Skillworks.Core.Shared.Stores.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed record SessionsRead(
    // The gate's own shortfall, and only it leaves no rows to stand.
    string? Unreachable,
    IReadOnlyList<SessionRow> Rows,
    IAsyncEnumerable<MeasureLanding> Measures,
    // Every Prompt line read, before any Filter, so an empty list tells a quiet month from a narrowed one.
    long Prompts,
    // At most one of the two, as a read either stopped at a place or ran out of Prompts at the end of its 30 days.
    DateTimeOffset? NextBeforeUtc,
    DateTimeOffset? QuietSinceUtc,
    TracedSessions Traced)
{
    public static SessionsRead Failed(string unreachable, long prompts) =>
        new(unreachable, [], AsyncEnumerable.Empty<MeasureLanding>(), prompts, null, null, TracedSessions.Unasked);
}
