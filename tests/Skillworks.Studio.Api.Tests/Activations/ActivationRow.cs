using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed record ActivationRow
{
    public required string Id { get; init; }

    public required string Skill { get; init; }

    public required string? Repository { get; init; }

    public required string? Branch { get; init; }

    public required string? Model { get; init; }

    public required string? Effort { get; init; }

    public required DateTimeOffset TimestampUtc { get; init; }

    public required OriginRow? Origin { get; init; }
}
