using Skillworks.Core.Filters;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Trace;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed class AgentQueries(TraceStoreReader traces)
{
    private const string AgentAttribute = "agent_id";

    private const string RunSpan = "claude_code.tool.execution";

    private const string WaitSpan = "claude_code.tool.blocked_on_user";

    private const string HookSpan = "claude_code.hook";

    public async Task<OpenedSpans> OfRunAsync(
        string id,
        DaySpan span,
        IReadOnlyList<StepKey> keys,
        IReadOnlyList<AgentCall> called,
        CancellationToken cancellationToken)
    {
        var read = await traces.OfSessionAsync(id, span.FromUtc, span.UntilUtc, cancellationToken);

        // A run recorded before traces were switched on comes back with none, and that is not a fault.
        return new OpenedSpans(
            read.Spans.Count > 0,
            RanBy(read.Spans, keys),
            SpanTree.Inside(read.Spans, keys),
            Wrapped(read.Spans, called),
            Waited(read.Spans),
            Hooked(read.Spans),
            read);
    }

    // Nothing an event carries says a person was asked, so a run with no Span cannot tell their delay from work.
    private static IReadOnlyDictionary<string, Spell> Waited(IReadOnlyList<Span> spans)
    {
        var waited = new Dictionary<string, Spell>(StringComparer.Ordinal);

        foreach (var span in spans)
        {
            if (span.Name == WaitSpan &&
                span.Attributes.GetValueOrDefault(StepKey.ToolUse) is { Length: > 0 } toolUse)
            {
                waited[toolUse] = Spelled(span);
            }
        }

        return waited;
    }

    // A Subagent's hook is that Subagent's work, and the main agent may have been busy through the whole of it.
    private static IReadOnlyList<Spell> Hooked(IReadOnlyList<Span> spans) =>
    [
        .. spans
            .Where(span => span.Name == HookSpan && Agent(span) is null)
            .Select(Spelled)
    ];

    private static Spell Spelled(Span span) =>
        new(span.Started, (long)(span.Ended - span.Started).TotalMilliseconds);

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

    // Only a Subagent's spans carry an agent id, so a key left out here belongs to the main agent.
    private static Dictionary<string, string> Named(IReadOnlyList<Span> spans)
    {
        var agents = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var span in spans)
        {
            if (StepKey.Of(span) is { } key && Agent(span) is { } agent)
            {
                agents[key] = agent;
            }
        }

        return agents;
    }

    // Every Tool call a Subagent makes wraps in a Span of this name carrying that Subagent's agent id, so the
    // one Span that wraps the whole run is the one whose Tool call is the Agent call that started it.
    private static IReadOnlyDictionary<string, AgentRoot> Wrapped(
        IReadOnlyList<Span> spans,
        IReadOnlyList<AgentCall> called)
    {
        var starters = called.Select(call => call.ToolUse).ToHashSet(StringComparer.Ordinal);
        var wrapped = new Dictionary<string, AgentRoot>(StringComparer.Ordinal);

        foreach (var span in spans)
        {
            if (span.Name == RunSpan &&
                Agent(span) is { } agent &&
                span.Attributes.GetValueOrDefault(StepKey.ToolUse) is { } toolUse &&
                starters.Contains(toolUse))
            {
                wrapped[agent] = new AgentRoot(toolUse, span.Started, span.Ended);
            }
        }

        return wrapped;
    }

    private static string? Agent(Span span) =>
        span.Attributes.GetValueOrDefault(AgentAttribute) is { Length: > 0 } agent ? agent : null;
}
