using Skillworks.Core.Tests.TraceStore;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string SplitTrace = "7a1c0a9e0000400080000000000000d4";

    private const string WaitedSpan = "e11c0a9e00000001";

    private const string HookedSpan = "e11c0a9e00000002";

    private const string WrapSpan = "e11c0a9e00000003";

    private const string GrepSpan = "e11c0a9e00000004";

    [Fact]
    public async Task Answers_with_the_split_once_the_spans_have_landed()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        var lines = await studio.StepLines(Morning);

        Assert.Equal(
            ["head", "exchanges", "activations", "context", "findings", "steps", "trace", "agents", "split", "findings", "end"],
            lines.Select(StudioHost.KindOf));
    }

    [Fact]
    public async Task Sends_the_exclusive_parts_and_the_overlapping_kinds_beside_them()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        var line = await studio.StepLine("split", Morning);

        Assert.Equal(["depth", "kind", "kinds", "parts"], StudioHost.Fields(line));
        Assert.Equal(["atUtc", "lengthMs", "part"], StudioHost.Fields(line["parts"]?[0]));
    }

    [Fact]
    public async Task Splits_the_run_into_parts_that_add_up_to_its_length()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(answer.Run?.LengthMs, answer.Parts.Sum(spell => spell.LengthMs));
    }

    [Fact]
    public async Task Gives_no_moment_of_the_run_to_two_parts()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        var parts = (await studio.PartsIn(Morning)).OrderBy(spell => spell.AtUtc).ToList();

        Assert.All(
            parts.Zip(parts.Skip(1)),
            pair => Assert.True(pair.First.AtUtc.AddMilliseconds(pair.First.LengthMs) <= pair.Second.AtUtc));
    }

    [Fact]
    public async Task Splits_a_run_into_the_model_thinking_the_tools_running_and_the_quiet_between_them()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        var split = Totals(await studio.PartsIn(Morning));

        Assert.Equal(5_000, split["model"]);
        Assert.Equal(5_000, split["tools"]);

        // Between the Turn ending and the Tool call starting, and again from the call up to the answer.
        Assert.Equal(5_000, split["quiet"]);
    }

    [Fact]
    public async Task Counts_the_wait_for_permission_apart_from_the_tool_that_waited()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        await studio.PushSpans(
            Morning,
            SplitTrace,
            Waits(WaitedSpan, "toolu_01", "2026-09-14T09:00:07Z", "2026-09-14T09:00:10Z"));

        var split = Totals(await studio.PartsIn(Morning));

        Assert.Equal(3_000, split["waiting"]);

        // What is left of the call once the person has answered, so their delay never reads as the tool's work.
        Assert.Equal(2_000, split["tools"]);
    }

    [Fact]
    public async Task Counts_the_wait_before_a_tool_call_a_person_refused()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Drop the table"),
            SessionEvent.Refused(Morning, "2026-09-14T09:00:05.000Z"));

        await studio.PushSpans(
            Morning,
            SplitTrace,
            Waits(WaitedSpan, "toolu_gone", "2026-09-14T09:00:01Z", "2026-09-14T09:00:05Z"));

        // The call never ran, so the whole of its stretch is the time a person took to say no.
        Assert.Equal(4_000, Totals(await studio.PartsIn(Morning))["waiting"]);
    }

    [Fact]
    public async Task Counts_a_hook_that_ran_inside_a_tool_call_as_a_hook_and_not_as_the_tool()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        // A hook guarding a Tool call runs inside the length Claude Code records for it.
        await studio.PushSpans(
            Morning,
            SplitTrace,
            Hooks(HookedSpan, null, "2026-09-14T09:00:07Z", "2026-09-14T09:00:09Z"));

        var split = Totals(await studio.PartsIn(Morning));

        Assert.Equal(2_000, split["hooks"]);
        Assert.Equal(3_000, split["tools"]);
    }

    [Fact]
    public async Task Counts_an_agent_tool_call_of_a_thin_run_as_a_tool_call_rather_than_losing_its_time()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Find the leak"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Find it", "Explore", lengthMs: 30_000),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:41.000Z", "Found."));

        var answer = await studio.StepAnswer(Morning);
        var split = Totals(answer.Parts);

        // With no Span there is no spell to stand for the work, and nothing running would be a lie.
        Assert.Equal("thin", answer.Depth);
        Assert.Equal(30_000, split["tools"]);
    }

    [Fact]
    public async Task Counts_a_hook_the_main_agent_ran()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        await studio.PushSpans(
            Morning,
            SplitTrace,
            Hooks(HookedSpan, null, "2026-09-14T09:00:05Z", "2026-09-14T09:00:07Z"));

        var split = Totals(await studio.PartsIn(Morning));

        Assert.Equal(2_000, split["hooks"]);
        Assert.Equal(3_000, split["quiet"]);
    }

    [Fact]
    public async Task Leaves_a_hook_a_subagent_ran_out_of_the_main_agents_hooks()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        await studio.PushSpans(
            Morning,
            SplitTrace,
            Hooks(HookedSpan, "agent-a", "2026-09-14T09:00:05Z", "2026-09-14T09:00:07Z"));

        Assert.False(Totals(await studio.PartsIn(Morning)).ContainsKey("hooks"));
    }

    [Fact]
    public async Task Gives_a_subagents_work_to_its_own_part_while_the_main_agent_is_idle()
    {
        using var studio = new StudioHost();

        await Worked(studio);

        var split = Totals(await studio.PartsIn(Morning));

        // The Agent Tool call only starts the Subagent, so the stretch is its work and never the main agent's.
        Assert.Equal(30_000, split["subagents"]);
        Assert.False(split.ContainsKey("tools"));
    }

    [Fact]
    public async Task Leaves_a_tool_call_a_subagent_made_out_of_the_main_agents_tools()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Find the leak"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:30.000Z", "Grep", 5_000, "toolu_grep"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Find it", "Explore", lengthMs: 30_000),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:41.000Z", "Found."));

        await studio.PushSpans(
            Morning,
            SplitTrace,
            Wraps(WrapSpan, "toolu_a", "agent-a"),
            Under(GrepSpan, WrapSpan, "toolu_grep", "agent-a"));

        var split = Totals(await studio.PartsIn(Morning));

        Assert.Equal(30_000, split["subagents"]);
        Assert.False(split.ContainsKey("tools"));
    }

    [Fact]
    public async Task Gives_a_turn_that_is_not_the_main_agents_to_side_requests()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"),
            SessionEvent.Turned(Morning, "2026-09-14T09:00:05.000Z", 5_000, source: "compact"),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:10.000Z", "Built."));

        var split = Totals(await studio.PartsIn(Morning));

        Assert.Equal(5_000, split["side"]);
        Assert.False(split.ContainsKey("model"));
    }

    [Fact]
    public async Task Counts_the_stretch_between_one_exchange_and_the_next_as_the_readers_own_turn()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:10.000Z", "Built."),
            SessionEvent.Prompted(Morning, "2026-09-14T09:01:00.000Z", "Now ship it"),
            SessionEvent.Answered(Morning, "2026-09-14T09:01:10.000Z", "Shipped."));

        var split = Totals(await studio.PartsIn(Morning));

        Assert.Equal(50_000, split["yourTurn"]);
        Assert.Equal(20_000, split["quiet"]);
    }

    [Fact]
    public async Task Reports_the_overlapping_sum_of_a_kind_beside_the_exclusive_part()
    {
        using var studio = new StudioHost();

        await Worked(studio);

        await studio.Push(SessionEvent.Turned(Morning, "2026-09-14T09:00:30.000Z", 10_000));

        var answer = await studio.StepAnswer(Morning);

        // The main agent's Turn takes the ten seconds they share, and the whole of each still reads here.
        Assert.Equal(20_000, Totals(answer.Parts)["subagents"]);
        Assert.Equal(30_000, Totals(answer.Kinds)["subagents"]);
        Assert.Equal(10_000, Totals(answer.Kinds)["model"]);
    }

    [Fact]
    public async Task Says_nothing_of_the_wait_the_hooks_or_the_subagents_of_a_thin_run()
    {
        using var studio = new StudioHost();

        await Turned(studio);

        await studio.Push(SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", lengthMs: 30_000));

        var answer = await studio.StepAnswer(Morning);
        var split = Totals(answer.Parts);

        // No Span, so none of the three can be known, and each is left out rather than read as none.
        Assert.Equal("thin", answer.Depth);
        Assert.False(split.ContainsKey("waiting"));
        Assert.False(split.ContainsKey("hooks"));
        Assert.False(split.ContainsKey("subagents"));
        Assert.True(split.ContainsKey("tools"));
    }

    private static Task Turned(StudioHost studio) =>
        studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"),
            SessionEvent.Turned(Morning, "2026-09-14T09:00:05.000Z", 5_000, source: "main"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:12.000Z", "Bash", 5_000, "toolu_01"),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:15.000Z", "Built."));

    // A Subagent's spell comes off the Span that wraps it, never off the event.
    private static async Task Worked(StudioHost studio)
    {
        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Find the leak"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Find it", "Explore", lengthMs: 30_000),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:41.000Z", "Found."));

        await studio.PushSpans(Morning, SplitTrace, Wraps(WrapSpan, "toolu_a", "agent-a"));
    }

    private static RecordedSpan Waits(string id, string toolUse, string at, string until) =>
        new("claude_code.tool.blocked_on_user", at, until, id, ToolUse: toolUse);

    private static RecordedSpan Hooks(string id, string? agent, string at, string until) =>
        new("claude_code.hook", at, until, id, Agent: agent);

    private static RecordedSpan Wraps(string id, string toolUse, string agent) =>
        new(
            "claude_code.tool.execution",
            "2026-09-14T09:00:10Z",
            "2026-09-14T09:00:40Z",
            id,
            Agent: agent,
            ToolUse: toolUse);

    private static RecordedSpan Under(string id, string parent, string toolUse, string agent) =>
        new("claude_code.tool", "2026-09-14T09:00:25Z", "2026-09-14T09:00:30Z", id, parent, agent, toolUse);

    private static IReadOnlyDictionary<string, long> Totals(IReadOnlyList<PartSpellRow> spells) =>
        spells
            .GroupBy(spell => spell.Part, StringComparer.Ordinal)
            .ToDictionary(part => part.Key, part => part.Sum(spell => spell.LengthMs), StringComparer.Ordinal);
}
