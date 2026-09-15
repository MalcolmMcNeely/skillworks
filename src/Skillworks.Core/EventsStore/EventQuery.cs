namespace Skillworks.Core.EventsStore;

// Every event Claude Code sends carries skill.name and the vcs attributes, so one narrowing serves them all.
public sealed record EventQuery(string EventName, DateTimeOffset From, DateTimeOffset Until)
{
    public string? Repository { get; init; }

    public string? Skill { get; init; }
}
