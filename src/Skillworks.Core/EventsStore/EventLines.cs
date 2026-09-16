namespace Skillworks.Core.EventsStore;

public sealed record EventLines(IReadOnlyList<EventLine> Lines, string? Unreachable)
{
    public static EventLines Of(IReadOnlyList<EventLine> lines) => new(lines, null);

    public static EventLines Failed(string reason) => new([], reason);
}
