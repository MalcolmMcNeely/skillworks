using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // Over Loki's default read of 100 lines, so a table read event by event would show the wrong length.
    private const int MoreEventsThanOneReadHolds = 400;

    [Fact]
    public async Task Measures_a_busy_session_from_totals_rather_than_from_a_list_of_its_events()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The busy run"));
        await studio.Push(
            SessionEvent.Every(Morning, At(Yesterday, "09:00:00.000"), TimeSpan.FromSeconds(3), MoreEventsThanOneReadHolds));

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(
            (long)(TimeSpan.FromSeconds(3) * (MoreEventsThanOneReadHolds - 1)).TotalMilliseconds,
            session.LengthMs);
    }
}
