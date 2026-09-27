using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string CostTrace = "7a1c0a9e0000400080000000000000d4";

    [Fact]
    public async Task Sets_apart_the_part_of_an_exchanges_cost_each_subagent_spent()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 1_000, 0.10m, request: "req_01"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:08.000"), 1_000, 0.30m, request: "req_02"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:09.000"), 1_000, 0.20m, request: "req_03"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:10.000"), 1_000, 0.05m, request: "req_04"));

        await studio.PushSpans(
            Morning,
            CostTrace,
            Asked("d11c0a9e00000002", "req_02", "agent-a"),
            Asked("d11c0a9e00000003", "req_03", "agent-a"),
            Asked("d11c0a9e00000004", "req_04", "agent-b"));

        var said = Assert.Single(await studio.ExchangesIn(Morning));

        // The Subagents' Turns already sit inside the Exchange's Cost, so their part is set apart and never added.
        Assert.Equal(0.65m, said.Cost);
        Assert.Equal(["agent-a", "agent-b"], said.Subagents!.Select(each => each.Agent));
        Assert.Equal([0.50m, 0.05m], said.Subagents!.Select(each => each.Cost));
    }

    [Fact]
    public async Task Sets_no_subagent_part_apart_in_an_exchange_the_main_agent_ran_alone()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 1_000, 0.10m, request: "req_01"));

        await studio.PushSpans(Morning, CostTrace, Asked("d11c0a9e00000001", "req_01", null));

        Assert.Empty(Assert.Single(await studio.ExchangesIn(Morning)).Subagents!);
    }

    [Fact]
    public async Task Leaves_the_subagent_part_unknown_in_a_run_with_no_spans()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 1_000, 0.10m, request: "req_01"));

        // Only a Span names the agent that ran a Turn, so none can be set apart, and none is not the same as zero.
        Assert.Null(Assert.Single(await studio.ExchangesIn(Morning)).Subagents);
    }

    [Fact]
    public async Task Reports_the_cost_of_the_turns_before_the_first_prompt()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "08:59:50.000"), 1_000, 0.02m),
            SessionEvent.Turned(Morning, At(Yesterday, "08:59:55.000"), 1_000, 0.03m),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 1_000, 0.10m));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(0.05m, answer.BeforeFirstPrompt);
        Assert.Equal(0.10m, Assert.Single(answer.Exchanges).Cost);
    }

    [Fact]
    public async Task Adds_the_exchange_costs_and_the_turns_before_the_first_prompt_up_to_the_sessions_cost()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "08:59:50.000"), 1_000, 0.02m),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 1_000, 0.10m, request: "req_01"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:08.000"), 1_000, 0.30m, request: "req_02"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:09.000"), 1_000, 0.01m, source: "generate_session_title"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:20.000"), "Built."),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:05:00.000"), "Now the docs"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:05:05.000"), 1_000, 0.07m, request: "req_03"));

        await studio.PushSpans(Morning, CostTrace, Asked("d11c0a9e00000002", "req_02", "agent-a"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(0.50m, answer.Run!.Cost);
        Assert.Equal(answer.Run.Cost, answer.Exchanges.Sum(each => each.Cost) + answer.BeforeFirstPrompt);
    }

    [Fact]
    public async Task Reports_no_cost_before_the_first_prompt_when_a_prompt_came_first()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 1_000, 0.10m));

        Assert.Equal(0m, (await studio.StepAnswer(Morning)).BeforeFirstPrompt);
    }
}
