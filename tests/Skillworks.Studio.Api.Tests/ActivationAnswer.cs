namespace Skillworks.Studio.Api.Tests;

public sealed record ActivationAnswer
{
    public required ActivationDetailRow Activation { get; init; }

    public required ProvenanceRow Provenance { get; init; }
}
