using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

public sealed class ActivationReport(ActivationQueries activations, ProvenanceReport provenance)
{
    public async Task<ActivationList> ListAsync(TelemetryFilter filter, CancellationToken cancellationToken)
    {
        var listed = await activations.ListAsync(filter, cancellationToken);
        var origins = await provenance.ForAsync(filter, cancellationToken);

        return new ActivationList(
            [.. listed.Select(a => a with { Origin = origins.Nearest(a.Skill, a.TimestampUtc) })],
            origins.Note);
    }

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
