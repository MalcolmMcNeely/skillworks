using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Answers;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Counts_every_tool_call_a_session_made()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The thrashing run"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:02:00.000")),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:03:00.000")));

        // A call that failed still ran, so it is one of the calls a run that thrashed made.
        Assert.Equal(3m, (await studio.SessionAnswer()).Measured("toolCalls", Morning));
    }

    [Fact]
    public async Task Adds_up_what_a_session_cost()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The expensive run"));
        await studio.Push(
            new ApiRequest(At(Yesterday, "09:01:00.000"), CostUsd: 0.25m) { Session = Morning },
            new ApiRequest(At(Yesterday, "09:02:00.000"), CostUsd: 0.75m) { Session = Morning });

        Assert.Equal(1m, (await studio.SessionAnswer()).Measured("cost", Morning));
    }

    [Fact]
    public async Task Counts_a_tool_call_that_failed_as_a_fault()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The broken run"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:02:00.000")),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:03:00.000")));

        Assert.Equal(2m, (await studio.SessionAnswer()).Measured("faults", Morning));
    }

    [Fact]
    public async Task Counts_a_model_error_as_a_fault()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run the model failed"),
            SessionEvent.ModelFailed(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:02:00.000")));

        // Nobody chose either one, and that is what puts them in the same count.
        Assert.Equal(2m, (await studio.SessionAnswer()).Measured("faults", Morning));
    }

    [Fact]
    public async Task Counts_a_tool_call_a_person_refused_as_friction()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run I said no to"),
            SessionEvent.Refused(Morning, At(Yesterday, "09:01:00.000")));

        Assert.Equal((0m, 1m), FaultsAndFriction(await studio.SessionAnswer(), Morning));
    }

    [Fact]
    public async Task Counts_a_tool_call_a_hook_blocked_as_friction()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run the hook stopped"),
            SessionEvent.HookBlocked(Morning, At(Yesterday, "09:01:00.000")));

        Assert.Equal((0m, 1m), FaultsAndFriction(await studio.SessionAnswer(), Morning));
    }

    [Fact]
    public async Task Shows_no_faults_for_a_session_that_met_only_refusals_and_hook_blocks()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The careful run"),
            SessionEvent.Refused(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.HookBlocked(Morning, At(Yesterday, "09:02:00.000")),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:03:00.000")));

        // A reader's own refusals must never make a clean run look broken.
        Assert.Equal((0m, 2m), FaultsAndFriction(await studio.SessionAnswer(), Morning));
    }

    [Fact]
    public async Task Leaves_a_tool_call_that_was_allowed_out_of_friction()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The smooth run"),
            SessionEvent.Allowed(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:02:00.000")));

        Assert.Equal(0m, (await studio.SessionAnswer()).Measured("friction", Morning));
    }

    [Fact]
    public async Task Counts_each_session_apart_from_the_others()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The early run"),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The later run"),
            SessionEvent.ToolRan(Afternoon, At(Yesterday, "14:01:00.000")),
            SessionEvent.Refused(Afternoon, At(Yesterday, "14:02:00.000")));

        var answer = await studio.SessionAnswer();

        Assert.Equal((1m, 1m, 0m), Counts(answer, Morning));
        Assert.Equal((1m, 0m, 1m), Counts(answer, Afternoon));
    }

    [Fact]
    public async Task Reports_nothing_counted_as_zero_for_a_session_that_only_talked()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var answer = await studio.SessionAnswer();

        Assert.Equal((0m, 0m, 0m), Counts(answer, Morning));
        Assert.Equal(0m, answer.Measured("cost", Morning));
    }

    private static (decimal ToolCalls, decimal Faults, decimal Friction) Counts(SessionsAnswer answer, string id) =>
        (answer.Measured("toolCalls", id), answer.Measured("faults", id), answer.Measured("friction", id));

    private static (decimal Faults, decimal Friction) FaultsAndFriction(SessionsAnswer answer, string id) =>
        (answer.Measured("faults", id), answer.Measured("friction", id));
}
