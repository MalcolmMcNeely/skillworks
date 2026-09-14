namespace Skillworks.Studio.Api.Tests.Health;

public sealed record HealthRow
{
    public required PartRow[] Parts { get; init; }

    public required string? WhyEmpty { get; init; }
}
