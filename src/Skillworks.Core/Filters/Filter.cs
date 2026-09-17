namespace Skillworks.Core.Filters;

// Days are UTC days, as Claude Code timestamps its events; a local day would move late sessions to the wrong day.
public sealed record Filter
{
    public DateOnly? From { get; init; }

    public DateOnly? To { get; init; }

    // Matched exactly: a near miss is a repository the reader has not got, and an empty answer says so.
    public string? Repository { get; init; }

    public string? Skill { get; init; }

    // Text, not the word itself: a hand-typed address that misspells a Depth must still open a table.
    public string? Depth { get; init; }

    // Skill and Depth are left out: they pick which rows are listed, and a never-fired skill still belongs there.
    public bool AsksWhatHappened => From is not null || To is not null || Repository is not null;

    public DateTimeOffset? FromUtc => From is { } day ? DaySpan.StartOf(day) : null;

    public DateTimeOffset? UntilUtc => To is { } day ? DaySpan.EndOf(day) : null;

    public bool Covers(string skill) => Skill is null || Skill == skill;

    public bool NarrowsByDepth => AskedDepth is not null;

    public bool Covers(Depth depth) => AskedDepth is null || AskedDepth == depth;

    // A number would parse as a Depth nobody has, so only a name the enum really holds narrows anything.
    private Depth? AskedDepth =>
        Enum.TryParse<Depth>(Depth, ignoreCase: true, out var asked) && Enum.IsDefined(asked) ? asked : null;

    // With no span, the lookback, so a zero always has a period it is honest about.
    public DaySpan Span(DateOnly today, int lookbackDays)
    {
        var days = Math.Max(1, lookbackDays);

        if (From is null && To is null)
        {
            return new DaySpan(today.AddDays(1 - days), today, Lookback: true);
        }

        var to = To ?? today;

        return new DaySpan(From ?? to.AddDays(1 - days), to, Lookback: false);
    }
}
