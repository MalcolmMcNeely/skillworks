using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Keeps_a_parents_row_for_a_skill_only_a_child_activated()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });
        await studio.Push(new SkillActivated("implement", At(Yesterday, "09:06:00.000")) { Session = Afternoon, Parent = Morning });

        var session = Assert.Single(await studio.SessionsIn("?skill=implement"));

        Assert.Equal(Morning, session.Id);
        Assert.Equal("The spec run", session.Name);
    }

    [Fact]
    public async Task Keeps_a_parents_row_for_a_repository_only_a_child_ran_in()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The spec run", "acme/nu"),
            Ran(Afternoon, At(Yesterday, "09:05:00.000"), "The build step", "acme/xi") with { Parent = Morning });

        var session = Assert.Single(await studio.SessionsIn("?repository=acme/xi"));

        Assert.Equal(Morning, session.Id);
        Assert.Equal("The spec run", session.Name);
    }

    [Fact]
    public async Task Keeps_a_parents_row_for_a_depth_only_a_child_matches()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });
        await studio.PushSpans(Afternoon, AfternoonTrace, Traced(AfternoonSpan));

        var session = Assert.Single(await studio.SessionsIn("?depth=full"));

        Assert.Equal(Morning, session.Id);
    }

    [Fact]
    public async Task Empties_the_table_when_the_read_of_whether_a_parent_left_events_fell_short()
    {
        // Only that read counts every event of a run by its Session alone.
        using var events = BrokenEventsStore.DownOn(asked =>
            asked.StartsWith("sum by (session_id) (count_over_time(", StringComparison.Ordinal) &&
            asked.Contains("|= \"claude_code.\" |", StringComparison.Ordinal));
        using var studio = new StudioHost(events: events);

        await PushWithPrompts(
            studio,
            new SessionEvent(Morning, "tool_result", At(DaysBack(2), "22:00:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:00:00.000"), "The build step") with { Parent = Morning });

        var answer = await studio.SessionAnswer();

        // Without it the Child would stand as a row of its own, which is a half-folded table.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    [Fact]
    public async Task Drops_a_parents_row_that_neither_it_nor_a_child_matches_and_leaves_a_session_with_no_parent_as_before()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The spec run", "acme/nu"),
            Ran(Afternoon, At(Yesterday, "09:05:00.000"), "The build step", "acme/nu") with { Parent = Morning },
            Ran(Evening, At(Yesterday, "14:00:00.000"), "The chat", "acme/xi"));

        Assert.Equal(["The chat"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }
}
