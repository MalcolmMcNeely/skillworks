namespace Skillworks.Studio.Api.Tests.Shared.Filters;

public sealed record SpanRow
{
    public required DateOnly From { get; init; }

    public required DateOnly To { get; init; }

    public required bool Lookback { get; init; }

    public required DateTimeOffset FromUtc { get; init; }

    public required DateTimeOffset UntilUtc { get; init; }
}
