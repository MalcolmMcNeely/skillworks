using Skillworks.Core.EventsStore;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Gaps;

public sealed class GapReport(TelemetrySwitch telemetry)
{
    public Gap InTotals(EventTotals period, IReadOnlyList<DateOnly> unread) =>
        Gap.Of(period.Unreachable, unread, (long)period.Total, Emitting());

    // The switch calls unreadable settings not emitting: safe for writing, but a lie on a screen.
    private bool? Emitting()
    {
        var state = telemetry.State();

        return state.Readable ? state.Emitting : null;
    }
}
