using Skillworks.Core.Tests.TraceStore;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string MainTrace = "7a1c0a9e0000400080000000000000a1";

    private const string ToolSpan = "b11c0a9e00000001";

    private const string TurnSpan = "b11c0a9e00000002";

    [Fact]
    public async Task Answers_one_run_with_its_events_first_and_which_agent_ran_each_step_second()
    {
        using var studio = new StudioHost();

        await SubagentRan(studio);

        var lines = await studio.StepLines(Morning);

        Assert.Equal(
            ["head", "exchanges", "skillCalls", "context", "steps", "agents", "end"],
            lines.Select(StudioHost.KindOf));
    }

    [Fact]
    public async Task Sends_which_agent_ran_a_step_and_never_the_span_itself()
    {
        using var studio = new StudioHost();

        await SubagentRan(studio);

        var line = await studio.StepLine("agents", Morning);

        Assert.Equal(["agents", "depth", "kind"], StudioHost.Fields(line));
    }

    [Fact]
    public async Task Attributes_a_tool_call_to_the_agent_its_span_names()
    {
        using var studio = new StudioHost();

        await SubagentRan(studio);

        var answer = await studio.StepAnswer(Morning);
        var step = Assert.Single(answer.Steps);

        // No log event carries an agent id, so the tool use id is the only way back to the agent.
        Assert.Equal("agent-a", answer.Agents[step.Id]);
    }

    [Fact]
    public async Task Attributes_a_turn_and_the_answer_it_wrote_to_the_agent_their_span_names()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, "2026-09-14T09:00:20.000Z", 2_000, request: "req_01"),
            SessionEvent.Answered(Morning, "2026-09-14T09:00:22.000Z", "Built.", request: "req_01"));
        await studio.PushSpans(Morning, MainTrace, Asked(TurnSpan, "req_01", "agent-b"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(["agent-b", "agent-b"], answer.Steps.Select(step => answer.Agents[step.Id]));
    }

    [Fact]
    public async Task Leaves_a_step_whose_span_names_no_agent_on_the_main_thread()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:10.000Z", "Bash", 4_000, use: "toolu_01"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:30.000Z", "Read", 1_000, use: "toolu_02"));

        await studio.PushSpans(
            Morning,
            MainTrace,
            Ran(ToolSpan, "toolu_01", null),
            Ran(TurnSpan, "toolu_02", "agent-a"));

        var answer = await studio.StepAnswer(Morning);

        // Only a Subagent's spans carry an agent id, so the main thread is what is left unnamed.
        Assert.Equal("full", answer.Depth);
        Assert.False(answer.Agents.ContainsKey(answer.Steps[0].Id));
        Assert.Equal("agent-a", answer.Agents[answer.Steps[1].Id]);
    }

    [Fact]
    public async Task Raises_a_run_from_thin_to_full_once_its_spans_land()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.ToolRan(Morning, "2026-09-14T09:00:10.000Z", "Bash", 4_000, use: "toolu_01"));

        Assert.Equal("thin", (await studio.StepAnswer(Morning)).Depth);

        await studio.PushSpans(Morning, MainTrace, Ran(ToolSpan, "toolu_01", "agent-a"));

        Assert.Equal("full", (await studio.StepAnswer(Morning)).Depth);
    }

    [Fact]
    public async Task Opens_a_run_recorded_before_traces_were_switched_on_and_reads_it_thin()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:10.000Z", "Bash", 4_000, use: "toolu_01"));

        var answer = await studio.StepAnswer(Morning);

        Assert.NotNull(answer.Run);
        Assert.Equal(2, answer.Steps.Count);
        Assert.Equal("thin", answer.Depth);
        Assert.Empty(answer.Agents);
    }

    [Fact]
    public async Task Leaves_a_thin_run_rather_than_a_blank_page_when_the_trace_store_never_answers()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await studio.Push(SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"));

        var answer = await studio.StepAnswer(Morning);

        Assert.NotNull(answer.Run);
        Assert.Single(answer.Steps);
        Assert.Equal("thin", answer.Depth);
        Assert.Equal("complete", answer.Events.Kind);
        Assert.Equal("unreachable", answer.Traces.Kind);
    }

    [Fact]
    public async Task Names_the_trace_store_and_not_the_events_store_when_only_the_trace_store_falls_short()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await studio.Push(SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"));

        var answer = await studio.StepAnswer(Morning);

        Assert.NotNull(answer.Traces.Missing);
        Assert.DoesNotContain("events store", answer.Traces.Missing, StringComparison.OrdinalIgnoreCase);
        Assert.Null(answer.Events.Missing);
    }

    [Fact]
    public async Task Names_the_events_store_and_not_the_trace_store_when_only_the_events_store_falls_short()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        await studio.PushSpans(Morning, MainTrace, Ran(ToolSpan, "toolu_01", "agent-a"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal("unreachable", answer.Events.Kind);
        Assert.Equal("complete", answer.Traces.Kind);
    }

    [Fact]
    public async Task Says_a_run_with_traces_switched_off_was_never_traced_rather_than_showing_nothing()
    {
        using var studio = new StudioHost(tracing: false);

        await studio.Push(SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal("thin", answer.Depth);
        Assert.Equal("telemetryOff", answer.Traces.Kind);
        Assert.NotNull(answer.Traces.Missing);
    }

    [Fact]
    public async Task Tells_two_agents_apart_when_both_ran_in_one_session()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:10.000Z", "Bash", 4_000, use: "toolu_01"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:11.000Z", "Bash", 4_000, use: "toolu_02"));

        // Claude Code gives each Subagent an agent id of its own, so two that ran in one Session never merge.
        await studio.PushSpans(
            Morning,
            MainTrace,
            Ran(ToolSpan, "toolu_01", "agent-a"),
            Ran(TurnSpan, "toolu_02", "agent-b"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(["agent-a", "agent-b"], answer.Steps.Select(step => answer.Agents[step.Id]));
    }

    [Fact]
    public async Task Keeps_the_tool_call_that_started_a_subagent_on_the_main_thread()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.ToolRan(Morning, "2026-09-14T09:00:10.000Z", "Agent", 4_000, use: "toolu_01"));

        // Every Span beneath a Subagent carries its agent id, and the one that ran the Subagent repeats
        // the tool use id of the call that started it, which belongs to the caller and not to the Subagent.
        await studio.PushSpans(
            Morning,
            MainTrace,
            Ran(ToolSpan, "toolu_01", null),
            Beneath(TurnSpan, ToolSpan, "toolu_01", "agent-a"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal("full", answer.Depth);
        Assert.False(answer.Agents.ContainsKey(Assert.Single(answer.Steps).Id));
    }

    private static async Task SubagentRan(StudioHost studio)
    {
        await studio.Push(SessionEvent.ToolRan(Morning, "2026-09-14T09:00:10.000Z", "Bash", 4_000, use: "toolu_01"));
        await studio.PushSpans(Morning, MainTrace, Ran(ToolSpan, "toolu_01", "agent-a"));
    }

    private static RecordedSpan Ran(string id, string toolUse, string? agent) =>
        new("claude_code.tool", "2026-09-14T09:00:06Z", "2026-09-14T09:00:10Z", id, Agent: agent, ToolUse: toolUse);

    private static RecordedSpan Asked(string id, string request, string? agent) =>
        new("claude_code.llm_request", "2026-09-14T09:00:18Z", "2026-09-14T09:00:20Z", id, Agent: agent, Request: request);

    private static RecordedSpan Beneath(string id, string parent, string toolUse, string agent) =>
        new("claude_code.tool.execution", "2026-09-14T09:00:07Z", "2026-09-14T09:00:09Z", id, parent, agent, toolUse);
}
