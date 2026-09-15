using Skillworks.Core.EventsStore;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Gaps;

public sealed class GapReport(TelemetrySwitch telemetry)
{
    public Gap InTotals(EventTotals period) =>
        Gap.Of(period.Unreachable, (long)period.Total, cappedAt: null, Emitting());

    // The whole period says whether anything fired, so a narrowed empty list is not quiet; only the read is ever cut.
    public Gap InList(EventReading listed, EventTotals period) =>
        Gap.Of(
            listed.Unreachable ?? period.Unreachable,
            (long)period.Total,
            listed.Truncated ? listed.Events.Count : null,
            Emitting());

    public Gap InRead(EventReading around) =>
        Gap.Of(around.Unreachable, around.Events.Count, cappedAt: null, Emitting());

    // The switch calls unreadable settings not emitting: safe for writing, but a lie on a screen.
    private bool? Emitting()
    {
        var state = telemetry.State();

        return state.Readable ? state.Emitting : null;
    }
}
