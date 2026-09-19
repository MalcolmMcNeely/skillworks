using System.Text.Json;

namespace Skillworks.Core.Shared.Stores.EventsStore;

public sealed class EventLine(IReadOnlyDictionary<string, string> labels, DateTimeOffset at)
{
    public DateTimeOffset At => at;

    public string? Repository =>
        EventAttributes.RepositoryOf(Attribute(EventAttributes.Owner), Attribute(EventAttributes.RepositoryName));

    public string? Attribute(string name) => labels.GetValueOrDefault(EventAttributes.LabelOf(name));

    // A page overlaps the one before it by an instant, and Claude Code numbers every event of a run.
    internal string Key =>
        JsonSerializer.Serialize(new { at, labels = labels.OrderBy(label => label.Key, StringComparer.Ordinal) });
}
