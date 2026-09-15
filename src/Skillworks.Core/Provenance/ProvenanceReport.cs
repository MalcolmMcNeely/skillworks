using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Provenance;

public sealed class ProvenanceReport(TelemetrySwitch telemetry)
{
    public ProvenanceNote NoteOn(EventCounts period, DaySpan span) =>
        ProvenanceNote.Of(period.Unreachable, period.Events, cappedAt: null, Emitting(), span.FromUtc);

    // The whole period says whether anything fired, so a narrowed empty list is not quiet; only the read is ever cut.
    public ProvenanceNote NoteOn(EventReading listed, EventCounts period, DaySpan span) =>
        ProvenanceNote.Of(
            listed.Unreachable ?? period.Unreachable,
            period.Events,
            listed.Truncated ? listed.Events.Count : null,
            Emitting(),
            span.FromUtc);

    public ProvenanceNote NoteOn(EventReading around, DateTimeOffset sinceUtc) =>
        ProvenanceNote.Of(around.Unreachable, around.Events.Count, cappedAt: null, Emitting(), sinceUtc);

    // The switch calls unreadable settings not emitting: safe for writing, but a lie on a screen.
    private bool? Emitting()
    {
        var state = telemetry.State();

        return state.Readable ? state.Emitting : null;
    }
}
