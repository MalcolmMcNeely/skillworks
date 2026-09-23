using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // Only the read of Parents before the span asks for several runs by name at once.
    private const string ParentBeforeSpanRead = "session_id=~";

    [Fact]
    public async Task Keeps_a_parents_row_for_a_skill_only_a_child_activated()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });
        await studio.Push(new SkillActivated("implement", At(Yesterday, "09:06:00.000")) { Session = Afternoon });

        var session = Assert.Single(await studio.SessionsIn("?skill=implement"));

        Assert.Equal(Morning, session.Id);
        Assert.Equal("The spec run", session.Name);
    }

    [Fact]
    public async Task Keeps_a_parents_row_for_a_repository_only_a_child_ran_in()
    {
        using var studio = new StudioHost();

        await studio.Push(
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

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });
        await studio.PushSpans(Afternoon, AfternoonTrace, Traced(AfternoonSpan));

        // The store reads the Batch a Span arrived in, and these arrived now, so the days asked for reach today.
        var session = Assert.Single(await studio.SessionsIn($"?from={Written(Yesterday)}&to={Written(Today)}&depth=full"));

        Assert.Equal(Morning, session.Id);
    }

    [Fact]
    public async Task Shows_a_parent_that_started_before_the_span_through_a_child_inside_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(2), "22:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:00:00.000"), "The build step") with { Parent = Morning });

        var session = Assert.Single(await studio.SessionsIn($"?from={Written(Yesterday)}&to={Written(Yesterday)}"));

        Assert.Equal(Morning, session.Id);
        Assert.Equal("The spec run", session.Name);
        Assert.Equal(Moment(At(DaysBack(2), "22:00:00.000")), session.StartedUtc);
    }

    [Fact]
    public async Task Empties_the_table_when_the_read_of_a_parent_before_the_span_fell_short()
    {
        using var events = Breaking(ParentBeforeSpanRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(2), "22:00:00.000"), "The spec run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:00:00.000"), "The build step") with { Parent = Morning });

        var answer = await studio.SessionAnswer($"?from={Written(Yesterday)}&to={Written(Yesterday)}");

        // Without it the Child would stand as a row of its own, which is a half-folded table.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    [Fact]
    public async Task Drops_a_parents_row_that_neither_it_nor_a_child_matches_and_leaves_a_session_with_no_parent_as_before()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The spec run", "acme/nu"),
            Ran(Afternoon, At(Yesterday, "09:05:00.000"), "The build step", "acme/nu") with { Parent = Morning },
            Ran(Evening, At(Yesterday, "14:00:00.000"), "The chat", "acme/xi"));

        Assert.Equal(["The chat"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }
}
