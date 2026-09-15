using System.Text.Json;

namespace Skillworks.Core.EventsStore;

public sealed class EventCount(IReadOnlyDictionary<string, string> labels, long count)
{
    public long Count => count;

    public string? Repository =>
        EventAttributes.RepositoryOf(Attribute(EventAttributes.Owner), Attribute(EventAttributes.RepositoryName));

    // Serialized in key order, so the same labels from two queries make one key whatever characters they hold.
    private string Group => JsonSerializer.Serialize(labels.OrderBy(label => label.Key, StringComparer.Ordinal));

    public string? Attribute(string name) => labels.GetValueOrDefault(EventAttributes.LabelOf(name));

    // A span counted in several queries answers as one query would.
    internal static IReadOnlyList<EventCount> Joined(IEnumerable<EventCount> groups) =>
    [
        .. groups
            .GroupBy(group => group.Group)
            .Select(same => same.First().Counting(same.Sum(group => group.Count)))
    ];

    private EventCount Counting(long total) => new(labels, total);
}
