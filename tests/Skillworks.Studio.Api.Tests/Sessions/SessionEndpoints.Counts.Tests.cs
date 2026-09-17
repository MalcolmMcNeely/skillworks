using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Answers;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Counts_every_tool_call_a_session_made()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The thrashing run"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:01:00.000Z"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:02:00.000Z"),
            SessionEvent.ToolFailed(Morning, "2026-09-14T09:03:00.000Z"));

        // A call that failed still ran, so it is one of the calls a run that thrashed made.
        Assert.Equal(3, Assert.Single(await studio.SessionsIn()).ToolCalls);
    }

    [Fact]
    public async Task Adds_up_what_a_session_cost()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The expensive run"));
        await studio.Push(
            new ApiRequest("2026-09-14T09:01:00.000Z", CostUsd: 0.25m) { Session = Morning },
            new ApiRequest("2026-09-14T09:02:00.000Z", CostUsd: 0.75m) { Session = Morning });

        Assert.Equal(1m, Assert.Single(await studio.SessionsIn()).Cost);
    }

    [Fact]
    public async Task Counts_a_tool_call_that_failed_as_a_fault()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The broken run"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:01:00.000Z"),
            SessionEvent.ToolFailed(Morning, "2026-09-14T09:02:00.000Z"),
            SessionEvent.ToolFailed(Morning, "2026-09-14T09:03:00.000Z"));

        Assert.Equal(2, Assert.Single(await studio.SessionsIn()).Faults);
    }

    [Fact]
    public async Task Counts_a_model_error_as_a_fault()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run the model failed"),
            SessionEvent.ModelFailed(Morning, "2026-09-14T09:01:00.000Z"),
            SessionEvent.ToolFailed(Morning, "2026-09-14T09:02:00.000Z"));

        // Nobody chose either one, and that is what puts them in the same count.
        Assert.Equal(2, Assert.Single(await studio.SessionsIn()).Faults);
    }

    [Fact]
    public async Task Counts_a_tool_call_a_person_refused_as_friction()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run I said no to"),
            SessionEvent.Refused(Morning, "2026-09-14T09:01:00.000Z"));

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(1, session.Friction);
        Assert.Equal(0, session.Faults);
    }

    [Fact]
    public async Task Counts_a_tool_call_a_hook_blocked_as_friction()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run the hook stopped"),
            SessionEvent.HookBlocked(Morning, "2026-09-14T09:01:00.000Z"));

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(1, session.Friction);
        Assert.Equal(0, session.Faults);
    }

    [Fact]
    public async Task Shows_no_faults_for_a_session_that_met_only_refusals_and_hook_blocks()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The careful run"),
            SessionEvent.Refused(Morning, "2026-09-14T09:01:00.000Z"),
            SessionEvent.HookBlocked(Morning, "2026-09-14T09:02:00.000Z"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:03:00.000Z"));

        var session = Assert.Single(await studio.SessionsIn());

        // A reader's own refusals must never make a clean run look broken.
        Assert.Equal(0, session.Faults);
        Assert.Equal(2, session.Friction);
    }

    [Fact]
    public async Task Leaves_a_tool_call_that_was_allowed_out_of_friction()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The smooth run"),
            SessionEvent.Allowed(Morning, "2026-09-14T09:01:00.000Z"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:02:00.000Z"));

        Assert.Equal(0, Assert.Single(await studio.SessionsIn()).Friction);
    }

    [Fact]
    public async Task Counts_each_session_apart_from_the_others()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The early run"),
            SessionEvent.ToolFailed(Morning, "2026-09-14T09:01:00.000Z"),
            SessionEvent.Titled(Afternoon, "2026-09-14T14:00:00.000Z", "The later run"),
            SessionEvent.ToolRan(Afternoon, "2026-09-14T14:01:00.000Z"),
            SessionEvent.Refused(Afternoon, "2026-09-14T14:02:00.000Z"));

        var sessions = (await studio.SessionsIn()).ToDictionary(session => session.Name);

        Assert.Equal((1, 1, 0), Counts(sessions["The early run"]));
        Assert.Equal((1, 0, 1), Counts(sessions["The later run"]));
    }

    [Fact]
    public async Task Reports_nothing_counted_as_zero_for_a_session_that_only_talked()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"));

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal((0, 0, 0), Counts(session));
        Assert.Equal(0m, session.Cost);
    }

    private static (int ToolCalls, int Faults, int Friction) Counts(SessionRow session) =>
        (session.ToolCalls, session.Faults, session.Friction);
}
