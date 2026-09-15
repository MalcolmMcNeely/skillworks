namespace Skillworks.Core.EventsStore;

public sealed record EventCounts(IReadOnlyList<EventCount> Groups, string? Unreachable)
{
    public long Events => Groups.Sum(group => group.Count);

    public static EventCounts Of(IReadOnlyList<EventCount> groups) => new(groups, null);

    public static EventCounts Failed(string reason) => new([], reason);
}
