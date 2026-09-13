using Skillworks.Core.Provenance;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

/// <summary>The firings the filter takes in, and what the events store had to say about them.</summary>
public sealed record ActivationList(
    IReadOnlyList<ActivationSummary> Activations,
    ProvenanceNote Provenance);

/// <summary>One firing opened, beside the same note.</summary>
public sealed record ActivationOpened(ActivationDetail Activation, ProvenanceNote Provenance);

/// <summary>
/// The firings, with what set each one off. The transcript says a skill fired and the events store
/// says whether Claude chose it or a developer typed it, so the two are joined here, on skill name
/// and moment, and never on a screen.
/// </summary>
public sealed class ActivationReport(ActivationStore activations, ProvenanceReport provenance)
{
    public async Task<ActivationList> ListAsync(TelemetryFilter filter, CancellationToken cancellationToken)
    {
        var listed = await activations.ListAsync(filter, cancellationToken);
        var origins = await provenance.ForAsync(filter, cancellationToken);

        return new ActivationList(
            [.. listed.Select(a => a with { Origin = origins.Nearest(a.Skill, a.TimestampUtc) })],
            origins.Note);
    }

    /// <summary>One firing by its id, or null when the ingest has never read it.</summary>
    public async Task<ActivationOpened?> OpenAsync(string id, CancellationToken cancellationToken)
    {
        if (await activations.OpenAsync(id, cancellationToken) is not { } activation)
        {
            return null;
        }

        var origins = await provenance.AroundAsync(activation.TimestampUtc, cancellationToken);

        return new ActivationOpened(
            activation with { Origin = origins.Nearest(activation.Skill, activation.TimestampUtc) },
            origins.Note);
    }
}
