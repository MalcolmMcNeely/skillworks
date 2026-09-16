using Skillworks.Core.Sessions;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Marks_a_session_running_while_its_last_event_is_recent()
    {
        using var studio = new StudioHost();

        var lastEvent = PinnedClock.Today - RunningWindow.Length + TimeSpan.FromMinutes(1);

        await studio.Push(
            SessionEvent.Titled(Morning, At(lastEvent - TimeSpan.FromMinutes(10)), "The run in hand"),
            new SessionEvent(Morning, "tool_result", At(lastEvent)));

        // No event says a Session ended, so a recent last event is all Studio has to go on.
        Assert.True(Assert.Single(await studio.SessionsIn()).Running);
    }

    [Fact]
    public async Task Leaves_a_session_whose_last_event_is_old_unmarked()
    {
        using var studio = new StudioHost();

        var lastEvent = PinnedClock.Today - RunningWindow.Length - TimeSpan.FromMinutes(1);

        await studio.Push(
            SessionEvent.Titled(Morning, At(lastEvent - TimeSpan.FromMinutes(10)), "The finished run"),
            new SessionEvent(Morning, "tool_result", At(lastEvent)));

        // A finished run must never read as Running, nor a half-finished one as finished.
        Assert.False(Assert.Single(await studio.SessionsIn()).Running);
    }

    private static string At(DateTimeOffset moment) =>
        moment.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", System.Globalization.CultureInfo.InvariantCulture);
}
