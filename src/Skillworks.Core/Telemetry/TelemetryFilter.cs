namespace Skillworks.Core.Telemetry;

/// <summary>
/// The one way every list narrows: a span of days, a repository and a skill. It is the same set on
/// every endpoint, so asking about last week in one project is learned once and asked everywhere.
/// </summary>
/// <remarks>
/// The ends are days rather than instants, because a span of days is the question a reader actually
/// asks, and both ends are taken in whole. A day is a UTC day, because that is what a transcript
/// timestamps, and reading it as a local one would move a late-night session into the wrong day.
/// </remarks>
public sealed record TelemetryFilter
{
    /// <summary>The first day taken in. Null asks from the beginning of the history.</summary>
    public DateOnly? From { get; init; }

    /// <summary>The last day taken in, whole. Null asks up to the newest thing read.</summary>
    public DateOnly? To { get; init; }

    /// <summary>
    /// Matched exactly as the choices offer it. A near miss is a repository the reader has not got,
    /// and an empty answer says so; matching it loosely would only have to guess which was meant.
    /// </summary>
    public string? Repository { get; init; }

    /// <summary>Matched exactly, as invoked. Null asks about every skill.</summary>
    public string? Skill { get; init; }

    /// <summary>
    /// True when the filter asks what happened somewhere or at some time, rather than only cutting
    /// the list of skills down. A skill that never fired has nothing to say to that question.
    /// </summary>
    public bool AsksWhatHappened => From is not null || To is not null || Repository is not null;

    /// <summary>The first instant taken in, or null when the answer runs from the beginning.</summary>
    public DateTimeOffset? FromUtc =>
        From is { } day ? new DateTimeOffset(day.ToDateTime(TimeOnly.MinValue), TimeSpan.Zero) : null;

    /// <summary>
    /// The first instant left out, so the whole of <see cref="To"/> is taken in. A range that
    /// stopped at midnight would drop a session that ran that evening, which nobody asked for.
    /// </summary>
    public DateTimeOffset? UntilUtc =>
        To is { } day ? new DateTimeOffset(day.AddDays(1).ToDateTime(TimeOnly.MinValue), TimeSpan.Zero) : null;

    /// <summary>Whether one skill name is in the answer at all.</summary>
    public bool Covers(string skill) => Skill is null || Skill == skill;
}
