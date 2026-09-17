using Skillworks.Core.Tests.TraceStore;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string TreeTrace = "7a1c0a9e0000400080000000000000c3";

    private const string AskedSpan = "d11c0a9e00000001";

    private const string UsedSpan = "d11c0a9e00000002";

    private const string CalledSpan = "d11c0a9e00000003";

    private const string RunSpan = "d11c0a9e00000004";

    private const string WithinSpan = "d11c0a9e00000005";

    [Fact]
    public async Task Answers_with_the_tree_once_the_spans_have_landed()
    {
        using var studio = new StudioHost();

        await NestedRan(studio);

        var lines = await studio.StepLines(Morning);

        Assert.Equal(
            ["head", "exchanges", "skillCalls", "context", "steps", "trace", "agents", "end"],
            lines.Select(StudioHost.KindOf));
    }

    [Fact]
    public async Task Sends_which_step_each_step_ran_inside_and_never_the_span_itself()
    {
        using var studio = new StudioHost();

        await NestedRan(studio);

        var line = await studio.StepLine("trace", Morning);

        Assert.Equal(["inside", "kind"], StudioHost.Fields(line));
    }

    [Fact]
    public async Task Nests_a_step_inside_the_step_whose_span_holds_its_own()
    {
        using var studio = new StudioHost();

        await NestedRan(studio);

        var answer = await studio.StepAnswer(Morning);
        var turn = answer.Steps[0];
        var tool = answer.Steps[1];

        Assert.Equal(turn.Id, answer.Inside[tool.Id]);
    }

    [Fact]
    public async Task Leaves_a_step_with_nothing_above_its_span_at_the_root()
    {
        using var studio = new StudioHost();

        await NestedRan(studio);

        var answer = await studio.StepAnswer(Morning);

        Assert.False(answer.Inside.ContainsKey(answer.Steps[0].Id));
    }

    [Fact]
    public async Task Nests_a_subagents_work_beneath_the_tool_call_that_started_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.AgentRan(Morning, "2026-09-14T09:00:40.000Z", "toolu_a", "Find the leak", "Explore", "Read", 30_000),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:20.000Z", "Grep", 2_000, "toolu_grep"));

        // The Span that wraps a Subagent's run stands for no Step, so the walk goes past it to the Agent call.
        await studio.PushSpans(
            Morning,
            TreeTrace,
            Starts(CalledSpan, "toolu_a"),
            Wraps(RunSpan, CalledSpan, "toolu_a", "agent-a"),
            Within(WithinSpan, RunSpan, "toolu_grep", "agent-a"));

        var answer = await studio.StepAnswer(Morning);
        var call = answer.Steps.Single(step => step.Tool == "Agent");
        var grep = answer.Steps.Single(step => step.Tool == "Grep");

        Assert.Equal(call.Id, answer.Inside[grep.Id]);
    }

    [Fact]
    public async Task Leaves_a_turn_and_the_answer_it_wrote_side_by_side_rather_than_one_inside_the_other()
    {
        using var studio = new StudioHost();

        // One request writes both events and both join to one span, so neither can hold the other.
        await studio.Push(
            SessionEvent.Turned(Morning, "2026-09-14T09:00:20.000Z", 2_000, request: "req_01"),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:22.000Z", "Built.", "req_01"));

        await studio.PushSpans(Morning, TreeTrace, Asks(AskedSpan, "req_01"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Empty(answer.Inside);
    }

    [Fact]
    public async Task Leaves_a_step_whose_span_nothing_above_stands_for_at_the_root()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.ToolRan(Morning, "2026-09-14T09:00:20.000Z", "Grep", 2_000, "toolu_grep"));

        await studio.PushSpans(
            Morning,
            TreeTrace,
            Wraps(RunSpan, null, "toolu_a", "agent-a"),
            Within(WithinSpan, RunSpan, "toolu_grep", "agent-a"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal("full", answer.Depth);
        Assert.Empty(answer.Inside);
    }

    [Fact]
    public async Task Leaves_a_thin_run_with_no_tree_at_all()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, "2026-09-14T09:00:20.000Z", 2_000, request: "req_01"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:25.000Z", "Bash", 3_000, use: "toolu_01"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal("thin", answer.Depth);
        Assert.Equal(2, answer.Steps.Count);
        Assert.Empty(answer.Inside);
    }

    private static async Task NestedRan(StudioHost studio)
    {
        await studio.Push(
            SessionEvent.Turned(Morning, "2026-09-14T09:00:20.000Z", 2_000, request: "req_01"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:25.000Z", "Bash", 3_000, use: "toolu_01"));

        await studio.PushSpans(
            Morning,
            TreeTrace,
            Asks(AskedSpan, "req_01"),
            Within(UsedSpan, AskedSpan, "toolu_01", null));
    }

    private static RecordedSpan Asks(string id, string request) =>
        new("claude_code.llm_request", "2026-09-14T09:00:18Z", "2026-09-14T09:00:20Z", id, Request: request);

    private static RecordedSpan Within(string id, string? parent, string toolUse, string? agent) =>
        new("claude_code.tool", "2026-09-14T09:00:22Z", "2026-09-14T09:00:25Z", id, parent, agent, toolUse);

    private static RecordedSpan Starts(string id, string toolUse) =>
        new("claude_code.tool", "2026-09-14T09:00:10Z", "2026-09-14T09:00:40Z", id, ToolUse: toolUse);

    private static RecordedSpan Wraps(string id, string? parent, string toolUse, string agent) =>
        new("claude_code.tool.execution", "2026-09-14T09:00:11Z", "2026-09-14T09:00:39Z", id, parent, agent, toolUse);
}
