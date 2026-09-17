using System.Globalization;
using Skillworks.Core.Tests.TraceStore;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string AgentTrace = "7a1c0a9e0000400080000000000000b2";

    private const string FirstCallSpan = "c11c0a9e00000001";

    private const string FirstRunSpan = "c11c0a9e00000002";

    private const string SecondCallSpan = "c11c0a9e00000003";

    private const string SecondRunSpan = "c11c0a9e00000004";

    private const string ThirdCallSpan = "c11c0a9e00000005";

    private const string ThirdRunSpan = "c11c0a9e00000006";

    private const string InsideSpan = "c11c0a9e00000007";

    private const string OtherInsideSpan = "c11c0a9e00000008";

    [Fact]
    public async Task Lists_every_subagent_the_session_ran()
    {
        using var studio = new StudioHost();

        await TwoRan(studio);

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(["agent-a", "agent-b"], answer.Subagents.Select(agent => agent.Id));
    }

    [Fact]
    public async Task Shows_each_subagent_with_its_name_type_length_cost_tool_calls_and_faults()
    {
        using var studio = new StudioHost();

        await TwoRan(studio);

        var agent = (await studio.StepAnswer(Morning)).Subagents[0];

        Assert.Equal("Find the leak", agent.Name);
        Assert.Equal("Explore", agent.Type);
        Assert.Equal(DateTimeOffset.Parse("2026-09-14T09:00:11Z", CultureInfo.InvariantCulture), agent.AtUtc);
        Assert.Equal(28_000, agent.LengthMs);
        Assert.Equal(1, agent.ToolCalls);
        Assert.Equal(0.40m, agent.Cost);
        Assert.Equal(0, agent.Faults);
    }

    [Fact]
    public async Task Sets_three_siblings_fired_together_side_by_side_so_an_expensive_one_stands_out()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, "2026-09-14T09:00:20.000Z", 3_000, 0.10m, "req_a"),
            SessionEvent.Turned(Morning, "2026-09-14T09:00:21.000Z", 3_000, 0.40m, "req_b"),
            SessionEvent.Turned(Morning, "2026-09-14T09:00:22.000Z", 3_000, 0.10m, "req_c"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Read the tests", "Explore", "Read", 30_000),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:41.000Z", "toolu_b", "Read the source", "Explore", "Read", 30_000),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:42.000Z", "toolu_c", "Read the docs", "Explore", "Read", 30_000));

        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"),
            Called(SecondCallSpan, "toolu_b"),
            Wrapped(SecondRunSpan, SecondCallSpan, "toolu_b", "agent-b"),
            Called(ThirdCallSpan, "toolu_c"),
            Wrapped(ThirdRunSpan, ThirdCallSpan, "toolu_c", "agent-c"),
            Thought(InsideSpan, "req_a", "agent-a"),
            Thought(OtherInsideSpan, "req_b", "agent-b"),
            Thought("c11c0a9e00000009", "req_c", "agent-c"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal([0.10m, 0.40m, 0.10m], answer.Subagents.Select(agent => agent.Cost));
    }

    [Fact]
    public async Task Tells_two_subagents_of_one_type_running_at_once_apart()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:20.000Z", "Grep", 2_000, "toolu_one"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:21.000Z", "Grep", 2_000, "toolu_two"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Read the tests", "Explore", "Read", 30_000),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:41.000Z", "toolu_b", "Read the source", "Explore", "Read", 30_000));

        // Both carry the same type and their events interleave, so only their agent ids keep them apart.
        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"),
            Called(SecondCallSpan, "toolu_b"),
            Wrapped(SecondRunSpan, SecondCallSpan, "toolu_b", "agent-b"),
            Used(InsideSpan, "toolu_one", "agent-a"),
            Used(OtherInsideSpan, "toolu_two", "agent-b"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(["agent-a", "agent-b"], answer.Subagents.Select(agent => agent.Id));
        Assert.Equal(["Read the tests", "Read the source"], answer.Subagents.Select(agent => agent.Name));
        Assert.Equal([1, 1], answer.Subagents.Select(agent => agent.ToolCalls));
    }

    [Fact]
    public async Task Counts_a_tool_call_to_the_subagent_that_made_it_and_not_to_the_main_agent()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:05.000Z", "Read", 1_000, "toolu_main"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:20.000Z", "Grep", 2_000, "toolu_one"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Read the tests", "Explore", "Read", 30_000));

        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"),
            Used(InsideSpan, "toolu_one", "agent-a"),
            Used(OtherInsideSpan, "toolu_main", null));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(1, Assert.Single(answer.Subagents).ToolCalls);
    }

    [Fact]
    public async Task Reads_the_subagents_own_run_and_not_a_tool_call_it_made_as_the_span_that_wraps_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:20.000Z", "Grep", 2_000, "toolu_grep"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Find the leak", "Explore", "Read", 30_000));

        // Every Tool call wraps in a span of this name, so only the agent id tells the Subagent's run apart.
        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"),
            Used(InsideSpan, "toolu_grep", "agent-a"),
            Wrapped(OtherInsideSpan, InsideSpan, "toolu_grep", "agent-a", "2026-09-14T09:00:18Z", "2026-09-14T09:00:20Z"));

        var agent = Assert.Single((await studio.StepAnswer(Morning)).Subagents);

        Assert.Equal("Find the leak", agent.Name);
        Assert.Equal("Explore", agent.Type);
        Assert.Equal(DateTimeOffset.Parse("2026-09-14T09:00:11Z", CultureInfo.InvariantCulture), agent.AtUtc);
        Assert.Equal(28_000, agent.LengthMs);
    }

    [Fact]
    public async Task Counts_a_failed_tool_call_as_the_subagents_own_fault()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolFailed(Morning, "2026-09-14T09:00:20.000Z", "Bash", "toolu_one"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Build it", "Explore", "Build", 30_000));

        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"),
            Used(InsideSpan, "toolu_one", "agent-a"));

        Assert.Equal(1, Assert.Single((await studio.StepAnswer(Morning)).Subagents).Faults);
    }

    [Fact]
    public async Task Reads_a_subagents_final_report_in_full_and_uncut()
    {
        using var studio = new StudioHost();

        var report = new string('r', 400);

        await studio.Push(
            SessionEvent.Answered(Morning, "2026-09-14T09:00:25.000Z", "Half way there.", "req_a"),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:30.000Z", report, "req_a"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Read the tests", "Explore", "Read", 30_000));

        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"),
            Thought(InsideSpan, "req_a", "agent-a"));

        var answer = await studio.StepAnswer(Morning);

        // A mark on a timeline carries a phrase, and the report is the whole of the last answer beside it.
        Assert.Equal(report, Assert.Single(answer.Subagents).Report);
        Assert.Contains(answer.Steps, step => step.Words is not null && step.Words.Length < report.Length);
    }

    [Fact]
    public async Task Shows_the_name_its_caller_gave_a_subagent_and_the_opening_words_of_its_brief()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.AgentRan(
                Morning,
                "2026-09-14T09:00:40.000Z",
                "toolu_a",
                "Find the leak",
                "Explore",
                "Read every file under src and say where the handle is left open",
                30_000));

        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"));

        var agent = Assert.Single((await studio.StepAnswer(Morning)).Subagents);

        Assert.Equal("Find the leak", agent.Name);
        Assert.Equal("Read every file under src and say where the handle is left open", agent.Brief);
    }

    [Fact]
    public async Task Names_a_subagent_by_its_type_when_its_caller_wrote_no_description()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", type: "Explore", brief: "Read", lengthMs: 30_000));

        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"));

        Assert.Equal("Explore", Assert.Single((await studio.StepAnswer(Morning)).Subagents).Name);
    }

    [Fact]
    public async Task Names_a_subagent_by_its_agent_id_when_nothing_of_the_call_was_recorded()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.AgentInputWithheld(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", 30_000));

        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a"));

        var agent = Assert.Single((await studio.StepAnswer(Morning)).Subagents);

        Assert.Equal("agent-a", agent.Name);
        Assert.Null(agent.Brief);
    }

    [Fact]
    public async Task Leaves_a_thin_run_with_no_subagents_rather_than_guessing_at_them()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Find the leak", "Explore", "Read", 30_000));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal("thin", answer.Depth);
        Assert.Empty(answer.Subagents);
    }

    [Fact]
    public async Task Sends_a_subagent_as_figures_and_words_and_never_the_span_itself()
    {
        using var studio = new StudioHost();

        await TwoRan(studio);

        var line = await studio.StepLine("agents", Morning);

        Assert.Equal(
            ["atUtc", "brief", "cost", "faults", "id", "lengthMs", "name", "report", "toolCalls", "type"],
            StudioHost.Fields(line["subagents"]?[0]));
    }

    private static async Task TwoRan(StudioHost studio)
    {
        await studio.Push(
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:20.000Z", "Grep", 2_000, "toolu_grep"),
            SessionEvent.Turned(Morning, "2026-09-14T09:00:25.000Z", 3_000, 0.40m, "req_a"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Find the leak", "Explore", "Read", 30_000),
            SessionEvent.Turned(Morning, "2026-09-14T09:01:20.000Z", 3_000, 0.10m, "req_b"),
            SessionEvent.AgentRan(Morning, "2026-09-14T09:01:40.000Z", "toolu_b", "Review the diff", "Review", "Judge", 30_000));

        await studio.PushSpans(
            Morning,
            AgentTrace,
            Called(FirstCallSpan, "toolu_a"),
            Wrapped(FirstRunSpan, FirstCallSpan, "toolu_a", "agent-a", "2026-09-14T09:00:11Z", "2026-09-14T09:00:39Z"),
            Used(InsideSpan, "toolu_grep", "agent-a"),
            Thought(OtherInsideSpan, "req_a", "agent-a"),
            Called(SecondCallSpan, "toolu_b"),
            Wrapped(SecondRunSpan, SecondCallSpan, "toolu_b", "agent-b", "2026-09-14T09:01:11Z", "2026-09-14T09:01:39Z"),
            Thought("c11c0a9e00000009", "req_b", "agent-b"));
    }

    // The Agent Tool call, which belongs to the caller and so carries no agent id of its own.
    private static RecordedSpan Called(string id, string toolUse) =>
        new("claude_code.tool", "2026-09-14T09:00:10Z", "2026-09-14T09:00:40Z", id, ToolUse: toolUse);

    // The Span Claude Code wraps a whole Subagent run in, and the only place its agent id meets the call's.
    private static RecordedSpan Wrapped(
        string id,
        string parent,
        string toolUse,
        string agent,
        string at = "2026-09-14T09:00:11Z",
        string until = "2026-09-14T09:00:39Z") =>
        new("claude_code.tool.execution", at, until, id, parent, agent, toolUse);

    private static RecordedSpan Used(string id, string toolUse, string? agent) =>
        new("claude_code.tool", "2026-09-14T09:00:18Z", "2026-09-14T09:00:20Z", id, Agent: agent, ToolUse: toolUse);

    private static RecordedSpan Thought(string id, string request, string agent) =>
        new("claude_code.llm_request", "2026-09-14T09:00:22Z", "2026-09-14T09:00:25Z", id, Agent: agent, Request: request);
}
