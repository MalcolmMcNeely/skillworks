namespace Skillworks.Core.EventsStore;

// Every event Claude Code sends carries these attributes, so one narrowing serves them all.
public sealed record EventQuery(string EventName, DateTimeOffset From, DateTimeOffset Until)
{
    // The body of every event is claude_code. then its name, so the bare stem matches all of them.
    public const string AnyEvent = "";

    public string? Repository { get; init; }

    public string? Session { get; init; }

    public string? Skill { get; init; }

    public string? QuerySource { get; init; }
}
