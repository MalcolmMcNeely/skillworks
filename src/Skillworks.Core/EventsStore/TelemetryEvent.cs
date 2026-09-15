namespace Skillworks.Core.EventsStore;

public sealed class TelemetryEvent(DateTimeOffset at, IReadOnlyDictionary<string, string> labels)
{
    public DateTimeOffset At => at;

    public string? Repository =>
        EventAttributes.RepositoryOf(Attribute(EventAttributes.Owner), Attribute(EventAttributes.RepositoryName));

    // Takes Claude Code's dotted name, so no caller has to know Loki's underscores.
    public string? Attribute(string name) => labels.GetValueOrDefault(EventAttributes.LabelOf(name));
}
