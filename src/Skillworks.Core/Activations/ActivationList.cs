using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

public sealed record ActivationList(
    IReadOnlyList<ActivationSummary> Activations,
    ProvenanceNote Provenance,
    DaySpan Span);
