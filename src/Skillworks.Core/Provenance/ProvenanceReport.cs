using Microsoft.Extensions.Options;
using Skillworks.Core.Settings;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Provenance;

public sealed class ProvenanceReport(
    SkillEvents events,
    TelemetrySwitch telemetry,
    IOptions<LokiOptions> options,
    TimeProvider clock)
{
    // Period only: an event carries no repository, so a project filter cannot narrow the origins.
    public async Task<ProvenanceReading> ForAsync(TelemetryFilter filter, CancellationToken cancellationToken)
    {
        var until = filter.UntilUtc ?? clock.GetUtcNow();
        var from = filter.FromUtc ?? until - TimeSpan.FromDays(options.Value.LookbackDays);

        return new ProvenanceReading(
            await events.ReadAsync(from, until, cancellationToken),
            from,
            Emitting());
    }

    public async Task<ProvenanceReading> AroundAsync(DateTimeOffset moment, CancellationToken cancellationToken)
    {
        var from = moment - ProvenanceReading.Tolerance;

        return new ProvenanceReading(
            await events.ReadAsync(from, moment + ProvenanceReading.Tolerance, cancellationToken),
            from,
            Emitting());
    }

    // The switch calls unreadable settings not emitting: safe for writing, but a lie on a screen.
    private bool? Emitting()
    {
        var state = telemetry.State();

        return state.Readable ? state.Emitting : null;
    }
}
