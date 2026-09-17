using System.Runtime.CompilerServices;
using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;

namespace Skillworks.Core.Activations;

public sealed class ActivationReport(ActivationQueries activations, GapReport gaps, Lookback lookback)
{
    public async IAsyncEnumerable<ArrivingLine> AnswerAsync(
        Filter filter,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);
        var (fired, period) = await activations.ActivationsAsync(span, filter, cancellationToken);

        if (period.Unreachable is null)
        {
            yield return new ActivationsPage(fired);
        }

        yield return new GapEnd(gaps.InTotals(period, period.Unreachable is null ? [] : span.NewestFirst()));
    }
}
