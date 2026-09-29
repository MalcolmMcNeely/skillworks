namespace Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

public sealed record TurnDetailsRow
{
    public required string Purpose { get; init; }

    public required string? Side { get; init; }

    public required string? SentAs { get; init; }

    public required long OutputTokens { get; init; }

    public required decimal Cost { get; init; }
}
