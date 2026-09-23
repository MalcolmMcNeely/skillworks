namespace Skillworks.Studio.Api.Tests.Dashboard.Skills;

public sealed record TriggerRow
{
    public required string? Trigger { get; init; }

    public required int Activations { get; init; }
}
