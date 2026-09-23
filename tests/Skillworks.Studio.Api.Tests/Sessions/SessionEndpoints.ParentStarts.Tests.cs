using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Answers;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Starts_a_parent_that_also_speaks_inside_the_span_at_its_first_event_before_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(2), "22:00:00.000"), "The spec run"),
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run, later"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });

        var session = Assert.Single(await studio.SessionsIn($"?from={Written(Yesterday)}&to={Written(Yesterday)}"));

        Assert.Equal(Morning, session.Id);
        Assert.Equal(Moment(At(DaysBack(2), "22:00:00.000")), session.StartedUtc);
        Assert.Equal("The spec run", session.Name);
    }

    [Fact]
    public async Task Runs_a_parents_length_from_its_first_event_before_the_span_to_the_last_event_of_a_child()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(2), "22:00:00.000"), "The spec run"),
            new SessionEvent(Morning, "tool_result", At(Yesterday, "09:00:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning },
            new SessionEvent(Afternoon, "tool_result", At(Yesterday, "09:30:00.000")) { Parent = Morning });

        var session = Assert.Single(await studio.SessionsIn($"?from={Written(Yesterday)}&to={Written(Yesterday)}"));

        Assert.Equal((long)TimeSpan.FromHours(11.5).TotalMilliseconds, session.LengthMs);
    }

    [Fact]
    public async Task Starts_a_session_that_names_no_parent_at_its_first_event_inside_the_span_beside_a_parent()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(2), "22:00:00.000"), "The spec run"),
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run, later"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning },
            SessionEvent.Titled(Evening, At(DaysBack(2), "23:00:00.000"), "The chat"),
            SessionEvent.Titled(Evening, At(Yesterday, "14:00:00.000"), "The chat, later"),
            new SessionEvent(Evening, "tool_result", At(Yesterday, "14:20:00.000")));

        var sessions = await studio.SessionsIn($"?from={Written(Yesterday)}&to={Written(Yesterday)}");
        var chat = sessions.Single(session => session.Id == Evening);

        Assert.Equal(Moment(At(Yesterday, "14:00:00.000")), chat.StartedUtc);
        Assert.Equal("The chat, later", chat.Name);
        Assert.Equal((long)TimeSpan.FromMinutes(20).TotalMilliseconds, chat.LengthMs);
    }

    [Fact]
    public async Task Draws_a_parents_row_with_its_start_before_the_span_while_a_measure_read_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(2), "22:00:00.000"), "The spec run"),
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run, later"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });

        var lines = await studio.SessionLines($"?from={Written(Yesterday)}&to={Written(Yesterday)}", count: 2);

        Assert.Equal(["head", "sessions"], lines.Select(StudioHost.KindOf));
        Assert.Equal(
            [Moment(At(DaysBack(2), "22:00:00.000"))],
            SessionsAnswer.RowsIn(lines).Select(row => row.StartedUtc));

        await StillOut(events, TurnRead);
    }
}
