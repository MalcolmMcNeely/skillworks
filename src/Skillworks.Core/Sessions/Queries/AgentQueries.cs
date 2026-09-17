using Skillworks.Core.Filters;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed class AgentQueries(TraceStoreReader traces)
{
    private const string AgentAttribute = "agent_id";

    private const string ToolSpan = "claude_code.tool";

    private const string TurnSpan = "claude_code.llm_request";

    public async Task<OpenedSpans> OfRunAsync(
        string id,
        DaySpan span,
        IReadOnlyList<StepKey> keys,
        CancellationToken cancellationToken)
    {
        var read = await traces.OfSessionAsync(id, span.FromUtc, cancellationToken);

        // A run recorded before traces were switched on comes back with none, and that is Thin and not broken.
        return new OpenedSpans(read.Spans.Count > 0 ? Depth.Full : Depth.Thin, RanBy(read.Spans, keys), read);
    }

    private static IReadOnlyDictionary<string, string> RanBy(IReadOnlyList<Span> spans, IReadOnlyList<StepKey> keys)
    {
        var agents = Named(spans);
        var ran = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var key in keys)
        {
            if (agents.TryGetValue(key.Key, out var agent))
            {
                ran[key.Step] = agent;
            }
        }

        return ran;
    }

    // Only a Subagent's spans carry an agent id, so a key left out here belongs to the main thread.
    private static Dictionary<string, string> Named(IReadOnlyList<Span> spans)
    {
        var agents = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var span in spans)
        {
            if (Keyed(span) is { } key && span.Attributes.GetValueOrDefault(AgentAttribute) is { Length: > 0 } agent)
            {
                agents[key] = agent;
            }
        }

        return agents;
    }

    // Every Span beneath a Subagent carries its agent id, and one of them repeats the tool use id of the
    // call that started it, so only the Span a key belongs to may answer for that key.
    private static string? Keyed(Span span) => span.Name switch
    {
        ToolSpan => span.Attributes.GetValueOrDefault(StepKey.ToolUse),

        TurnSpan => span.Attributes.GetValueOrDefault(StepKey.Request),

        _ => null,
    };
}
