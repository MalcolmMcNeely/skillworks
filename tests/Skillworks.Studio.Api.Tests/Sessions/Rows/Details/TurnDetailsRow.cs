namespace Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

public sealed record TurnDetailsRow
{
    public required string Purpose { get; init; }

    public required string? Side { get; init; }

    public required string? SentAs { get; init; }

    public required string? Model { get; init; }

    public required string? Effort { get; init; }

    public required string? Speed { get; init; }

    public required decimal Cost { get; init; }

    public required long LengthMs { get; init; }

    public required long? FirstWordMs { get; init; }

    public required long CacheReadTokens { get; init; }

    public required long CacheWriteTokens { get; init; }

    public required long InputTokens { get; init; }

    public required long OutputTokens { get; init; }

    public required string? Words { get; init; }

    public required int? WordsLength { get; init; }

    public required string? StopReason { get; init; }

    public required int? Attempt { get; init; }
}
