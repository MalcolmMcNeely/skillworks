namespace Skillworks.Core.EventsStore;

public sealed class EventCount(IReadOnlyDictionary<string, string> labels, long count)
{
    public long Count => count;

    public string? Repository =>
        EventAttributes.RepositoryOf(Attribute(EventAttributes.Owner), Attribute(EventAttributes.RepositoryName));

    public string? Attribute(string name) => labels.GetValueOrDefault(EventAttributes.LabelOf(name));
}
