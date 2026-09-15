namespace Skillworks.Core.Filters;

public sealed class Lookback(int days, TimeProvider clock)
{
    public DaySpan SpanOf(Filter filter) =>
        filter.Span(DateOnly.FromDateTime(clock.GetUtcNow().UtcDateTime), days);
}
