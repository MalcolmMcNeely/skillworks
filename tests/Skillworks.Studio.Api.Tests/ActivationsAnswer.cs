namespace Skillworks.Studio.Api.Tests;

public sealed record ActivationsAnswer
{
    public required ActivationRow[] Activations { get; init; }

    public required ProvenanceRow Provenance { get; init; }
}
