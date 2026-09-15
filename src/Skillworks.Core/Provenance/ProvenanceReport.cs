using Microsoft.Extensions.Options;
using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Provenance;

public sealed class ProvenanceReport(
    EventsStoreReader events,
    TelemetrySwitch telemetry,
    IOptions<LokiOptions> options,
    TimeProvider clock)
{
    // Period only: the activations it is joined to still name a repository by its folder, which no event carries.
    public async Task<ProvenanceReading> ForAsync(Filter filter, CancellationToken cancellationToken)
    {
        var until = filter.UntilUtc ?? clock.GetUtcNow();

        // All one query may span, as the activations it is joined to reach back without a limit.
        var from = filter.FromUtc ?? until - TimeSpan.FromDays(options.Value.MaxQueryDays);

        return new ProvenanceReading(
            await events.ReadAsync(SkillEvent.EventName, from, until, cancellationToken),
            from,
            Emitting());
    }

    public async Task<ProvenanceReading> AroundAsync(DateTimeOffset moment, CancellationToken cancellationToken)
    {
        var from = moment - ProvenanceReading.Tolerance;

        return new ProvenanceReading(
            await events.ReadAsync(SkillEvent.EventName, from, moment + ProvenanceReading.Tolerance, cancellationToken),
            from,
            Emitting());
    }

    public ProvenanceNote NoteOn(EventCounts period, DaySpan span) =>
        ProvenanceNote.Of(period.Unreachable, period.Events, truncated: false, Emitting(), span.FromUtc);

    // The switch calls unreadable settings not emitting: safe for writing, but a lie on a screen.
    private bool? Emitting()
    {
        var state = telemetry.State();

        return state.Readable ? state.Emitting : null;
    }
}
