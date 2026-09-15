using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed record ActivationsAnswer
{
    public required ActivationRow[] Activations { get; init; }

    public required ProvenanceRow Provenance { get; init; }

    public required SpanRow Span { get; init; }
}
