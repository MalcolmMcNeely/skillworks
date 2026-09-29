namespace Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

public sealed record ToolDetailsRow
{
    public required string? Tool { get; init; }

    public required bool Passed { get; init; }

    public required string? Error { get; init; }

    public required string? Input { get; init; }

    public required long? InputBytes { get; init; }

    public required string? Parameters { get; init; }

    public required string? Command { get; init; }

    public required string? Description { get; init; }

    public required long? ResultBytes { get; init; }

    public required string? AllowedBy { get; init; }
}
