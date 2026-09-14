namespace Skillworks.Studio.Api.Tests.Activations;

public sealed record ArgumentRow
{
    public required string Name { get; init; }

    public required string Value { get; init; }
}
