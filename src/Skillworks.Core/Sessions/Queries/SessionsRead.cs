using Skillworks.Core.Sessions.Measures;
using Skillworks.Core.Shared.Stores.EventsStore;
using Skillworks.Core.Shared.Stores.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed record SessionsRead(
    // The gate's own shortfall, and only it leaves no rows to stand.
    string? Unreachable,
    IReadOnlyList<SessionRow> Rows,
    IAsyncEnumerable<MeasureLanding> Measures,
    EventTotals Period,
    TracedSessions Traced);
