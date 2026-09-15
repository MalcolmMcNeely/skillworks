using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;

namespace Skillworks.Core.Activations;

public sealed class ActivationReport(ActivationQueries activations, GapReport gaps, Lookback lookback)
{
    public async Task<ActivationList> ListAsync(Filter filter, CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);
        var (listed, read, period) = await activations.ListAsync(span, filter, cancellationToken);

        return new ActivationList(listed, gaps.InList(read, period), span);
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

        return new ActivationOpened(activation, gaps.InRead(read));
    }
}
