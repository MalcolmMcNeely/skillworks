namespace Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

public sealed record RefusalDetailsRow
{
    public required string? Tool { get; init; }

    public required string? Input { get; init; }

    public required long? InputBytes { get; init; }

    public required string? Parameters { get; init; }

    public required string? Command { get; init; }

    public required string? Description { get; init; }

    public required string? RefusedBy { get; init; }
}
