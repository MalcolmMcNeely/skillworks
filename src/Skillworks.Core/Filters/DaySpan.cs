namespace Skillworks.Core.Filters;

public sealed record DaySpan(DateOnly From, DateOnly To, bool Lookback)
{
    public DateTimeOffset FromUtc => StartOf(From);

    public DateTimeOffset UntilUtc => EndOf(To);

    // A method, not a property, so the days are not written into every span on the wire.
    public IReadOnlyList<DateOnly> NewestFirst() =>
        [.. Enumerable.Range(0, Math.Max(0, To.DayNumber - From.DayNumber + 1)).Select(back => To.AddDays(-back))];

    public static DaySpan Of(DateOnly day) => new(day, day, Lookback: false);

    internal static DateTimeOffset StartOf(DateOnly day) => new(day.ToDateTime(TimeOnly.MinValue), TimeSpan.Zero);

    // The next midnight, so the day is taken in whole and a session run that evening is not dropped.
    internal static DateTimeOffset EndOf(DateOnly day) => StartOf(day.AddDays(1));
}
