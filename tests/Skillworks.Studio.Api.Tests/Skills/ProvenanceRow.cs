namespace Skillworks.Studio.Api.Tests.Skills;

public sealed record ProvenanceRow
{
    public required string Gap { get; init; }

    public required string? Missing { get; init; }

    public required DateTimeOffset SinceUtc { get; init; }
}
