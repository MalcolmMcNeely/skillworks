using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    // An agent id is never empty, so this key cannot name a Subagent.
    private const string MainAgentKey = "";

    // Claude Code names the skill on the Turn alone, and a Tool call is written after the Turn that asked for it.
    public static StepsPage Steps(OpenedRun opened, OpenedSpans traced)
    {
        var asked = new Dictionary<string, Step>(StringComparer.Ordinal);
        var steps = new List<Step>();

        foreach (var step in opened.Drawn.Select(each => each.Step))
        {
            var agent = traced.Agents.GetValueOrDefault(step.Id) ?? MainAgentKey;

            if (step.Kind == StepKind.Turn)
            {
                asked[agent] = step;
            }

            var asker = asked.GetValueOrDefault(agent);

            steps.Add(step.Kind is StepKind.Tool or StepKind.Refused
                ? step with { Skill = asker?.Skill, Unnamed = asker?.Unnamed ?? false, SkillKnown = true }
                : step);
        }

        return new StepsPage(steps);
    }

    public static IReadOnlyList<Subagent> Ran(
        OpenedRun opened,
        IReadOnlyDictionary<string, string> agents,
        IReadOnlyDictionary<string, AgentRoot> wrapped)
    {
        var called = opened.Called.ToDictionary(call => call.ToolUse, StringComparer.Ordinal);
        var worked = Worked(opened.Drawn, agents);

        return
        [
            .. wrapped.Keys
                .Union(worked.Keys, StringComparer.Ordinal)
                .Select(agent => Tallied(
                    agent,
                    wrapped.GetValueOrDefault(agent),
                    worked.GetValueOrDefault(agent) ?? [],
                    called))
                .OrderBy(each => each.AtUtc)
        ];
    }

    private static Dictionary<string, IReadOnlyList<DrawnStep>> Worked(
        IReadOnlyList<DrawnStep> drawn,
        IReadOnlyDictionary<string, string> agents) =>
        drawn.Where(each => agents.ContainsKey(each.Step.Id))
            .GroupBy(each => agents[each.Step.Id], StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => (IReadOnlyList<DrawnStep>)[.. group], StringComparer.Ordinal);

    private static Subagent Tallied(
        string agent,
        AgentRoot? root,
        IReadOnlyList<DrawnStep> worked,
        IReadOnlyDictionary<string, AgentCall> called)
    {
        var call = root is null ? null : called.GetValueOrDefault(root.ToolUse);
        var began = root?.Started ?? worked.Min(each => each.Step.AtUtc);
        var ended = root?.Ended ?? worked.Max(each => each.Step.AtUtc.AddMilliseconds(each.Step.LengthMs));

        return new Subagent(
            agent,
            // Nothing reads as empty: the id is the last thing left that tells one Subagent from another.
            call?.Name ?? call?.Type ?? agent,
            call?.Type,
            began,
            (long)(ended - began).TotalMilliseconds,
            worked.Count(each => each.Step.Kind == StepKind.Tool),
            worked.Where(each => each.Step.Kind == StepKind.Turn).Sum(each => Number(each.Line, CostAttribute)),
            worked.Count(each => each.Step.Fault),
            call?.Brief,
            Reported(worked));
    }

    private static string? Reported(IReadOnlyList<DrawnStep> worked) =>
        worked.LastOrDefault(each => each.Step.Kind == StepKind.Answer) is { } last
            ? Recorded(last.Line, EventAttributes.Response)
            : null;

    private static IReadOnlyList<AgentCall> Called(IReadOnlyList<EventLine> lines) =>
    [
        .. lines
            .Where(line => Named(ToolCallEvent)(line) && line.Attribute(ToolAttribute) == AgentCall.Tool)
            .Select(line => line.Attribute(StepKey.ToolUse) is { Length: > 0 } use
                ? AgentCall.Of(use, Recorded(line, EventAttributes.ToolInput))
                : null)
            .OfType<AgentCall>()
    ];
}
