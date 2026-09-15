namespace Skillworks.Studio.Api.Tests.Harness;

// Studio reads back from today and the tests' events have fixed dates; it still ticks, so timeouts still fire.
public sealed class PinnedClock : TimeProvider
{
    public static readonly DateTimeOffset Today = new(2026, 9, 15, 12, 0, 0, TimeSpan.Zero);

    private readonly long _started;

    public PinnedClock() => _started = GetTimestamp();

    public override DateTimeOffset GetUtcNow() => Today + GetElapsedTime(_started);
}
