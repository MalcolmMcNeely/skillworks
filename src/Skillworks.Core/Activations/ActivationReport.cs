using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

public sealed class ActivationReport(ActivationQueries activations, ProvenanceReport provenance, Lookback lookback)
{
    public async Task<ActivationList> ListAsync(Filter filter, CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);
        var (listed, read, period) = await activations.ListAsync(span, filter, cancellationToken);

        return new ActivationList(listed, provenance.NoteOn(read, period, span), span);
    }

    public async Task<ActivationOpened?> OpenAsync(string id, CancellationToken cancellationToken)
    {
        if (ActivationId.Parse(id) is not { } activationId)
        {
            return null;
        }

        var (activation, read) = await activations.OpenAsync(activationId, cancellationToken);

        // An outage is not a not found, or a good link would say its firing never happened.
        if (activation is null && read.Unreachable is null)
        {
            return null;
        }

        return new ActivationOpened(activation, provenance.NoteOn(read, activationId.ReadFrom));
    }
}
