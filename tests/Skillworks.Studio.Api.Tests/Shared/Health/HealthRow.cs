namespace Skillworks.Studio.Api.Tests.Shared.Health;

public sealed record HealthRow
{
    public required PartRow[] Parts { get; init; }
}
