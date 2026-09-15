namespace Skillworks.Core.Filters;

// Days are UTC days, as Claude Code timestamps its events; a local day would move late sessions to the wrong day.
public sealed record Filter
{
    public DateOnly? From { get; init; }

    public DateOnly? To { get; init; }

    // Matched exactly: a near miss is a repository the reader has not got, and an empty answer says so.
    public string? Repository { get; init; }

    public string? Skill { get; init; }

    // Skill is left out: it only picks which skills are listed, and a never-fired one still belongs there.
    public bool AsksWhatHappened => From is not null || To is not null || Repository is not null;

    public DateTimeOffset? FromUtc => From is { } day ? DaySpan.StartOf(day) : null;

    public DateTimeOffset? UntilUtc => To is { } day ? DaySpan.EndOf(day) : null;

    public bool Covers(string skill) => Skill is null || Skill == skill;

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
