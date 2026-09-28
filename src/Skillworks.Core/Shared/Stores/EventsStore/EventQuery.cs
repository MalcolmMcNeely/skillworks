namespace Skillworks.Core.Shared.Stores.EventsStore;

// Every event Claude Code sends carries these attributes, so one narrowing serves them all.
public sealed record EventQuery(string EventName, DateTimeOffset From, DateTimeOffset Until)
{
    // The body of every event is claude_code. then its name, so the bare stem matches all of them.
    public const string AnyEvent = "";

    // Narrows on top of EventName, so a read of several events leaves EventName at AnyEvent.
    public IReadOnlyCollection<string>? AnyOfEvents { get; init; }

    public string? Repository { get; init; }

    public string? Session { get; init; }

    public IReadOnlyCollection<string>? Sessions { get; init; }

    // Only a Child's events pass, so a Parent's own events are asked for by Sessions.
    public IReadOnlyCollection<string>? Parents { get; init; }

    public string? Skill { get; init; }

    public string? QuerySource { get; init; }

    public bool NamesParent { get; init; }
}
