namespace Skillworks.Studio.Api.Tests.Activations;

public sealed record ActivationRow
{
    public required string Skill { get; init; }

    public required DateTimeOffset AtUtc { get; init; }

    public required string Session { get; init; }

    public required string? Repository { get; init; }

    public required string? Trigger { get; init; }
}
