using Skillworks.Core.EventsStore;
using Skillworks.Core.Sessions.Measures;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed record SessionsRead(
    // The gate's own shortfall, and only it leaves no rows to stand.
    string? Unreachable,
    IReadOnlyList<SessionRow> Rows,
    IAsyncEnumerable<SessionMeasure> Measures,
    // A wait still, because the survey is out of the gate and must not hold the rows back.
    Task<EventTotals> Period,
    TracedSessions Traced);
