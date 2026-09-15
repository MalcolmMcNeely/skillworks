namespace Skillworks.Core.EventsStore;

// Every event Claude Code sends carries these attributes, so one narrowing serves them all.
public sealed record EventQuery(string EventName, DateTimeOffset From, DateTimeOffset Until)
{
    public string? Repository { get; init; }

    public string? Skill { get; init; }

    public string? Session { get; init; }

    public string? Sequence { get; init; }
}
