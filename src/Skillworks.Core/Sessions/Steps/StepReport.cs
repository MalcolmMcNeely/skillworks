using System.Runtime.CompilerServices;
using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;
using Skillworks.Core.Sessions.Queries;

namespace Skillworks.Core.Sessions.Steps;

public sealed class StepReport(StepQueries steps, GapReport gaps, Lookback lookback)
{
    public async IAsyncEnumerable<ArrivingLine> AnswerAsync(
        string id,
        Filter filter,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);
        var (run, opened, read) = await steps.OpenAsync(id, span, cancellationToken);

        yield return new StepsHead(run);

        if (read.Unreachable is null)
        {
            yield return new StepsPage(opened);
        }

        yield return new GapEnd(gaps.InLines(read, read.Unreachable is null ? [] : span.NewestFirst()));
    }
}
