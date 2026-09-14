using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed record ActivationAnswer
{
    public required ActivationDetailRow Activation { get; init; }

    public required ProvenanceRow Provenance { get; init; }
}
