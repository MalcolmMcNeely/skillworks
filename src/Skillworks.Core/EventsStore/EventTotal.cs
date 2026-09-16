using System.Text.Json;

namespace Skillworks.Core.EventsStore;

public sealed class EventTotal(IReadOnlyDictionary<string, string> labels, decimal total, DateTimeOffset? startOfHour = null)
{
    public decimal Total => total;

    public DateTimeOffset? StartOfHour => startOfHour;

    public string? Repository =>
        EventAttributes.RepositoryOf(Attribute(EventAttributes.Owner), Attribute(EventAttributes.RepositoryName));

    // Serialized in key order, so the same labels from two queries make one key whatever characters they hold.
    private string Group =>
        JsonSerializer.Serialize(new { startOfHour, labels = labels.OrderBy(label => label.Key, StringComparer.Ordinal) });

    public string? Attribute(string name) => labels.GetValueOrDefault(EventAttributes.LabelOf(name));

    // A span totalled in several queries answers as one query would.
    internal static IReadOnlyList<EventTotal> Joined(
        IEnumerable<EventTotal> groups,
        Func<IEnumerable<decimal>, decimal> join) =>
    [
        .. groups
            .GroupBy(group => group.Group)
            .Select(same => same.First().Totalling(join(same.Select(group => group.Total))))
    ];

    private EventTotal Totalling(decimal sum) => new(labels, sum, startOfHour);
}
