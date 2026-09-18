using Skillworks.Core.EventsStore;
using Skillworks.Core.Telemetry;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Gaps;

public sealed class GapReport(TelemetrySwitch telemetry)
{
    public Gap InTotals(EventTotals period, IReadOnlyList<DateOnly> unread) =>
        Gap.Of(period.Unreachable, unread, (long)period.Total, Emitting());

    // Withheld words beat a switch that is off here: the events did arrive, and the two ask for different fixes.
    public Gap InLines(EventLines read, IReadOnlyList<DateOnly> unread, bool withheld) =>
        read.Unreachable is null && withheld
            ? Gap.OfWords(telemetry.WordsOn())
            : Gap.Of(read.Unreachable, unread, read.Lines.Count, Emitting());

    // The switch is left out, because the store did answer for every read but these.
    public Gap InMeasures(string? unreachable, IReadOnlyList<string> measures) =>
        Gap.OfMeasures(unreachable, measures);

    public Gap InSpans(SessionSpans read) =>
        Gap.OfSpans(read.Unreachable, read.Shortened, read.Spans.Count, telemetry.TracesOn());

    public Gap InDepths(TracedSessions read) => Gap.OfDepths(read.Unreachable, read.Shortened);

    // The switch calls unreadable settings not emitting: safe for writing, but a lie on a screen.
    private bool? Emitting()
    {
        var state = telemetry.State();

        return state.Readable ? state.Emitting : null;
    }
}
