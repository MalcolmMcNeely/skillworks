using System.Runtime.CompilerServices;
using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Context;
using Skillworks.Core.Sessions.Exchanges;
using Skillworks.Core.Sessions.Queries;
using Skillworks.Core.Sessions.SkillCalls;

namespace Skillworks.Core.Sessions.Steps;

public sealed class StepReport(StepQueries steps, AgentQueries agents, GapReport gaps, Lookback lookback)
{
    public async IAsyncEnumerable<ArrivingLine> AnswerAsync(
        string id,
        Filter filter,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);
        var opened = await steps.OpenAsync(id, span, cancellationToken);

        yield return new StepsHead(opened.Run);

        if (opened.Read.Unreachable is null)
        {
            // Ahead of the steps, so a screen that draws on the steps landing has every panel already.
            yield return new ExchangesPage(opened.Said);
            yield return new SkillCallsPage(opened.Fired);
            yield return new ContextPage(opened.Sent, opened.LimitTokens);
            yield return new StepsPage(opened.Steps);
        }

        // Asked for once the events have drawn all they can, so a slow trace store delays only what they cannot.
        var ran = await agents.OfRunAsync(id, span, opened.Keys, cancellationToken);

        yield return new AgentsPage(ran.Depth, ran.Agents);

        yield return new StoresEnd(
            gaps.InLines(opened.Read, opened.Read.Unreachable is null ? [] : span.NewestFirst()),
            gaps.InSpans(ran.Read));
    }
}
