namespace Skillworks.Studio.Api.Tests.Sessions.Rows;

public sealed record FindingRow
{
    public required string Kind { get; init; }

    public required string? Subject { get; init; }

    public required decimal? Figure { get; init; }

    public required decimal Bar { get; init; }

    public required string? Step { get; init; }

    public required DateTimeOffset AtUtc { get; init; }

    public required long LengthMs { get; init; }
}
