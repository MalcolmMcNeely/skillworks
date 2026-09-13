using Microsoft.Extensions.Options;
using Skillworks.Core.Settings;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Provenance;

/// <summary>
/// Reads provenance for the period a screen is looking at. It owns the one rule the events store
/// cannot be asked without: what period "everything" means, given a store that will not answer a
/// question longer than a month.
/// <para>
/// It also asks the switch, every time. An empty answer means one thing when Claude Code is filling
/// the store and another when it has never been asked to, and the store itself cannot tell them
/// apart.
/// </para>
/// </summary>
public sealed class ProvenanceReport(
    SkillEvents events,
    TelemetrySwitch telemetry,
    IOptions<LokiOptions> options,
    TimeProvider clock)
{
    /// <summary>
    /// The same period the rest of the screen is narrowed to, so provenance and cost answer for
    /// the same slice of history rather than for two.
    /// </summary>
    /// <remarks>
    /// Narrowed by period alone. An event carries no repository, so a screen narrowed to one
    /// project gets the ways a name was delivered anywhere in that period. That is wider than the
    /// row beside it, and the only alternative is to show a filtered screen no provenance at all.
    /// </remarks>
    public async Task<ProvenanceReading> ForAsync(TelemetryFilter filter, CancellationToken cancellationToken)
    {
        var until = filter.UntilUtc ?? clock.GetUtcNow();
        var from = filter.FromUtc ?? until - TimeSpan.FromDays(options.Value.LookbackDays);

        return new ProvenanceReading(
            await events.ReadAsync(from, until, cancellationToken),
            from,
            Emitting());
    }

    /// <summary>
    /// The moments around one firing, which is all a single firing can be joined to. Asking for
    /// the whole filtered period would read a month of events to answer about a second of it.
    /// </summary>
    public async Task<ProvenanceReading> AroundAsync(DateTimeOffset moment, CancellationToken cancellationToken)
    {
        var from = moment - ProvenanceReading.Tolerance;

        return new ProvenanceReading(
            await events.ReadAsync(from, moment + ProvenanceReading.Tolerance, cancellationToken),
            from,
            Emitting());
    }

    /// <summary>
    /// Whether Claude Code is emitting, or null when Studio could not read the settings and so
    /// cannot say. The switch reports a document it could not parse as not emitting, which is the
    /// safe answer for deciding whether to write it and would be a lie on a screen.
    /// </summary>
    private bool? Emitting()
    {
        var state = telemetry.State();

        return state.Readable ? state.Emitting : null;
    }
}
