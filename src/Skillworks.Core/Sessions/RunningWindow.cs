namespace Skillworks.Core.Sessions;

// No event says a Session ended, so one window decides Running everywhere.
public static class RunningWindow
{
    // Long enough to carry a person reading an answer, short enough that yesterday's run never reads as live.
    public static readonly TimeSpan Length = TimeSpan.FromMinutes(15);

    public static bool Covers(DateTimeOffset lastEvent, DateTimeOffset now) => now - lastEvent < Length;
}
