namespace Skillworks.Core.EventsStore;

public sealed record EventReading(IReadOnlyList<TelemetryEvent> Events, string? Unreachable, bool Truncated = false)
{
    public static EventReading Of(IReadOnlyList<TelemetryEvent> events, bool truncated) =>
        new(events, null, truncated);

    public static EventReading Failed(string reason) => new([], reason);
}
