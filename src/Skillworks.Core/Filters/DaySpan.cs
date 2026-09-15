namespace Skillworks.Core.Filters;

public sealed record DaySpan(DateOnly From, DateOnly To, bool Lookback)
{
    public DateTimeOffset FromUtc => StartOf(From);

    public DateTimeOffset UntilUtc => EndOf(To);

    internal static DateTimeOffset StartOf(DateOnly day) => new(day.ToDateTime(TimeOnly.MinValue), TimeSpan.Zero);

    // The next midnight, so the day is taken in whole and a session run that evening is not dropped.
    internal static DateTimeOffset EndOf(DateOnly day) => StartOf(day.AddDays(1));
}
