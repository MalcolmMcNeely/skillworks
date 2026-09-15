namespace Skillworks.Studio.Api.Tests.Skills;

public sealed record GapRow
{
    public required string Kind { get; init; }

    public required string? Missing { get; init; }
}
