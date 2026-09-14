namespace Skillworks.Core.Filters;

// Days are UTC days, as transcripts timestamp them; a local day would move late sessions to the wrong day.
public sealed record TelemetryFilter
{
    public DateOnly? From { get; init; }

    public DateOnly? To { get; init; }

    // Matched exactly: a near miss is a repository the reader has not got, and an empty answer says so.
    public string? Repository { get; init; }

    public string? Skill { get; init; }

    // Skill is left out: it only picks which skills are listed, and a never-fired one still belongs there.
    public bool AsksWhatHappened => From is not null || To is not null || Repository is not null;

    public DateTimeOffset? FromUtc =>
        From is { } day ? new DateTimeOffset(day.ToDateTime(TimeOnly.MinValue), TimeSpan.Zero) : null;

    // A day past To, so To is taken in whole and a session run that evening is not dropped.
    public DateTimeOffset? UntilUtc =>
        To is { } day ? new DateTimeOffset(day.AddDays(1).ToDateTime(TimeOnly.MinValue), TimeSpan.Zero) : null;

    public bool Covers(string skill) => Skill is null || Skill == skill;
}
