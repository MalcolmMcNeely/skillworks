namespace Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

public sealed record FaultDetailsRow
{
    public required string? Error { get; init; }

    public required int? StatusCode { get; init; }

    public required int? Attempt { get; init; }

    public required string? Model { get; init; }

    public required string? Effort { get; init; }

    public required string Purpose { get; init; }

    public required string? Side { get; init; }

    public required string? SentAs { get; init; }
}
