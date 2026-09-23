using Skillworks.Core.Sessions;
using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Answers;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // Only the read that finds Parents names the key, so no other read of the answer is spelled this way.
    private const string ParentRead = "skillworks_parent_session_id";

    private const string AbsentParent ="8f1c0a9e-0000-4000-8000-000000000009";

    [Fact]
    public async Task Folds_two_children_into_their_parents_row()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning },
            SessionEvent.Titled(Evening, At(Yesterday, "09:10:00.000"), "The review step") with { Parent = Morning });

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(Morning, session.Id);
        Assert.Equal("The spec run", session.Name);
        Assert.Equal(Moment(At(Yesterday, "09:00:00.000")), session.StartedUtc);
    }

    [Fact]
    public async Task Runs_a_parents_length_to_the_last_event_of_a_child_that_ended_after_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            new SessionEvent(Morning, "tool_result", At(Yesterday, "09:10:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning },
            new SessionEvent(Afternoon, "tool_result", At(Yesterday, "09:50:00.000")) { Parent = Morning });

        // A Parent sits idle while its Children work, so its own events alone would read as finished early.
        Assert.Equal((long)TimeSpan.FromMinutes(50).TotalMilliseconds, Assert.Single(await studio.SessionsIn()).LengthMs);
    }

    [Fact]
    public async Task Marks_a_parent_running_while_only_a_child_is_running()
    {
        using var studio = new StudioHost();

        var recent = Now - RunningWindow.Length + TimeSpan.FromMinutes(1);
        var old = Now - RunningWindow.Length - TimeSpan.FromMinutes(30);

        await studio.Push(
            SessionEvent.Titled(Morning, Stamped(old), "The spec run"),
            new SessionEvent(Afternoon, "tool_result", Stamped(old)) { Parent = Morning },
            new SessionEvent(Afternoon, "tool_result", Stamped(recent)) { Parent = Morning });

        Assert.True(Assert.Single(await studio.SessionsIn()).Running);
    }

    [Fact]
    public async Task Marks_a_parent_running_while_only_the_parent_is_running()
    {
        using var studio = new StudioHost();

        var recent = Now - RunningWindow.Length + TimeSpan.FromMinutes(1);
        var old = Now - RunningWindow.Length - TimeSpan.FromMinutes(30);

        await studio.Push(
            SessionEvent.Titled(Morning, Stamped(old), "The spec run"),
            new SessionEvent(Morning, "tool_result", Stamped(recent)),
            new SessionEvent(Afternoon, "tool_result", Stamped(old)) { Parent = Morning });

        Assert.True(Assert.Single(await studio.SessionsIn()).Running);
    }

    [Fact]
    public async Task Lists_a_child_whose_parent_left_no_events_as_its_own_row()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = AbsentParent });

        // Folding into a row that does not exist would lose the work altogether.
        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(Afternoon, session.Id);
        Assert.Equal("The build step", session.Name);
    }

    [Fact]
    public async Task Leaves_a_session_that_names_no_parent_as_its_own_row_beside_a_parent()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            new SessionEvent(Morning, "tool_result", At(Yesterday, "09:30:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning },
            SessionEvent.Titled(Evening, At(Yesterday, "14:00:00.000"), "The chat"),
            new SessionEvent(Evening, "tool_result", At(Yesterday, "14:20:00.000")));

        var sessions = await studio.SessionsIn();

        Assert.Equal(["The chat", "The spec run"], sessions.Select(session => session.Name));
        Assert.Equal(
            (long)TimeSpan.FromMinutes(20).TotalMilliseconds,
            sessions.Single(session => session.Id == Evening).LengthMs);
    }

    [Fact]
    public async Task Empties_the_table_when_the_read_that_finds_parents_fell_short()
    {
        using var events = Breaking(ParentRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });

        var answer = await studio.SessionAnswer();

        // Without it a Child would stand as a row of its own, which is a half-folded table.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    [Fact]
    public async Task Draws_the_folded_rows_while_a_measure_read_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });

        var lines = await studio.SessionLines(count: 2);

        Assert.Equal(["head", "sessions"], lines.Select(StudioHost.KindOf));
        Assert.Equal(["The spec run"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        await StillOut(events, TurnRead);
    }
}
