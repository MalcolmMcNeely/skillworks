using System.Text.Json;

namespace Skillworks.Core.EventsStore;

public sealed class EventTotal(IReadOnlyDictionary<string, string> labels, decimal total)
{
    public decimal Total => total;

    public string? Repository =>
        EventAttributes.RepositoryOf(Attribute(EventAttributes.Owner), Attribute(EventAttributes.RepositoryName));

    // Serialized in key order, so the same labels from two queries make one key whatever characters they hold.
    private string Group => JsonSerializer.Serialize(labels.OrderBy(label => label.Key, StringComparer.Ordinal));

    public string? Attribute(string name) => labels.GetValueOrDefault(EventAttributes.LabelOf(name));

    // A span totalled in several queries answers as one query would.
    internal static IReadOnlyList<EventTotal> Joined(IEnumerable<EventTotal> groups) =>
    [
        .. groups
            .GroupBy(group => group.Group)
            .Select(same => same.First().Totalling(same.Sum(group => group.Total)))
    ];

    private EventTotal Totalling(decimal sum) => new(labels, sum);
}
