namespace Skillworks.Studio.Api.Tests;

public sealed record PartRow
{
    public required string Name { get; init; }

    public required string State { get; init; }

    public required string Detail { get; init; }

    public required string? Action { get; init; }
}
