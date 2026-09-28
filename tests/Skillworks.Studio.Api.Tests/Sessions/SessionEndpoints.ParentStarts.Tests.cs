using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Answers;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Starts_a_parent_that_began_before_the_prompt_that_placed_it_at_its_first_event()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            new SessionEvent(Morning, "tool_result", At(DaysBack(2), "22:00:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:00:00.000"), "The build step") with { Parent = Morning },
            new SessionEvent(Afternoon, "tool_result", At(Yesterday, "09:30:00.000")) { Parent = Morning });

        var session = Assert.Single(await studio.SessionsIn());

        // The Parent spoke only before its Child's Prompt, and a row that began there would read eleven hours short.
        Assert.Equal(Morning, session.Id);
        Assert.Equal(Moment(At(DaysBack(2), "22:00:00.000")), session.StartedUtc);
        Assert.Equal((long)TimeSpan.FromHours(11.5).TotalMilliseconds, session.LengthMs);
        Assert.Equal((DaysBack(2), Yesterday), (session.FirstDay, session.LastDay));
    }

    [Fact]
    public async Task Draws_a_parents_row_with_its_true_start_while_a_measure_read_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await PushWithPrompts(
            studio,
            new SessionEvent(Morning, "tool_result", At(DaysBack(2), "22:00:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });

        var lines = await studio.SessionLines(count: 2, closeAfter: events.HoldingRead);

        Assert.Equal(["head", "sessions"], lines.Select(StudioHost.KindOf));
        Assert.Equal(
            [Moment(At(DaysBack(2), "22:00:00.000"))],
            SessionsAnswer.RowsIn(lines).Select(row => row.StartedUtc));

        await StillOut(events, TurnRead);
    }
}
